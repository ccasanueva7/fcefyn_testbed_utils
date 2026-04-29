#!/usr/bin/env python3
"""
Helper script to resolve target file from device name in labnet.yaml.

**Note**: This script is optional! When running pytest, LG_ENV is automatically
resolved from LG_PLACE. You only need this script for:
- Debugging: checking which target file would be used
- Advanced use cases: manual environment setup outside pytest
- CI/CD: verifying target file resolution

Usage:
    python3 scripts/resolve_target.py <device_name>

Example:
    python3 scripts/resolve_target.py belkin_rt3200_1
    # Output: targets/linksys_e8450.yaml
"""

import sys
from pathlib import Path

import yaml


def resolve_target_file(device_name: str, labnet_path: Path = None) -> str:
    """
    Resolve the target file for a given device name.

    This function handles both:
    1. Direct device names (e.g., 'linksys_e8450')
    2. Device instance names (e.g., 'belkin_rt3200_1') that map to base devices

    Args:
        device_name: Name of the device or instance (e.g., 'belkin_rt3200_1' or 'linksys_e8450')
        labnet_path: Path to labnet.yaml (defaults to ../labnet.yaml)

    Returns:
        Path to the target file (e.g., 'targets/linksys_e8450.yaml')
    """
    if labnet_path is None:
        script_dir = Path(__file__).parent
        labnet_path = script_dir.parent / "labnet.yaml"

    with open(labnet_path, "r") as f:
        labnet = yaml.safe_load(f)

    # First, check if it's a direct device name
    if device_name in labnet.get("devices", {}):
        device_config = labnet["devices"][device_name]
        # If target_file is specified, use it; otherwise use device_name
        target_name = device_config.get("target_file", device_name)
        target_file = f"targets/{target_name}.yaml"
        return target_file

    # If not found, check if it's a device instance in any lab
    for lab_name, lab_config in labnet.get("labs", {}).items():
        device_instances = lab_config.get("device_instances", {})
        for base_device, instances in device_instances.items():
            if device_name in instances:
                # Found it! Use the base device
                if base_device in labnet.get("devices", {}):
                    device_config = labnet["devices"][base_device]
                    target_name = device_config.get("target_file", base_device)
                    target_file = f"targets/{target_name}.yaml"
                    return target_file

    # Not found anywhere
    print(f"Error: Device or instance '{device_name}' not found in labnet.yaml", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("Usage: resolve_target.py <device_name>", file=sys.stderr)
        print("Example: resolve_target.py belkin_rt3200_1", file=sys.stderr)
        sys.exit(1)

    device_name = sys.argv[1]
    target_file = resolve_target_file(device_name)
    print(target_file)


if __name__ == "__main__":
    main()
