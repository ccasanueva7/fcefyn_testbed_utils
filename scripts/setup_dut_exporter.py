#!/usr/bin/env python3
"""
Setup Prometheus node exporter on OpenWrt DUTs via parallel SSH.

Installs prometheus-node-exporter-lua and optional collectors (hwmon, wifi,
filesystem), configures loopback-only listening, and enables the service.

Prerequisite: DUT must have internet access (run provision_dut.py first).

Usage:
  python setup_dut_exporter.py --all
  python setup_dut_exporter.py --device belkin-rt3200-1
  python setup_dut_exporter.py --all --dry-run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

SSH_TIMEOUT = 30
SSH_BASE_CMD = [
    "ssh",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", f"ConnectTimeout={SSH_TIMEOUT}",
    "-o", "LogLevel=ERROR",
]

OPKG_PACKAGES = [
    "prometheus-node-exporter-lua",
    "prometheus-node-exporter-lua-openwrt",
    "prometheus-node-exporter-lua-hwmon",
    "prometheus-node-exporter-lua-wifi",
    "luci-lib-nixio",
]

FILESYSTEM_LUA = r'''local nix = require "nixio"

local function scrape()
  local metric_size_bytes = metric("node_filesystem_size_bytes", "gauge")
  local metric_free_bytes = metric("node_filesystem_free_bytes", "gauge")
  local metric_avail_bytes = metric("node_filesystem_avail_bytes", "gauge")
  local metric_files = metric("node_filesystem_files", "gauge")
  local metric_files_free = metric("node_filesystem_files_free", "gauge")
  local metric_readonly = metric("node_filesystem_readonly", "gauge")

  for e in io.lines("/proc/self/mounts") do
    local fields = space_split(e)
    local device, mount_point, fs_type = fields[1], fields[2], fields[3]

    if mount_point:find("/dev/?", 1) ~= 1
    and mount_point:find("/proc/?", 1) ~= 1
    and mount_point:find("/sys/?", 1) ~= 1
    and fs_type ~= "overlay" and fs_type ~= "squashfs"
    and fs_type ~= "tmpfs"   and fs_type ~= "sysfs"
    and fs_type ~= "proc"    and fs_type ~= "devtmpfs"
    and fs_type ~= "devpts"  and fs_type ~= "debugfs"
    and fs_type ~= "cgroup"  and fs_type ~= "cgroup2"
    and fs_type ~= "pstore" then
      local ok, stat = pcall(nix.fs.statvfs, mount_point)
      if ok and stat then
        local labels = { device = device, fstype = fs_type, mountpoint = mount_point }
        local ro = (nix.bit.band(stat.flag, 0x001) == 1) and 1 or 0
        metric_size_bytes(labels, stat.blocks * stat.bsize)
        metric_free_bytes(labels, stat.bfree  * stat.bsize)
        metric_avail_bytes(labels, stat.bavail * stat.bsize)
        metric_files(labels, stat.files)
        metric_files_free(labels, stat.ffree)
        metric_readonly(labels, ro)
      end
    end
  end
end

return { scrape = scrape }
'''


def build_setup_script() -> str:
    """Build a shell script that installs and configures the exporter on a DUT."""
    pkgs = " ".join(OPKG_PACKAGES)
    lines = [
        "#!/bin/sh",
        "set -e",
        "",
        f"opkg update && opkg install {pkgs}",
        "",
        "uci set prometheus-node-exporter-lua.main.listen_interface='loopback'",
        "uci commit prometheus-node-exporter-lua",
        "",
        "cat > /usr/lib/lua/prometheus-collectors/filesystem.lua << 'LUAEOF'",
        FILESYSTEM_LUA.strip(),
        "LUAEOF",
        "",
        "/etc/init.d/prometheus-node-exporter-lua enable",
        "/etc/init.d/prometheus-node-exporter-lua restart",
        "",
        "sleep 2",
        'METRICS=$(wget -qO- http://127.0.0.1:9100/metrics 2>&1 | head -5)',
        'if [ -n "$METRICS" ]; then',
        '  echo "VERIFY_OK"',
        '  echo "$METRICS"',
        "else",
        '  echo "VERIFY_FAIL: no metrics on :9100"',
        "fi",
    ]
    return "\n".join(lines)


def load_duts(config_path: Path) -> list[dict]:
    """Load DUT entries with ssh_alias from dut-config.yaml."""
    if not config_path.exists():
        return []
    try:
        import yaml
    except ImportError:
        print("ERROR: pyyaml required. Run: pip install pyyaml", file=sys.stderr)
        return []
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    duts = data.get("duts") or {}
    result = []
    for dut_id, hw in duts.items():
        ssh_alias = hw.get("ssh_alias")
        if ssh_alias:
            result.append({"id": dut_id, "ssh_alias": ssh_alias})
    return result


def find_dut_by_name(name: str, config_path: Path) -> dict | None:
    """Find a single DUT by id, ssh_alias, or serial device name."""
    duts = load_duts(config_path)
    for d in duts:
        if name in (d["id"], d["ssh_alias"]):
            return d
    norm = name if name.startswith("/") else f"/dev/{name}"
    try:
        import yaml
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        for dut_id, hw in (data.get("duts") or {}).items():
            port = hw.get("serial_port", "")
            if port == norm or Path(port).name == Path(norm).name:
                return {"id": dut_id, "ssh_alias": hw.get("ssh_alias", "")}
    except Exception:
        pass
    return None


def run_on_dut(
    dut: dict, script: str, dry_run: bool = False,
) -> bool:
    """SSH into a DUT, run the setup script, return True on success."""
    dut_id = dut["id"]
    ssh_alias = dut["ssh_alias"]

    if dry_run:
        print(f"\n  [{dut_id}] ({ssh_alias}) DRY-RUN:")
        for line in script.split("\n"):
            print(f"    {line}")
        return True

    print(f"  [{dut_id}] SSH to {ssh_alias}...")
    cmd = SSH_BASE_CMD + [ssh_alias, script]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=SSH_TIMEOUT + 120,
        )
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT {dut_id}: SSH timed out (opkg too slow?)", file=sys.stderr)
        return False

    stdout = result.stdout.decode(errors="replace").strip()
    stderr = result.stderr.decode(errors="replace").strip()

    if result.returncode == 0 and "VERIFY_OK" in stdout:
        print(f"  OK {dut_id} -> exporter installed and serving metrics")
        return True

    if result.returncode == 0 and "VERIFY_FAIL" in stdout:
        print(f"  WARN {dut_id}: installed but metrics not serving yet", file=sys.stderr)
        if stdout:
            print(f"    stdout: {stdout[:300]}", file=sys.stderr)
        return True

    print(f"  FAIL {dut_id} (exit {result.returncode})", file=sys.stderr)
    if stderr:
        print(f"    stderr: {stderr[:500]}", file=sys.stderr)
    if stdout:
        print(f"    stdout: {stdout[:500]}", file=sys.stderr)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install Prometheus node exporter on OpenWrt DUTs via SSH",
        epilog=(
            "Examples:\n"
            "  setup_dut_exporter.py --all                     # all DUTs\n"
            "  setup_dut_exporter.py --device belkin-rt3200-1   # one DUT\n"
            "  setup_dut_exporter.py --all --dry-run            # preview\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--device", "-d", help="DUT name, ssh_alias, or serial device")
    parser.add_argument("--all", "-a", action="store_true", help="Setup all DUTs")
    parser.add_argument("--config", default=None, type=Path, help="Path to dut-config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Print script without executing")
    args = parser.parse_args()

    config_path = args.config or (REPO_ROOT / "configs" / "dut-config.yaml")
    script = build_setup_script()

    if args.all:
        duts = load_duts(config_path)
        if not duts:
            print("ERROR: No DUTs found. Check dut-config.yaml.", file=sys.stderr)
            return 1
        print(f"Setting up exporter on {len(duts)} DUTs...")

        if args.dry_run:
            for dut in duts:
                run_on_dut(dut, script, dry_run=True)
            return 0

        procs: list[tuple[dict, subprocess.Popen]] = []
        for dut in duts:
            cmd = SSH_BASE_CMD + [dut["ssh_alias"], script]
            print(f"  [{dut['id']}] Launching SSH to {dut['ssh_alias']}...")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            procs.append((dut, proc))

        ok = 0
        for dut, proc in procs:
            try:
                stdout, stderr = proc.communicate(timeout=SSH_TIMEOUT + 120)
                out = stdout.decode(errors="replace").strip()
                err = stderr.decode(errors="replace").strip()
                if proc.returncode == 0 and "VERIFY_OK" in out:
                    print(f"  OK {dut['id']} -> exporter installed and serving metrics")
                    ok += 1
                elif proc.returncode == 0:
                    print(f"  WARN {dut['id']}: installed but verify inconclusive", file=sys.stderr)
                    if out:
                        print(f"    {out[:300]}", file=sys.stderr)
                    ok += 1
                else:
                    print(f"  FAIL {dut['id']} (exit {proc.returncode})", file=sys.stderr)
                    if err:
                        print(f"    {err[:500]}", file=sys.stderr)
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"  TIMEOUT {dut['id']} -> killed", file=sys.stderr)

        print(f"\nDone: {ok}/{len(duts)} succeeded.")
        return 0 if ok == len(duts) else 1

    if not args.device:
        parser.error("Specify --device or --all")
        return 1

    dut = find_dut_by_name(args.device, config_path)
    if not dut:
        print(f"ERROR: '{args.device}' not found in {config_path}", file=sys.stderr)
        return 1

    success = run_on_dut(dut, script, dry_run=args.dry_run)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
