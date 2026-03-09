"""
Switch drivers package - Vendor-specific command builders for managed switches.

Each driver module exposes functions that return lists of CLI commands.
The actual SSH execution is handled by switch_client.py via Netmiko.

Use get_driver(name) to load a driver by name (e.g. tplink_jetstream).
"""

from __future__ import annotations

import importlib
import re


def get_driver(name: str):
    """Load driver module by name. Name must be a valid Python identifier."""
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValueError(f"Invalid driver name: {name!r}")
    return importlib.import_module(f"switch_drivers.{name}")
