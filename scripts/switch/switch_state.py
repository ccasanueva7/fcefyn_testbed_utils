#!/usr/bin/env python3
"""
Switch state tracking - Persist last applied VLAN configuration for differential updates.

Written by pool-manager.py (hybrid mode) and switch_vlan_preset.py (isolated/mesh presets).
Used by pool-manager to avoid redundant switch commands when re-applying the same hybrid config.

State file: ~/.config/labgrid-switch-state.yaml
When run under sudo, uses the original user's home so state is shared between tools.
"""

import logging
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from constants import user_config_dir

logger = logging.getLogger(__name__)


def _get_state_file_path() -> Path:
    """Return the path to the switch state file (~/.config/labgrid-switch-state.yaml)."""
    return user_config_dir() / "labgrid-switch-state.yaml"


def load_switch_state() -> dict | None:
    """
    Load switch state from file. Returns None if file does not exist or is invalid.
    """
    state_file = _get_state_file_path()
    if not state_file.is_file():
        return None
    if yaml is None:
        logger.warning("PyYAML not installed, cannot load switch state")
        return None
    try:
        with open(state_file) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return None
        return data
    except (OSError, yaml.YAMLError) as e:
        logger.warning("Could not load switch state from %s: %s", state_file, e)
        return None


def save_switch_state(state: dict) -> None:
    """Write switch state to file."""
    if yaml is None:
        logger.warning("PyYAML not installed, cannot save switch state")
        return
    state_file = _get_state_file_path()
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w") as f:
            yaml.dump(state, f, default_flow_style=False, sort_keys=False)
    except OSError as e:
        logger.warning("Could not write switch state to %s: %s", state_file, e)


def save_preset_state(preset: str) -> None:
    """
    Invalidate hybrid state after applying a full preset (isolated or mesh).
    Call from switch_vlan_preset.py on success.
    """
    save_switch_state({
        "last_applied_by": "switch_vlan_preset",
        "preset": preset,
        "hybrid_ports": None,
        "uplink_tagged_vlans": None,
    })


def save_hybrid_state(ports: dict, uplink_tagged_vlans: list) -> None:
    """
    Save hybrid port state after pool-manager successfully applied config.
    ports: dict mapping port str (e.g. "11") to {"pool": "libremesh"|"openwrt", "vlan": int}
    uplink_tagged_vlans: sorted list of VLAN IDs on uplink ports
    """
    save_switch_state({
        "last_applied_by": "pool-manager",
        "preset": None,
        "hybrid_ports": ports,
        "uplink_tagged_vlans": uplink_tagged_vlans,
    })


def is_hybrid_state_valid_for_diff(state: dict | None) -> bool:
    """Return True if state can be used for differential apply (only changed ports)."""
    if state is None:
        return False
    if state.get("last_applied_by") != "pool-manager":
        return False
    hybrid_ports = state.get("hybrid_ports")
    if not isinstance(hybrid_ports, dict):
        return False
    return True
