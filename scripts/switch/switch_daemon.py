#!/usr/bin/env python3
"""
Switch SSH Daemon - Maintains a persistent SSH session to the managed switch.

Follows the same architecture as arduino_daemon.py: a long-running process
holds a single Netmiko SSH connection and exposes it to clients through a
Unix socket with JSON request/response protocol.

This eliminates repeated SSH connect/disconnect cycles that TP-Link JetStream
switches handle poorly (rate-limiting, session drops, 'No existing session').

Protocol (JSON over AF_UNIX):
  Request:  {"action": "send_config", "commands": [...]}
  Request:  {"action": "send_command", "command": "show ..."}
  Request:  {"action": "ping"}
  Response: {"success": true, "output": "..."}
  Response: {"success": false, "error": "..."}
"""

import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_SOCKET_PATH = "/tmp/switch-ssh.sock"
DEFAULT_PID_PATH = "/tmp/switch-ssh.pid"
MAX_MSG_SIZE = 65536
RECONNECT_DELAY_SEC = 5
CONNECT_MAX_RETRIES = 3


class SwitchSSHDaemon:
    def __init__(self, socket_path: str = DEFAULT_SOCKET_PATH,
                 pidfile: str = DEFAULT_PID_PATH):
        self.socket_path = socket_path
        self.pidfile = pidfile

        self._conn = None
        self._server_socket = None
        self._running = False
        self._ssh_lock = threading.Lock()
        self._conn_params: dict[str, str] = {}

    def start(self):
        if self._is_already_running():
            if self._socket_reachable():
                logger.info("Daemon already running (socket reachable)")
                return True
            logger.warning("Stale pidfile, cleaning up")
            self._remove_file(self.pidfile)

        self._load_credentials()

        if not self._connect_ssh():
            return False

        if not self._setup_socket():
            return False

        with open(self.pidfile, "w") as f:
            f.write(str(os.getpid()))

        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        self._running = True
        logger.info("Switch SSH Daemon started (PID: %d)", os.getpid())
        self._main_loop()

    def _load_credentials(self):
        from switch_abstraction.client import get_credentials, _resolve_conn_timeout

        creds = get_credentials()
        self._conn_params = {
            "device_type": creds["device_type"],
            "host": creds["host"],
            "username": creds["user"],
            "password": creds["password"],
            "conn_timeout": _resolve_conn_timeout(),
            "allow_agent": False,
            "use_keys": False,
        }
        logger.info("Loaded credentials for %s@%s",
                     creds["user"], creds["host"])

    def _connect_ssh(self) -> bool:
        from netmiko import ConnectHandler

        for attempt in range(1, CONNECT_MAX_RETRIES + 1):
            try:
                self._conn = ConnectHandler(**self._conn_params)
                logger.info("SSH connected to %s (attempt %d)",
                            self._conn_params["host"], attempt)
                return True
            except Exception as e:
                logger.error("SSH connect attempt %d/%d failed: %s",
                             attempt, CONNECT_MAX_RETRIES, e)
                if attempt < CONNECT_MAX_RETRIES:
                    time.sleep(RECONNECT_DELAY_SEC)
        return False

    def _reconnect_ssh(self) -> bool:
        logger.warning("Reconnecting SSH session...")
        if self._conn:
            try:
                self._conn.disconnect()
            except Exception:
                pass
            self._conn = None
        return self._connect_ssh()

    def _ensure_connected(self) -> bool:
        if self._conn and self._conn.is_alive():
            return True
        return self._reconnect_ssh()

    def _setup_socket(self) -> bool:
        try:
            self._remove_file(self.socket_path)
            self._server_socket = socket.socket(socket.AF_UNIX,
                                                socket.SOCK_STREAM)
            self._server_socket.bind(self.socket_path)
            self._server_socket.listen(5)
            os.chmod(self.socket_path, 0o666)
            logger.info("Socket created: %s", self.socket_path)
            return True
        except Exception as e:
            logger.error("Failed to create socket: %s", e)
            return False

    def _main_loop(self):
        while self._running:
            try:
                self._server_socket.settimeout(1.0)
                try:
                    client, _ = self._server_socket.accept()
                    threading.Thread(target=self._handle_client,
                                     args=(client,), daemon=True).start()
                except socket.timeout:
                    continue
            except Exception as e:
                if self._running:
                    logger.error("Main loop error: %s", e)

    def _handle_client(self, client: socket.socket):
        try:
            with client:
                data = client.recv(MAX_MSG_SIZE)
                if not data:
                    return
                request = json.loads(data.decode("utf-8"))
                response = self._dispatch(request)
                client.sendall(json.dumps(response).encode("utf-8"))
        except Exception as e:
            logger.error("Client error: %s", e)

    def _dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        action = request.get("action", "")

        if action == "ping":
            return {"success": True, "output": "pong"}

        if action == "send_config":
            commands = request.get("commands")
            if not isinstance(commands, list):
                return {"success": False, "error": "commands must be a list"}
            return self._exec_send_config(commands)

        if action == "send_command":
            cmd = request.get("command")
            if not isinstance(cmd, str):
                return {"success": False, "error": "command must be a string"}
            return self._exec_send_command(cmd)

        return {"success": False, "error": f"Unknown action: {action}"}

    def _exec_send_config(self, commands: list[str]) -> dict[str, Any]:
        if not commands:
            return {"success": True, "output": ""}
        try:
            with self._ssh_lock:
                if not self._ensure_connected():
                    return {"success": False,
                            "error": "SSH connection unavailable"}
                output = self._conn.send_config_set(commands, cmd_verify=False)
                return {"success": True, "output": output}
        except Exception as e:
            logger.error("send_config failed: %s", e)
            return {"success": False, "error": str(e)}

    def _exec_send_command(self, command: str) -> dict[str, Any]:
        try:
            with self._ssh_lock:
                if not self._ensure_connected():
                    return {"success": False,
                            "error": "SSH connection unavailable"}
                output = self._conn.send_command(command)
                return {"success": True, "output": output}
        except Exception as e:
            logger.error("send_command failed: %s", e)
            return {"success": False, "error": str(e)}

    def _shutdown(self, signum=None, frame=None):
        logger.info("Shutting down...")
        self._running = False

        if self._conn:
            try:
                self._conn.disconnect()
            except Exception:
                pass

        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass

        for path in (self.socket_path, self.pidfile):
            self._remove_file(path)

    def _socket_reachable(self) -> bool:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect(self.socket_path)
            return True
        except (OSError, socket.error):
            return False

    def _is_already_running(self) -> bool:
        if not os.path.exists(self.pidfile):
            return False
        try:
            with open(self.pidfile) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            self._remove_file(self.pidfile)
            return False

    @staticmethod
    def _remove_file(path: str):
        try:
            if os.path.exists(path):
                os.unlink(path)
        except OSError:
            pass


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Switch SSH Daemon - persistent SSH to managed switch",
    )
    parser.add_argument("action", choices=["start", "stop", "status"])

    args = parser.parse_args()
    daemon = SwitchSSHDaemon()

    if args.action == "start":
        if not daemon.start():
            sys.exit(1)

    elif args.action == "stop":
        try:
            with open(DEFAULT_PID_PATH) as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            print("Stop signal sent")
        except FileNotFoundError:
            print("Daemon not running (no pidfile)")
        except Exception as e:
            print(f"Error: {e}")

    elif args.action == "status":
        if daemon._is_already_running():
            alive = daemon._socket_reachable()
            print(f"Daemon is running (socket {'reachable' if alive else 'NOT reachable'})")
        else:
            print("Daemon is not running")


if __name__ == "__main__":
    main()
