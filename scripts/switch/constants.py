"""
Shared constants and helpers for the testbed scripts.

Centralizes network constants, switch defaults, and path resolution
used across switch/, dut_gateway, provision_mesh_ip, and pool-manager.
"""

import os
from pathlib import Path


# -- Network constants -------------------------------------------------------

MESH_GATEWAY = "192.168.200.254"
MESH_DNS = "8.8.8.8 8.8.4.4"
MESH_DNS_LIST = ["8.8.8.8", "8.8.4.4"]
VLAN_MESH = 200

# -- Switch defaults ----------------------------------------------------------

DEFAULT_SWITCH_HOST = "192.168.0.1"
DEFAULT_SWITCH_USER = "admin"


# -- Path helpers -------------------------------------------------------------

def repo_root() -> Path:
    """Return the repository root (parent of scripts/switch/)."""
    return Path(__file__).resolve().parent.parent.parent


def user_config_dir() -> Path:
    """Return ~/.config/ for the real user, respecting SUDO_USER when running as root."""
    if os.geteuid() == 0:
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user:
            try:
                import pwd
                home = Path(pwd.getpwnam(sudo_user).pw_dir)
                return home / ".config"
            except (ImportError, KeyError):
                pass
    return Path(os.path.expanduser("~/.config"))
