"""
Shared SSH utilities for virtual mesh tests.
Import from here, not from conftest.py, so imports work regardless of
which directory pytest is invoked from.
"""

import os
import subprocess

SSH_BASE_PORT: int = int(os.environ.get("VIRTUAL_MESH_SSH_BASE_PORT", 2222))
N_NODES: int = int(os.environ.get("VIRTUAL_MESH_NODES", 2))
SSH_TIMEOUT: int = int(os.environ.get("VIRTUAL_MESH_SSH_TIMEOUT", 30))

SSH_OPTS = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
    "-o", f"ConnectTimeout={SSH_TIMEOUT}",
]

NODES: list[dict] = [
    {"name": f"vm{i}", "port": SSH_BASE_PORT + i - 1, "index": i}
    for i in range(1, N_NODES + 1)
]


def node_mac(index: int, vwifi: bool = False) -> str:
    """Return the MAC address assigned by launch_debug_vms.sh for a node.

    eth0 (mesh LAN): 52:54:00:00:00:0N
    eth2 (vwifi):    52:54:99:00:00:0N
    """
    prefix = "52:54:99:00:00" if vwifi else "52:54:00:00:00"
    return f"{prefix}:{index:02x}"


def ssh_run(port: int, cmd: str, timeout: int = SSH_TIMEOUT) -> tuple[int, str, str]:
    """Run a command on a VM via SSH. Returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["ssh"] + SSH_OPTS + ["-p", str(port), "root@127.0.0.1", cmd],
        capture_output=True,
        text=True,
        timeout=timeout + 5,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()
