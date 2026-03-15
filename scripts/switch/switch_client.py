"""
Switch Client - Centralized SSH management for managed switches via Netmiko.

All switch SSH operations (VLAN configuration, PoE control) go through this
module. Vendor-specific command building is delegated to driver modules in
switch_drivers/. This module handles:
  - Credential loading from config files and environment variables
  - SSH connection via Netmiko (ConnectHandler)
  - Lockfile serialization to prevent concurrent SSH sessions
  - High-level operations: send_config_commands, poe_on/off/cycle

Requires: netmiko (pip install netmiko)
"""

from __future__ import annotations

import fcntl
import logging
import os
import time
from contextlib import contextmanager
from typing import Generator

from constants import DEFAULT_SWITCH_HOST, DEFAULT_SWITCH_USER, user_config_dir

logger = logging.getLogger(__name__)

DEFAULT_DEVICE_TYPE = "tplink_jetstream"

LOCK_PATH = "/tmp/poe_switch.lock"
LOCK_TIMEOUT = 60


def _open_lock_file():
    """Open lock file for flock. Creates with 0o666 to allow any user to open it.
    On PermissionError (e.g. file exists with restrictive perms from root),
    tries chmod 0o666 and retry. Raises helpful error if still failing.
    """
    try:
        return os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o666)
    except PermissionError:
        if os.path.exists(LOCK_PATH):
            try:
                os.chmod(LOCK_PATH, 0o666)
                return os.open(LOCK_PATH, os.O_RDWR)
            except (PermissionError, OSError) as e:
                raise PermissionError(
                    f"Cannot access lock file {LOCK_PATH}. "
                    "If it was created by root, run: sudo chmod 666 /tmp/poe_switch.lock"
                ) from e
        raise


@contextmanager
def switch_lock(timeout: float = LOCK_TIMEOUT) -> Generator[bool, None, None]:
    """Acquire exclusive lock to serialize SSH sessions to the switch.

    Prevents concurrent SSH connections that cause session contention
    when multiple scripts drive the switch in parallel (PoE + VLAN).

    Lock file is created with mode 0o666 so any user can open it. If the
    file already exists with restrictive perms (e.g. from root), chmod
    is attempted before retry.
    """
    lock_fd = None
    try:
        lock_fd = _open_lock_file()
        deadline = time.time() + timeout
        acquired = False
        while time.time() < deadline:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                logger.debug("Acquired switch lock")
                break
            except BlockingIOError:
                time.sleep(0.1)

        if not acquired:
            logger.warning("Lock timeout after %ds, proceeding anyway", timeout)

        yield acquired
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except Exception:
                pass
            os.close(lock_fd)
            logger.debug("Released switch lock")


def _get_config_paths() -> list[str]:
    """Return config file paths to check, accounting for sudo.

    Priority:
    1. POE_SWITCH_CONFIG env var (explicit path from caller, e.g. testbed-mode.sh)
    2. ~/.config/poe_switch_control.conf (SUDO_USER-aware via user_config_dir)
    3. /etc/poe_switch_control.conf
    """
    paths: list[str] = []
    if explicit := os.environ.get("POE_SWITCH_CONFIG"):
        paths.append(explicit)
    paths.append(str(user_config_dir() / "poe_switch_control.conf"))
    paths.append("/etc/poe_switch_control.conf")
    return paths


def load_config() -> dict[str, str]:
    """Load switch credentials from config file or environment.

    Config file format (key=value, one per line):
        POE_SWITCH_HOST=192.168.0.1
        POE_SWITCH_USER=admin
        POE_SWITCH_PASSWORD=secret
    """
    config: dict[str, str] = {}
    for path in _get_config_paths():
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


def load_switch_password() -> str:
    """Load switch password from config file or POE_SWITCH_PASSWORD env var."""
    config = load_config()
    return (
        os.environ.get("POE_SWITCH_PASSWORD")
        or config.get("POE_SWITCH_PASSWORD", "")
    )


def get_switch_driver():
    """Load the configured driver module from switch_drivers/."""
    from switch_drivers import get_driver

    config = load_config()
    name = config.get("POE_SWITCH_DRIVER", "tplink_jetstream")
    return get_driver(name)


