#!/usr/bin/env python3
"""
Provision OpenWrt DUTs via serial console after a clean flash.

Configures everything a DUT needs to be reachable and have internet:
  1. Mesh SSH/control IPs (10.13.200.x, 192.168.200.x on br-lan)
  2. On-link route for 10.13.0.0/16
  3. Default gateway for the DUT's isolated VLAN
  4. DNS (8.8.8.8 / 8.8.4.4)
  5. Firewall disabled (not needed on test DUTs)
  6. NTP enabled (many DUTs lack RTC; wrong date breaks SSL/opkg)
  7. Per-device hooks (OpenWrt One eth swap, LibreRouter opkg feeds, etc.)

All commands are sent over USB serial (pyserial). No SSH or network
connectivity required -- works on a freshly flashed DUT.

UCI sections use named keys for idempotency (safe to re-run).

Usage:
  python provision_dut.py --all
  python provision_dut.py --device belkin-rt3200-1
  python provision_dut.py --all --dry-run
  python provision_dut.py --device openwrt-one --skip-mesh-ip
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

try:
    import serial
except ImportError:
    print("ERROR: pyserial required. Run: pip install pyserial", file=sys.stderr)
    sys.exit(2)

# ---------------------------------------------------------------------------
# Per-device hooks: commands that only apply to specific hardware.
# Key = device_type from dut-config.yaml.
# Value = list of shell/UCI commands to send BEFORE the final commit.
# ---------------------------------------------------------------------------

DEVICE_HOOKS: dict[str, list[str]] = {
    "openwrt_one": [
        # Swap eth0/eth1 so PoE port (eth0) becomes br-lan (192.168.1.1)
        "uci delete network.@device[0].ports 2>/dev/null; true",
        "uci add_list network.@device[0].ports='eth0'",
        "uci set network.wan.device='eth1'",
        "uci set network.wan6.device='eth1'",
    ],
    "librerouter_v1": [
        # Fix SNAPSHOT feeds to 23.05.2 and disable non-existent feeds
        "sed -i 's/23.05-SNAPSHOT/23.05.2/g' /etc/opkg/distfeeds.conf",
        (
            "sed -i"
            " -e '/librerouteros_libremesh/s/^/#/'"
            " -e '/librerouteros_librerouter/s/^/#/'"
            " -e '/librerouteros_tmate/s/^/#/'"
            " /etc/opkg/distfeeds.conf"
        ),
    ],
}

SHELL_PROMPT_MARKER = "root@"
PROMPT_WAIT_TIMEOUT = 10.0


# ---------------------------------------------------------------------------
# Serial helpers (adapted from provision_mesh_ip.py)
# ---------------------------------------------------------------------------


def send_command(ser: serial.Serial, cmd: str, timeout: float = 3.0) -> str:
    """Send a command and collect output until *timeout* seconds of silence."""
    ser.reset_input_buffer()
    ser.write(cmd.encode("utf-8") + b"\r\n")
    deadline = time.monotonic() + timeout
    buf: list[str] = []
    while time.monotonic() < deadline:
        if ser.in_waiting:
            chunk = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
            buf.append(chunk)
            deadline = min(deadline, time.monotonic() + 0.5)
        time.sleep(0.05)
    return "".join(buf)


def wait_for_prompt(ser: serial.Serial, timeout: float = PROMPT_WAIT_TIMEOUT) -> bool:
    """Send empty lines until the shell prompt appears, or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        out = send_command(ser, "", timeout=1.0)
        if SHELL_PROMPT_MARKER in out:
            return True
        time.sleep(0.3)
    return False


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------


def build_mesh_ip_commands(mesh_ip: str) -> list[str]:
    """UCI commands for persistent mesh SSH/control IPs and route."""
    last_octet = mesh_ip.split(".")[-1]
    gw_subnet_ip = f"192.168.200.{last_octet}"
    return [
        "uci set network.lan_mesh=interface",
        "uci set network.lan_mesh.device='br-lan'",
        "uci set network.lan_mesh.proto='static'",
        f"uci set network.lan_mesh.ipaddr='{mesh_ip}'",
        "uci set network.lan_mesh.netmask='255.255.255.0'",
        "uci set network.mesh_route=route",
        "uci set network.mesh_route.interface='lan'",
        "uci set network.mesh_route.target='10.13.0.0'",
        "uci set network.mesh_route.netmask='255.255.0.0'",
        "uci set network.mesh_route.gateway='0.0.0.0'",
        f"uci add_list network.lan.ipaddr='{gw_subnet_ip}/24'",
        "uci delete network.lan_mesh_gw 2>/dev/null; true",
        "uci delete network.mesh_gateway 2>/dev/null; true",
    ]


