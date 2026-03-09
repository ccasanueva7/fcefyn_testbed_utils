#!/usr/bin/env python3
"""
PoE Switch Control - Control PoE ports on a managed switch via SSH.

Used for power cycling the OpenWRT One (PoE on port 1) and other PoE devices.
Integrates with PDUDaemon via localcmdline driver.

Uses switch_client.py (Netmiko) for all SSH operations, with lockfile
serialization to prevent SSH session contention when multiple PoE devices
are controlled in parallel.

Requires: netmiko (pip install netmiko)
Password: set POE_SWITCH_PASSWORD environment variable, or pass via --password.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from switch_client import SwitchClient, load_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_HOST = "192.168.0.1"
DEFAULT_USER = "admin"
DEFAULT_DELAY_SEC = 3
POE_PORTS = (1, 2, 3, 4, 5, 6, 7, 8)


def run_poe_command(
    host: str,
    user: str,
    password: str,
    port: int,
    action: str,
) -> bool:
    """Execute PoE enable/disable on switch port via SSH."""
    if action not in ("on", "off"):
        logger.error("Invalid action: %s", action)
        return False

    if port not in POE_PORTS:
        logger.error("Port %d is not a PoE port (valid: %s)", port, POE_PORTS)
        return False

    try:
        client = SwitchClient(host=host, user=user, password=password)
    except ValueError as e:
        logger.error("%s", e)
        return False

    if action == "on":
        return client.poe_on(port)
    else:
        return client.poe_off(port)


def run_poe_cycle_single_session(
    host: str,
    user: str,
    password: str,
    port: int,
    delay_sec: float = DEFAULT_DELAY_SEC,
) -> bool:
    """Power cycle (off + wait + on) in a single SSH session."""
    if port not in POE_PORTS:
        logger.error("Port %d is not a PoE port (valid: %s)", port, POE_PORTS)
        return False

    try:
        client = SwitchClient(host=host, user=user, password=password)
    except ValueError as e:
        logger.error("%s", e)
        return False

    return client.poe_cycle(port, delay_sec)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Control PoE ports on a managed switch via SSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s on 1              # Enable PoE on port 1 (OpenWRT One)
  %(prog)s off 1             # Disable PoE on port 1
  %(prog)s cycle 1           # Power cycle: off, wait 3s, on (single SSH session)
  %(prog)s cycle 1 --delay 5 # Power cycle with 5s delay

Config file (recommended): ~/.config/poe_switch_control.conf
  Copy from configs/templates/poe_switch_control.conf.example and set POE_SWITCH_PASSWORD.
  Not in git - never commit real passwords.

Environment: POE_SWITCH_PASSWORD (fallback if no config file)
        """,
    )

    config = load_config()

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
        help="Password (config file, env POE_SWITCH_PASSWORD, or this option)",
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
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    on_parser = subparsers.add_parser("on", help="Enable PoE on port")
    on_parser.add_argument("port", type=int, choices=POE_PORTS, help="Switch port (1-8)")

    off_parser = subparsers.add_parser("off", help="Disable PoE on port")
    off_parser.add_argument("port", type=int, choices=POE_PORTS, help="Switch port (1-8)")

    cycle_parser = subparsers.add_parser("cycle", help="Power cycle: off, wait, on")
    cycle_parser.add_argument("port", type=int, choices=POE_PORTS, help="Switch port (1-8)")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.action:
        parser.print_help()
        return 3

    port = args.port
    password = args.password

    if not password:
        logger.error(
            "Password required. Set POE_SWITCH_PASSWORD environment variable "
            "or use --password (avoid in scripts for security)."
        )
        return 3

    if args.action == "cycle":
        success = run_poe_cycle_single_session(
            args.host, args.user, password, port, args.delay
        )
        return 0 if success else 2

    success = run_poe_command(args.host, args.user, password, port, args.action)
    return 0 if success else 2


if __name__ == "__main__":
    sys.exit(main())