def get_credentials(
    host: str | None = None,
    user: str | None = None,
    password: str | None = None,
    device_type: str | None = None,
) -> dict[str, str]:
    """Build a credentials dict, filling gaps from config/env."""
    config = load_config()
    return {
        "host": host or os.environ.get("POE_SWITCH_HOST") or config.get("POE_SWITCH_HOST", DEFAULT_SWITCH_HOST),
        "user": user or os.environ.get("POE_SWITCH_USER") or config.get("POE_SWITCH_USER", DEFAULT_SWITCH_USER),
        "password": password or os.environ.get("POE_SWITCH_PASSWORD") or config.get("POE_SWITCH_PASSWORD", ""),
        "device_type": device_type or config.get("POE_SWITCH_DEVICE_TYPE", DEFAULT_DEVICE_TYPE),
    }


class SwitchClient:
    """Central SSH client for managed switch operations.

    Uses Netmiko for SSH transport and vendor-specific drivers for
    command building. All operations are serialized via a lockfile.
    """

    def __init__(
        self,
        host: str | None = None,
        user: str | None = None,
        password: str | None = None,
        device_type: str | None = None,
    ):
        creds = get_credentials(host, user, password, device_type)
        self.host = creds["host"]
        self.user = creds["user"]
        self.password = creds["password"]
        self.device_type = creds["device_type"]

        if not self.password:
            raise ValueError(
                "Switch password required. Set POE_SWITCH_PASSWORD in "
                "~/.config/poe_switch_control.conf or via env var."
            )

    def _connect(self):
        """Create a Netmiko connection (caller must disconnect)."""
        from netmiko import ConnectHandler

        return ConnectHandler(
            device_type=self.device_type,
            host=self.host,
            username=self.user,
            password=self.password,
            conn_timeout=10,
        )

    def send_config_commands(self, commands: list[str]) -> bool:
        """Send configuration commands to the switch.

        Wraps Netmiko's send_config_set which handles enable/config mode
        transitions automatically.
        """
        if not commands:
            logger.info("No commands to send, skipping SSH session")
            return True

        with switch_lock():
            try:
                conn = self._connect()
            except Exception as e:
                logger.error("SSH connection to switch failed: %s", e)
                return False

            try:
                output = conn.send_config_set(
                    commands,
                    cmd_verify=False,
                )
                logger.debug("Switch output:\n%s", output)
                logger.info("Switch configuration applied successfully (%d commands)", len(commands))
                return True
            except Exception as e:
                logger.error("Switch command execution failed: %s", e)
                return False
            finally:
                conn.disconnect()

    def send_command(self, command: str) -> str | None:
        """Send a single show command and return output, or None on failure."""
        with switch_lock():
            try:
                conn = self._connect()
            except Exception as e:
                logger.error("SSH connection to switch failed: %s", e)
                return None

            try:
                output = conn.send_command(command)
                return output
            except Exception as e:
                logger.error("Switch command failed: %s", e)
                return None
            finally:
                conn.disconnect()

    def poe_on(self, port: int) -> bool:
        """Enable PoE on a switch port."""
        driver = get_switch_driver()
        cmds = driver.build_poe_commands(port, "on")
        success = self.send_config_commands(cmds)
        if success:
            logger.info("PoE enabled on port %d", port)
        return success

    def poe_off(self, port: int) -> bool:
        """Disable PoE on a switch port."""
        driver = get_switch_driver()
        cmds = driver.build_poe_commands(port, "off")
        success = self.send_config_commands(cmds)
        if success:
            logger.info("PoE disabled on port %d", port)
        return success

    def poe_cycle(self, port: int, delay_sec: float = 3.0) -> bool:
        """Power cycle a PoE port: off, wait, on — in a single locked session."""
        driver = get_switch_driver()
        off_cmds = driver.build_poe_commands(port, "off")
        on_cmds = driver.build_poe_commands(port, "on")

        with switch_lock():
            try:
                conn = self._connect()
            except Exception as e:
                logger.error("SSH connection to switch failed: %s", e)
                return False

            try:
                conn.send_config_set(off_cmds, cmd_verify=False)
                logger.info("PoE off on port %d, waiting %.1fs", port, delay_sec)
                time.sleep(delay_sec)

                conn.send_config_set(on_cmds, cmd_verify=False)
                logger.info("PoE cycle on port %d completed successfully", port)
                return True
            except Exception as e:
                logger.error("PoE cycle failed on port %d: %s", port, e)
                return False
            finally:
                conn.disconnect()