def build_gateway_commands(vlan: int, mesh_ip: str) -> list[str]:
    """UCI commands for default gateway in the DUT's isolated VLAN."""
    gateway = f"192.168.{vlan}.254"
    last_octet = mesh_ip.split(".")[-1]
    src_ip = f"192.168.{vlan}.{last_octet}"
    return [
        "uci delete network.lan.gateway 2>/dev/null; true",
        f"uci set network.lan.gateway='{gateway}'",
    ]


def build_dns_commands() -> list[str]:
    """UCI + resolv.conf for public DNS."""
    return [
        "uci set network.lan.dns='8.8.8.8 8.8.4.4'",
        "echo 'nameserver 8.8.8.8' > /etc/resolv.conf",
        "echo 'nameserver 8.8.4.4' >> /etc/resolv.conf",
    ]


def build_firewall_commands() -> list[str]:
    """Disable and stop the firewall persistently."""
    return [
        "if [ -x /etc/init.d/firewall ]; then /etc/init.d/firewall disable 2>/dev/null; fi || true",
        "if [ -x /etc/init.d/firewall ]; then /etc/init.d/firewall stop 2>/dev/null; fi || true",
        "iptables -P OUTPUT ACCEPT 2>/dev/null || true",
        "iptables -F OUTPUT 2>/dev/null || true",
    ]


def build_ntp_commands() -> list[str]:
    """Set approximate date from host clock, then enable sysntpd.

    Many DUTs lack RTC and boot at epoch (1970). Without a reasonable date,
    SSL handshakes and opkg downloads fail. The host-sourced date gets the
    DUT close enough for SSL to work; NTP refines it afterward.
    """
    from datetime import datetime, timezone

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return [
        f"date -s '{now_utc}'",
        "uci set system.ntp.enabled='1'",
        "uci commit system",
        "if [ -x /etc/init.d/sysntpd ]; then /etc/init.d/sysntpd restart; fi || true",
    ]


def build_commit_commands() -> list[str]:
    """Commit network UCI and restart networking."""
    return [
        "uci commit network",
        "/etc/init.d/network restart",
    ]


def build_verify_commands(vlan: int) -> list[str]:
    """Post-provision connectivity check."""
    gateway = f"192.168.{vlan}.254"
    return [
        f"ping -c 2 -W 3 {gateway} 2>&1 || echo 'WARN: gateway unreachable'",
        "ping -c 2 -W 3 8.8.8.8 2>&1 || echo 'WARN: no internet'",
    ]


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


def load_dut_list(config_path: Path) -> list[dict]:
    """Load DUT entries from dut-config.yaml.

    Returns list of dicts with: id, serial_port, serial_speed,
    switch_vlan_isolated, libremesh_fixed_ip, device_type.
    """
    if not config_path.exists():
        return []
    try:
        import yaml
    except ImportError:
        print("ERROR: pyyaml required for --all. Run: pip install pyyaml", file=sys.stderr)
        return []
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    duts = data.get("duts") or {}
    result = []
    for dut_id, hw in duts.items():
        port = hw.get("serial_port")
        ip = hw.get("libremesh_fixed_ip")
        vlan = hw.get("switch_vlan_isolated")
        if port and ip and vlan:
            result.append({
                "id": dut_id,
                "serial_port": port,
                "serial_speed": int(hw.get("serial_speed", 115200)),
                "switch_vlan_isolated": int(vlan),
                "libremesh_fixed_ip": ip,
                "device_type": hw.get("device_type", ""),
            })
    return result


def find_dut_by_device(device: str, config_path: Path) -> dict | None:
    """Find a single DUT by serial device name (short or full path)."""
    duts = load_dut_list(config_path)
    norm = device if device.startswith("/") else f"/dev/{device}"
    for d in duts:
        if d["serial_port"] == norm or Path(d["serial_port"]).name == Path(norm).name:
            return d
    return None


# ---------------------------------------------------------------------------
# Provisioning logic
# ---------------------------------------------------------------------------


