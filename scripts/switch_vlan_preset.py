#!/usr/bin/env python3
"""
Switch VLAN Preset - Apply isolated or mesh VLAN configuration on TP-Link SG2016P via SSH.

Switches between:
  - isolated: each DUT in its own VLAN (100-106) for OpenWrt tests
  - mesh:     all DUTs in VLAN 200 for LibreMesh multi-node tests

For hybrid mode (DUTs split across both pools), use pool-manager.py instead.
Uses the same config file as poe_switch_control.py (~/.config/poe_switch_control.conf).
Requires: paramiko (pip install paramiko)
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_HOST = "192.168.0.1"
DEFAULT_USER = "admin"

SLEEP_AFTER_SEND = 0.5
SLEEP_AFTER_PROMPT = 0.5
SLEEP_INITIAL = 2
SLEEP_CLEAR = 1
PROMPT_TIMEOUT = 12

CONFIG_PATHS = (
    os.path.expanduser("~/.config/poe_switch_control.conf"),
    "/etc/poe_switch_control.conf",
)

# Preset definitions: list of (interface, commands under interface)
# Commands are sent after "interface gigabitEthernet 1/0/X"
# NOTE: "switchport general allowed vlan" ADDS to existing. When switching from mesh,
# we must first remove VLAN 200. TP-Link uses "no switchport general allowed vlan X"
# (without untagged/tagged) per their CLI guide.
# Ports 4-8: sysConfigBackup_isolated leaves them unconfigured (no explicit vlan).
PRESET_ISOLATED = [
    (1, ["no switchport general allowed vlan 200", "switchport general allowed vlan 104 untagged", "switchport pvid 104", "power inline supply disable"]),
    (2, ["no switchport general allowed vlan 200", "switchport general allowed vlan 105 untagged", "switchport pvid 105"]),
    (3, ["no switchport general allowed vlan 200", "switchport general allowed vlan 106 untagged", "switchport pvid 106"]),
    (4, ["no switchport general allowed vlan 200"]),
    (5, ["no switchport general allowed vlan 200"]),
    (6, ["no switchport general allowed vlan 200"]),
    (7, ["no switchport general allowed vlan 200"]),
    (8, ["no switchport general allowed vlan 200"]),
    (9, ["no switchport general allowed vlan 200", "switchport general allowed vlan 100-106 tagged"]),
    (10, ["no switchport general allowed vlan 200", "switchport general allowed vlan 100-106 tagged"]),
    (11, ["no switchport general allowed vlan 200", "switchport general allowed vlan 100 untagged", "switchport pvid 100"]),
    (12, ["no switchport general allowed vlan 200", "switchport general allowed vlan 101 untagged", "switchport pvid 101"]),
    (13, ["no switchport general allowed vlan 200", "switchport general allowed vlan 102 untagged", "switchport pvid 102"]),
    (14, ["no switchport general allowed vlan 200", "switchport general allowed vlan 103 untagged", "switchport pvid 103"]),
    (15, ["no switchport general allowed vlan 200", "switchport general allowed vlan 105 untagged", "switchport pvid 105"]),
    (16, ["no switchport general allowed vlan 200", "switchport general allowed vlan 104 untagged", "switchport pvid 104"]),
]

# When switching from isolated, remove the per-port VLAN before adding 200.
# Use "no switchport general allowed vlan X" (without untagged/tagged) per TP-Link CLI.
# Ports 4-8: may have default vlan 1 if unconfigured; remove it before adding 200.
PRESET_MESH = [
    (1, ["no switchport general allowed vlan 104", "switchport general allowed vlan 200 untagged", "switchport pvid 200", "power inline supply disable"]),
    (2, ["no switchport general allowed vlan 105", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (3, ["no switchport general allowed vlan 106", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (4, ["no switchport general allowed vlan 1", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (5, ["no switchport general allowed vlan 1", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (6, ["no switchport general allowed vlan 1", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (7, ["no switchport general allowed vlan 1", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (8, ["no switchport general allowed vlan 1", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (9, ["switchport general allowed vlan 100-106,200 tagged"]),
    (10, ["switchport general allowed vlan 100-106,200 tagged"]),
    (11, ["no switchport general allowed vlan 100", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (12, ["no switchport general allowed vlan 101", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (13, ["no switchport general allowed vlan 102", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (14, ["no switchport general allowed vlan 103", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (15, ["no switchport general allowed vlan 105", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (16, ["no switchport general allowed vlan 104", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
]


def load_config() -> dict:
    """Load switch credentials from config file (same as poe_switch_control)."""
    config = {}
    for path in CONFIG_PATHS:
        if os.path.isfile(path) and os.access(path, os.R_OK):
            try:
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            config[key.strip()] = value.strip().strip("'\"")
            except OSError:
                pass
            break
    return config


def _wait_for_prompt(channel, timeout_sec: float = PROMPT_TIMEOUT) -> bool:
    """Read until we see CLI prompt (# or >)."""
    deadline = time.time() + timeout_sec
    buf = ""
    while time.time() < deadline:
        if channel.recv_ready():
            data = channel.recv(1024).decode("utf-8", errors="replace")
            buf += data
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Recv: %r", data)
            if "#" in buf or ">" in buf:
                return True
        else:
            time.sleep(0.1)
    logger.warning("Prompt timeout. Last output: %s", buf[-200:] if buf else "(none)")
    return False


def _send_cmd(channel, cmd: str, wait: bool = True) -> None:
    channel.send(cmd + "\r\n")
    time.sleep(SLEEP_AFTER_SEND)
    if wait:
        if not _wait_for_prompt(channel, PROMPT_TIMEOUT):
            logger.warning("Prompt not seen after: %s", cmd)
        time.sleep(SLEEP_AFTER_PROMPT)


def _apply_preset(channel, preset: list, create_vlan_200: bool = False) -> bool:
    """Send CLI commands for a preset. Caller manages SSH connection."""
    commands = ["enable", "configure"]

    if create_vlan_200:
        commands.extend(["vlan 200", 'name "mesh"', "exit"])

    for port, iface_cmds in preset:
        iface = f"interface gigabitEthernet 1/0/{port}"
        commands.append(iface)
        commands.extend(iface_cmds)
        commands.append("exit")

    commands.append("end")

    for cmd in commands:
        logger.debug("Sending: %s", cmd)
        _send_cmd(channel, cmd)

    return True


VLAN_MODE_FILE = Path(os.path.expanduser("~/.config/labgrid-vlan-mode"))


def _write_vlan_mode_file(preset_name: str) -> None:
    """Write current switch mode for labgrid-dut-proxy (SSH VLAN selection)."""
    try:
        VLAN_MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
        VLAN_MODE_FILE.write_text(preset_name)
    except OSError as e:
        logger.warning("Could not write %s: %s (SSH may use wrong VLAN)", VLAN_MODE_FILE, e)


def run_preset(
    host: str,
    user: str,
    password: str,
    preset_name: str,
) -> bool:
    """Apply VLAN preset (isolated or mesh) via SSH."""
    try:
        import paramiko
    except ImportError:
        logger.error("paramiko not installed. Run: pip install paramiko")
        return False

    if preset_name == "isolated":
        preset = PRESET_ISOLATED
        create_vlan_200 = False
    elif preset_name == "mesh":
        preset = PRESET_MESH
        create_vlan_200 = True
    else:
        logger.error("Invalid preset. Use: isolated | mesh")
        return False

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            host,
            username=user,
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
        )
    except Exception as e:
        logger.error("SSH connection failed: %s", e)
        return False

    try:
        channel = client.invoke_shell()
        channel.settimeout(20)

        time.sleep(SLEEP_INITIAL)
        channel.send("\r\n")
        time.sleep(SLEEP_CLEAR)
        if not _wait_for_prompt(channel, PROMPT_TIMEOUT):
            logger.error("Failed to get initial prompt")
            return False

        success = _apply_preset(channel, preset, create_vlan_200=create_vlan_200)
        if success:
            logger.info("Preset '%s' applied successfully", preset_name)
            _write_vlan_mode_file(preset_name)
        return success

    except Exception as e:
        logger.error("Command execution failed: %s", e)
        return False
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply VLAN preset (isolated or mesh) on TP-Link SG2016P via SSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Presets:
  isolated  - Each DUT in its own VLAN (100-106). For OpenWrt tests.
  mesh      - All DUTs in VLAN 200. For LibreMesh multi-node tests.

