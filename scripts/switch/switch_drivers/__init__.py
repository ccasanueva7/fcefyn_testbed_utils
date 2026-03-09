"""
Switch drivers package - Vendor-specific command builders for managed switches.

Each driver module exposes functions that return lists of CLI commands.
The actual SSH execution is handled by switch_client.py via Netmiko.
"""
