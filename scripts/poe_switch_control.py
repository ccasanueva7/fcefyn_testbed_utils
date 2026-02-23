#!/usr/bin/env python3
"""
PoE Switch Control - Control PoE ports on TP-Link SG2016P via SSH.

Used for power cycling the OpenWRT One (PoE on port 1) and other PoE devices.
Integrates with PDUDaemon via localcmdline driver.

Requires: paramiko (pip install paramiko)
Password: set POE_SWITCH_PASSWORD environment variable, or pass via --password.
"""

import argparse
import logging
import os
import sys
import time
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_HOST = "192.168.0.1"
DEFAULT_USER = "admin"
DEFAULT_DELAY_SEC = 5
POE_PORTS = (1, 2, 3, 4, 5, 6, 7, 8)  # SG2016P has PoE on ports 1-8


def run_poe_command(
    host: str,
    user: str,
    password: str,
    port: int,
    action: str,
    delay_sec: float = DEFAULT_DELAY_SEC,
) -> bool:
    """Execute PoE enable/disable on switch port via SSH."""
    try:
        import paramiko
    except ImportError:
        logger.error("paramiko not installed. Run: pip install paramiko")
        return False

    if action not in ("on", "off"):
        logger.error(f"Invalid action: {action}")
        return False

    if port not in POE_PORTS:
        logger.error(f"Port {port} is not a PoE port (valid: {POE_PORTS})")
        return False

    poe_cmd = "enable" if action == "on" else "disable"
    # CLI: interface gigabitEthernet 1/0/N
    interface = f"gigabitEthernet 1/0/{port}"

    commands = [
        "enable",
        "configure",
        f"interface {interface}",
        f"power inline supply {poe_cmd}",
        "end",
    ]

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
        logger.error(f"SSH connection failed: {e}")
        return False

    try:
        channel = client.invoke_shell()
        channel.settimeout(10)

        def send_cmd(cmd: str) -> None:
            channel.send(cmd + "\n")
            time.sleep(0.5)

        for cmd in commands:
            logger.debug(f"Sending: {cmd}")
            send_cmd(cmd)

        # Read output to clear buffer
        time.sleep(1)
        while channel.recv_ready():
            channel.recv(4096)

        client.close()

        if action == "off" and delay_sec > 0:
            logger.info(f"PoE off on port {port}, waiting {delay_sec}s before next action")
            time.sleep(delay_sec)

        logger.info(f"PoE {action} on port {port} completed successfully")
        return True

    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return False
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Control PoE ports on TP-Link SG2016P switch via SSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s on 1              # Enable PoE on port 1 (OpenWRT One)
  %(prog)s off 1             # Disable PoE on port 1
  %(prog)s cycle 1           # Power cycle: off, wait 5s, on
  %(prog)s cycle 1 --delay 10 # Power cycle with 10s delay

Environment:
  POE_SWITCH_PASSWORD        Switch admin password (required for non-interactive use)
        """,
    )

    parser.add_argument(
        "--host",
        default=os.environ.get("POE_SWITCH_HOST", DEFAULT_HOST),
        help=f"Switch IP (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("POE_SWITCH_USER", DEFAULT_USER),
        help=f"SSH username (default: {DEFAULT_USER})",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("POE_SWITCH_PASSWORD", ""),
        help="SSH password (or set POE_SWITCH_PASSWORD env var)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SEC,
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
        if not run_poe_command(args.host, args.user, password, port, "off", args.delay):
            return 2
        return 0 if run_poe_command(args.host, args.user, password, port, "on", 0) else 2

    success = run_poe_command(args.host, args.user, password, port, args.action)
    return 0 if success else 2


if __name__ == "__main__":
    sys.exit(main())
