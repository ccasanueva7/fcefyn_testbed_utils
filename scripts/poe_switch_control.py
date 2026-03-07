#!/usr/bin/env python3
"""
PoE Switch Control - Control PoE ports on TP-Link SG2016P via SSH.

Used for power cycling the OpenWRT One (PoE on port 1) and other PoE devices.
Integrates with PDUDaemon via localcmdline driver.

Optimized for speed: single SSH session for cycle (off+on), reduced wait times.
Uses lockfile serialization to prevent SSH session contention when multiple
PoE devices are controlled in parallel.

Requires: paramiko (pip install paramiko)
Password: set POE_SWITCH_PASSWORD environment variable, or pass via --password.
"""

import argparse
import fcntl
import logging
import os
import sys
import time
from contextlib import contextmanager
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_HOST = "192.168.0.1"
DEFAULT_USER = "admin"
DEFAULT_DELAY_SEC = 3
POE_PORTS = (1, 2, 3, 4, 5, 6, 7, 8)  # SG2016P has PoE on ports 1-8

# Timings tuned for TP-Link SG2016P (needs settling time for shell)
SLEEP_AFTER_SEND = 0.5
SLEEP_AFTER_PROMPT = 0.5
SLEEP_INITIAL = 2
SLEEP_CLEAR = 1
PROMPT_TIMEOUT = 8

CONFIG_PATHS = (
    os.path.expanduser("~/.config/poe_switch_control.conf"),
    "/etc/poe_switch_control.conf",
)

LOCK_PATH = "/tmp/poe_switch.lock"
LOCK_TIMEOUT = 60


@contextmanager
def poe_lock(timeout: float = LOCK_TIMEOUT):
    """Acquire exclusive lock to serialize SSH sessions to the switch.
    
    Prevents concurrent SSH connections that cause session contention
    and delayed power cycling when multiple PoE devices boot in parallel.
    """
    lock_fd = None
    try:
        lock_fd = open(LOCK_PATH, "w")
        deadline = time.time() + timeout
        acquired = False
        while time.time() < deadline:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                logger.debug("Acquired PoE lock")
                break
            except BlockingIOError:
                time.sleep(0.1)
        
        if not acquired:
            logger.warning("Lock timeout after %ds, proceeding anyway", timeout)
        
        yield acquired
    finally:
        if lock_fd:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except Exception:
                pass
            lock_fd.close()
            logger.debug("Released PoE lock")


def load_config() -> dict:
    """Load password and options from config file. Not in git."""
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
    """Read until we see a CLI prompt (# or >)."""
    deadline = time.time() + timeout_sec
    buf = ""
    while time.time() < deadline:
        if channel.recv_ready():
            data = channel.recv(1024).decode("utf-8", errors="replace")
            buf += data
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Recv: {repr(data)}")
            if "#" in buf or ">" in buf:
                return True
        else:
            time.sleep(0.1)
    logger.warning(f"Prompt timeout. Last output: {buf[-200:] if buf else '(none)'}")
    return False


def _send_cmd(channel, cmd: str, wait: bool = True) -> None:
    channel.send(cmd + "\r\n")
    time.sleep(SLEEP_AFTER_SEND)
    if wait:
        if not _wait_for_prompt(channel, PROMPT_TIMEOUT):
            logger.warning(f"Prompt not seen after: {cmd}")
        time.sleep(SLEEP_AFTER_PROMPT)


def _run_poe_commands(
    channel,
    port: int,
    action: str,
) -> bool:
    """Send CLI commands for PoE on/off. Caller manages connection."""
    if action not in ("on", "off"):
        return False
    poe_cmd = "enable" if action == "on" else "disable"
    interface = f"gigabitEthernet 1/0/{port}"
    commands = [
        "enable",
        "configure",
        f"interface {interface}",
        f"power inline supply {poe_cmd}",
        "end",
    ]
    for cmd in commands:
        logger.debug(f"Sending: {cmd}")
        _send_cmd(channel, cmd)
    time.sleep(1)
    while channel.recv_ready():
        channel.recv(4096)
    return True


def run_poe_command(
    host: str,
    user: str,
    password: str,
    port: int,
    action: str,
    delay_sec: float = 0,
) -> bool:
    """Execute PoE enable/disable on switch port via SSH.
    
    Uses lockfile serialization to prevent concurrent SSH sessions.
    """
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

    with poe_lock():
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
            channel.settimeout(15)

            time.sleep(SLEEP_INITIAL)
            channel.send("\r\n")
            time.sleep(SLEEP_CLEAR)
            if not _wait_for_prompt(channel, PROMPT_TIMEOUT):
                logger.error("Failed to get initial prompt")
                return False

            success = _run_poe_commands(channel, port, action)

            if success and action == "off" and delay_sec > 0:
                logger.info(f"PoE off on port {port}, waiting {delay_sec}s before next action")
                time.sleep(delay_sec)

            if success:
                logger.info(f"PoE {action} on port {port} completed successfully")
            return success

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return False
        finally:
            client.close()


def run_poe_cycle_single_session(
    host: str,
    user: str,
    password: str,
    port: int,
    delay_sec: float = DEFAULT_DELAY_SEC,
) -> bool:
    """Power cycle (off + wait + on) in a single SSH session.
    
    Uses lockfile serialization to prevent concurrent SSH sessions.
    """
    try:
        import paramiko
    except ImportError:
        logger.error("paramiko not installed. Run: pip install paramiko")
        return False

    if port not in POE_PORTS:
        logger.error(f"Port {port} is not a PoE port (valid: {POE_PORTS})")
        return False

    with poe_lock():
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
            channel.settimeout(15)

            time.sleep(SLEEP_INITIAL)
            channel.send("\r\n")
            time.sleep(SLEEP_CLEAR)
            if not _wait_for_prompt(channel, PROMPT_TIMEOUT):
                logger.error("Failed to get initial prompt")
                return False

            # Off
            if not _run_poe_commands(channel, port, "off"):
                return False
            logger.info(f"PoE off on port {port}, waiting {delay_sec}s")
            time.sleep(delay_sec)

            # On
            if not _run_poe_commands(channel, port, "on"):
                return False
            logger.info("PoE cycle completed successfully")
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
  %(prog)s cycle 1           # Power cycle: off, wait 3s, on (single SSH session)
  %(prog)s cycle 1 --delay 5 # Power cycle with 5s delay

Config file (recommended): ~/.config/poe_switch_control.conf
  Copy from configs/poe_switch_control.conf.example and set POE_SWITCH_PASSWORD.
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
