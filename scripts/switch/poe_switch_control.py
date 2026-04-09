#!/usr/bin/env python3
"""
PoE Switch Control - Control PoE ports on a managed switch via SSH.

Used for power cycling the OpenWRT One (PoE on port 1) and other PoE devices.
Integrates with PDUDaemon via localcmdline driver.

Uses labgrid-switch-abstraction (SwitchClient) for all SSH operations,
with lockfile serialization to prevent SSH session contention when
multiple PoE devices are controlled in parallel.

Requires: labgrid-switch-abstraction (pip install)
Password: set SWITCH_PASSWORD env var, or in ~/.config/switch.conf.
"""

import argparse
import logging
import os
import sys

from switch_abstraction.client import SwitchClient, load_config
from switch_abstraction.constants import DEFAULT_SWITCH_HOST, DEFAULT_SWITCH_USER

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
DEFAULT_DELAY_SEC = 3
POE_PORTS = (1, 2, 3, 4, 5, 6, 7, 8)


def _validate_ports(ports: list[int]) -> list[int]:
    """Validate that all ports are PoE-capable. Returns the list or raises."""
    invalid = [p for p in ports if p not in POE_PORTS]
    if invalid:
        logger.error("Invalid PoE port(s) %s (valid: %s)", invalid, POE_PORTS)
        raise ValueError(f"Invalid PoE port(s): {invalid}")
    return ports


def run_poe_command(
    host: str,
    user: str,
    password: str,
    ports: list[int],
    action: str,
) -> bool:
    """Execute PoE enable/disable on one or more switch ports via SSH."""
    if action not in ("on", "off"):
        logger.error("Invalid action: %s", action)
        return False

    try:
        _validate_ports(ports)
        client = SwitchClient(host=host, user=user, password=password)
    except Exception as e:
        logger.error("%s", e)
        return False

    if action == "on":
        return client.poe_on_multi(ports)
    else:
        return client.poe_off_multi(ports)


def run_poe_cycle_single_session(
    host: str,
    user: str,
    password: str,
    ports: list[int],
    delay_sec: float = DEFAULT_DELAY_SEC,
) -> bool:
    """Power cycle (off + wait + on) one or more ports in a single SSH session."""
    try:
        _validate_ports(ports)
        client = SwitchClient(host=host, user=user, password=password)
    except Exception as e:
        logger.error("%s", e)
        return False

    return client.poe_cycle_multi(ports, delay_sec)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Control PoE ports on a managed switch via SSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s on 1              # Enable PoE on port 1 (OpenWRT One)
  %(prog)s on 1 2            # Enable PoE on ports 1 and 2 (single SSH session)
  %(prog)s off 1             # Disable PoE on port 1
  %(prog)s cycle 1           # Power cycle: off, wait 3s, on (single SSH session)
  %(prog)s cycle 1 2         # Power cycle ports 1 and 2 together
  %(prog)s cycle 1 --delay 5 # Power cycle with 5s delay

Config file (recommended): ~/.config/switch.conf
  Copy from configs/templates/switch.conf.example and set SWITCH_PASSWORD.
  Not in git - never commit real passwords.

Environment: SWITCH_PASSWORD (fallback if no config file)
        """,
    )

    config = load_config()

    parser.add_argument(
        "--host",
        default=os.environ.get("SWITCH_HOST") or config.get("SWITCH_HOST", DEFAULT_SWITCH_HOST),
        help=f"Switch IP (default: {DEFAULT_SWITCH_HOST})",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("SWITCH_USER") or config.get("SWITCH_USER", DEFAULT_SWITCH_USER),
        help=f"SSH username (default: {DEFAULT_SWITCH_USER})",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("SWITCH_PASSWORD") or config.get("SWITCH_PASSWORD", ""),
        help="Password (config file, env SWITCH_PASSWORD, or this option)",
    )
    delay_default = os.environ.get("POE_CYCLE_DELAY") or config.get("POE_CYCLE_DELAY")
    try:
        delay_default = float(delay_default) if delay_default else DEFAULT_DELAY_SEC
    except (TypeError, ValueError):
        delay_default = DEFAULT_DELAY_SEC

    parser.add_argument(
        "--delay",
        type=float,
        default=delay_default,
        help=f"Delay in seconds for cycle between off/on (default: {DEFAULT_DELAY_SEC})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    on_parser = subparsers.add_parser("on", help="Enable PoE on one or more ports")
    on_parser.add_argument(
        "ports", nargs="+", type=int, choices=POE_PORTS, help="Switch port(s) (1-8). Multiple allowed.", metavar="PORT"
    )

    off_parser = subparsers.add_parser("off", help="Disable PoE on one or more ports")
    off_parser.add_argument(
        "ports", nargs="+", type=int, choices=POE_PORTS, help="Switch port(s) (1-8). Multiple allowed.", metavar="PORT"
    )

    cycle_parser = subparsers.add_parser("cycle", help="Power cycle: off, wait, on")
    cycle_parser.add_argument(
        "ports", nargs="+", type=int, choices=POE_PORTS, help="Switch port(s) (1-8). Multiple allowed.", metavar="PORT"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.action:
        parser.print_help()
        return 3

    ports = args.ports
    password = args.password

    if not password:
        logger.error(
            "Password required. Set SWITCH_PASSWORD environment variable "
            "or use --password (avoid in scripts for security)."
        )
        return 3

    if args.action == "cycle":
        success = run_poe_cycle_single_session(args.host, args.user, password, ports, args.delay)
        return 0 if success else 2

    success = run_poe_command(args.host, args.user, password, ports, args.action)
    return 0 if success else 2


if __name__ == "__main__":
    sys.exit(main())