def provision_one(
    dut: dict,
    *,
    dry_run: bool = False,
    skip_mesh_ip: bool = False,
    skip_internet: bool = False,
) -> bool:
    """Provision a single DUT. Returns True on success."""
    dut_id = dut["id"]
    port = dut["serial_port"]
    baud = dut["serial_speed"]
    vlan = dut["switch_vlan_isolated"]
    mesh_ip = dut["libremesh_fixed_ip"]
    device_type = dut.get("device_type", "")

    all_commands: list[str] = []

    if not skip_mesh_ip:
        all_commands += build_mesh_ip_commands(mesh_ip)

    if not skip_internet:
        all_commands += build_gateway_commands(vlan, mesh_ip)
        all_commands += build_dns_commands()
        all_commands += build_firewall_commands()
        all_commands += build_ntp_commands()

    hooks = DEVICE_HOOKS.get(device_type, [])
    if hooks:
        all_commands += hooks

    all_commands += build_commit_commands()

    if not skip_internet:
        all_commands += build_verify_commands(vlan)

    if dry_run:
        print(f"\n  [{dut_id}] {port} (VLAN {vlan}, type={device_type})")
        print(f"  Mesh IP: {mesh_ip}")
        for cmd in all_commands:
            print(f"    {cmd}")
        return True

    if not Path(port).exists():
        print(f"  SKIP {dut_id}: {port} not found", file=sys.stderr)
        return False

    print(f"  [{dut_id}] Connecting to {port} @ {baud}...")
    try:
        ser = serial.Serial(port=port, baudrate=baud, timeout=0.5, write_timeout=2.0)
    except serial.SerialException as e:
        print(f"  ERROR {dut_id}: {e}", file=sys.stderr)
        return False

    try:
        if not wait_for_prompt(ser):
            print(f"  ERROR {dut_id}: no shell prompt on {port} (DUT booted?)", file=sys.stderr)
            return False

        for cmd in all_commands:
            out = send_command(ser, cmd, timeout=4.0)
            if "error" in out.lower() and "exists" not in out.lower() and "no such" not in out.lower():
                print(f"  WARN {dut_id} on '{cmd}': {out[:200]}", file=sys.stderr)
    finally:
        ser.close()

    print(f"  OK {dut_id} -> provisioned (VLAN {vlan}, mesh {mesh_ip})")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Provision OpenWrt DUTs via serial (mesh IPs + internet + per-device hooks)",
        epilog=(
            "Examples:\n"
            "  provision_dut.py --all                     # all DUTs\n"
            "  provision_dut.py --device belkin-rt3200-1   # one DUT\n"
            "  provision_dut.py --all --dry-run            # preview commands\n"
            "  provision_dut.py --all --skip-mesh-ip       # internet only\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--device", "-d", help="Serial device (e.g. belkin-rt3200-1 or /dev/bpi-r4)")
    parser.add_argument("--all", "-a", action="store_true", help="Provision all DUTs in dut-config.yaml")
    parser.add_argument("--config", default=None, type=Path, help="Path to dut-config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without connecting")
    parser.add_argument("--skip-mesh-ip", action="store_true", help="Skip mesh IP provisioning step")
    parser.add_argument("--skip-internet", action="store_true", help="Skip gateway/DNS/firewall/NTP step")
    args = parser.parse_args()

    config_path = args.config or (REPO_ROOT / "configs" / "dut-config.yaml")

    if args.all:
        duts = load_dut_list(config_path)
        if not duts:
            print("ERROR: No DUTs found. Check dut-config.yaml.", file=sys.stderr)
            return 1
        print(f"Provisioning {len(duts)} DUTs from {config_path.name}...")
        if not args.dry_run:
            print("Close any screen/minicom sessions on these ports first.\n")
        ok = 0
        for dut in duts:
            if provision_one(dut, dry_run=args.dry_run, skip_mesh_ip=args.skip_mesh_ip, skip_internet=args.skip_internet):
                ok += 1
            if not args.dry_run:
                time.sleep(0.5)
        print(f"\nDone: {ok}/{len(duts)} succeeded.")
        return 0 if ok == len(duts) else 1

    if not args.device:
        parser.error("Specify --device or --all")
        return 1

    dut = find_dut_by_device(args.device, config_path)
    if not dut:
        print(f"ERROR: Device '{args.device}' not found in {config_path}", file=sys.stderr)
        return 1

    success = provision_one(dut, dry_run=args.dry_run, skip_mesh_ip=args.skip_mesh_ip, skip_internet=args.skip_internet)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