Config: same as poe_switch_control (~/.config/poe_switch_control.conf)
  POE_SWITCH_HOST, POE_SWITCH_USER, POE_SWITCH_PASSWORD

For hybrid mode (split DUTs), use pool-manager.py instead.
        """,
    )

    config = load_config()

    parser.add_argument(
        "preset",
        choices=["isolated", "mesh"],
        help="VLAN preset to apply",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("POE_SWITCH_HOST") or config.get("POE_SWITCH_HOST", DEFAULT_HOST),
        help=f"Switch IP (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("POE_SWITCH_USER") or config.get("POE_SWITCH_USER", DEFAULT_USER),
        help=f"SSH username (default: {DEFAULT_USER})",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("POE_SWITCH_PASSWORD") or config.get("POE_SWITCH_PASSWORD", ""),
        help="Password (from config or env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show commands that would be sent, do not connect",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.dry_run:
        preset = PRESET_MESH if args.preset == "mesh" else PRESET_ISOLATED
        create = args.preset == "mesh"
        print(f"Would apply preset: {args.preset}")
        if create:
            print("  vlan 200")
            print('  name "mesh"')
            print("  exit")
        for port, cmds in preset:
            print(f"  interface gigabitEthernet 1/0/{port}")
            for c in cmds:
                print(f"    {c}")
            print("  exit")
        print("  end")
        return 0

    if not args.password:
        logger.error(
            "Password required. Set POE_SWITCH_PASSWORD or use --password. "
            "Config file: ~/.config/poe_switch_control.conf"
        )
        return 3

    success = run_preset(
        args.host, args.user, args.password, args.preset
    )
    return 0 if success else 2


if __name__ == "__main__":
    sys.exit(main())
