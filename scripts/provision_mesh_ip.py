#!/usr/bin/env python3
"""
Provision persistent mesh networking on OpenWrt DUTs via serial console.

Configures each DUT with the addresses needed for SSH access in mesh mode:
  - Secondary IP 10.13.200.x on br-lan (SSH reachability)
  - Route 10.13.0.0/16 (host can reach the DUT)
  - Secondary IP 192.168.200.x on br-lan (gateway subnet, for mesh internet)

The default gateway is NOT modified here; it is managed by dut_gateway.py
which updates the DUT gateway via parallel SSH when VLAN changes occur.

All sections use named UCI keys for idempotency (re-running is safe).

Usage:
  python provision_mesh_ip.py --device /dev/belkin-rt3200-1
  python provision_mesh_ip.py --all
  python provision_mesh_ip.py --device /dev/belkin-rt3200-1 --dry-run
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

DEFAULT_DEVICE_IP_MAP = {
    "/dev/belkin-rt3200-1": "10.13.200.11",
    "/dev/belkin-rt3200-2": "10.13.200.196",
    "/dev/belkin-rt3200-3": "10.13.200.118",
    "/dev/bpi-r4": "10.13.200.169",
    "/dev/openwrt-one": "10.13.200.120",
    "/dev/librerouter-1": "10.13.200.77",
}

for _k, _v in list(DEFAULT_DEVICE_IP_MAP.items()):
    DEFAULT_DEVICE_IP_MAP[_k.rstrip("/").replace("/dev/", "")] = _v


def load_pool_config(config_path: Path) -> list[tuple[str, str, int]]:
    """Load (serial_port, mesh_ip, baud) for all DUTs from dut-config.yaml."""
    if not config_path.exists():
        return []
    try:
        import yaml
    except ImportError:
        return []
    with open(config_path) as f:
        data = yaml.safe_load(f)
    duts = data.get("duts") or {}
    result = []
    for _dut_id, hw in duts.items():
        port = hw.get("serial_port")
        ip = hw.get("libremesh_fixed_ip")
        baud = int(hw.get("serial_speed", 115200))
        if port and ip:
            result.append((port, ip, baud))
    return result


def resolve_ip(device_path: str, explicit_ip: str | None, config_path: Path) -> str | None:
    """Resolve the mesh IP for the given device."""
    if explicit_ip:
        return explicit_ip
    norm = device_path if device_path.startswith("/") else f"/dev/{device_path}"
    duts = load_pool_config(config_path)
    for port, ip, _ in duts:
        if port == norm:
            return ip
    return DEFAULT_DEVICE_IP_MAP.get(norm) or DEFAULT_DEVICE_IP_MAP.get(Path(norm).name)


def send_command(ser: serial.Serial, cmd: str, timeout: float = 3.0) -> str:
    """Send command and read response until timeout."""
    ser.reset_input_buffer()
    ser.write(cmd.encode("utf-8") + b"\r\n")
    deadline = time.monotonic() + timeout
    buf = []
    while time.monotonic() < deadline:
        if ser.in_waiting:
            chunk = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
            buf.append(chunk)
        time.sleep(0.05)
    return "".join(buf)


def _build_uci_commands(ip: str) -> list[str]:
    """Build UCI commands for mesh networking. Uses named sections for idempotency.

    Only provisions addresses and routes needed for SSH reachability:
    - lan_mesh interface (10.13.200.x on br-lan)
    - Host route 10.13.0.0/16 (on-link)
    - Gateway-subnet IP 192.168.200.x on lan (for MikroTik reachability in mesh)

    Does NOT modify the default gateway or DNS -- those are managed by
    dut_gateway.py when VLAN changes occur.
    """
    last_octet = ip.split(".")[-1]
    gateway_subnet_ip = f"192.168.200.{last_octet}"

    return [
        "uci set network.lan_mesh=interface",
        "uci set network.lan_mesh.device='br-lan'",
        "uci set network.lan_mesh.proto='static'",
        f"uci set network.lan_mesh.ipaddr='{ip}'",
        "uci set network.lan_mesh.netmask='255.255.255.0'",
        "uci set network.mesh_route=route",
        "uci set network.mesh_route.interface='lan'",
        "uci set network.mesh_route.target='10.13.0.0'",
        "uci set network.mesh_route.netmask='255.255.0.0'",
        "uci set network.mesh_route.gateway='0.0.0.0'",
        f"uci add_list network.lan.ipaddr='{gateway_subnet_ip}/24'",
        "uci delete network.lan_mesh_gw 2>/dev/null; true",
        "uci delete network.mesh_gateway 2>/dev/null; true",
        "uci commit network",
        "/etc/init.d/network restart",
    ]


def provision_one(
    device_path: str,
    ip: str,
    baud: int,
    dry_run: bool,
) -> bool:
    """Apply lan_mesh and route to one DUT. Returns True on success."""
    uci_cmds = _build_uci_commands(ip)

    if dry_run:
        print(f"  [DRY-RUN] {device_path} -> {ip}")
        for c in uci_cmds:
            print(f"    {c}")
        return True

    if not Path(device_path).exists():
        print(f"  SKIP {device_path}: device not found", file=sys.stderr)
        return False

    try:
        ser = serial.Serial(
            port=device_path,
            baudrate=baud,
            timeout=0.5,
            write_timeout=2.0,
        )
    except serial.SerialException as e:
        print(f"  ERROR {device_path}: {e}", file=sys.stderr)
        return False

    try:
        send_command(ser, "", timeout=0.5)
        for cmd in uci_cmds:
            out = send_command(ser, cmd, timeout=2.0)
            if "error" in out.lower() and "exists" not in out.lower():
                print(f"  WARN {device_path} on '{cmd}': {out[:200]}", file=sys.stderr)
    finally:
        ser.close()

    print(f"  OK {device_path} -> {ip}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Provision persistent mesh IP (10.13.200.x) on OpenWrt DUTs via serial"
    )
    parser.add_argument(
        "--device",
        "-d",
        help="Serial device (e.g. /dev/belkin-rt3200-1). Use --all for all DUTs.",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Apply to all DUTs defined in dut-config.yaml (serial_port + libremesh_fixed_ip)",
    )
    parser.add_argument("--ip", help="Mesh IP to assign (default: from dut-config or built-in map)")
    parser.add_argument("--config", default=None, type=Path, help="Path to dut-config.yaml")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate (used with --device)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without connecting")
    args = parser.parse_args()

    config_path = args.config or (REPO_ROOT / "configs" / "dut-config.yaml")

    if args.all:
        duts = load_pool_config(config_path)
        if not duts:
            print("ERROR: No DUTs found in dut-config. Check serial_port and libremesh_fixed_ip.", file=sys.stderr)
            return 1
        print(f"Provisioning {len(duts)} DUTs from dut-config...")
        print("Close any screen/minicom sessions on these ports first.")
        ok = 0
        for port, ip, baud in duts:
            if provision_one(port, ip, baud, args.dry_run):
                ok += 1
            if not args.dry_run:
                time.sleep(0.5)
        print(f"Done: {ok}/{len(duts)} succeeded.")
        return 0 if ok == len(duts) else 1

    if not args.device:
        parser.error("Specify --device or --all")
        return 1

    ip = resolve_ip(args.device, args.ip, config_path)
    if not ip:
            print(f"ERROR: No IP for {args.device}. Use --ip or add to dut-config.yaml", file=sys.stderr)
        return 1

    print(f"Device: {args.device} -> Mesh IP: {ip}")
    success = provision_one(args.device, ip, args.baud, args.dry_run)
    if success and not args.dry_run:
        print(f"Done. DUT should be reachable at {ip} via SSH in mesh mode.")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
