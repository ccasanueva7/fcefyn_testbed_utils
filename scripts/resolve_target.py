#!/usr/bin/env python3
"""
Helper script to resolve target file from device name in labnet.yaml.

**Note**: This script is optional! When running pytest, LG_ENV is automatically
resolved from LG_PLACE. You only need this script for:
- Debugging: checking which target file would be used
- Advanced use cases: manual environment setup outside pytest
- CI/CD: verifying target file resolution

Default ``labnet.yaml``: ``LABNET_PATH``, or ``OPENWRT_TESTS_DIR/labnet.yaml``,
or ``../openwrt-tests/labnet.yaml`` relative to this repository (sibling clone).

Usage:
    python3 scripts/resolve_target.py <device_name>

Example:
    python3 scripts/resolve_target.py belkin_rt3200_1
    # Output: targets/linksys_e8450.yaml
"""

import os
import sys
import yaml
from pathlib import Path


def _default_labnet_path() -> Path:
    explicit = os.environ.get("LABNET_PATH", "").strip()
    if explicit:
        p = Path(os.path.expanduser(explicit)).resolve()
        if not p.is_file():
            print(f"Error: LABNET_PATH does not point to a file: {p}", file=sys.stderr)
            sys.exit(1)
        return p

    odir = os.environ.get("OPENWRT_TESTS_DIR", "").strip()
    if odir:
        p = (Path(os.path.expanduser(odir)).resolve() / "labnet.yaml")
        if not p.is_file():
            print(
                f"Error: OPENWRT_TESTS_DIR set but labnet.yaml not found: {p}",
                file=sys.stderr,
            )
            sys.exit(1)
        return p

    utils_root = Path(__file__).resolve().parent.parent
    sibling = utils_root.parent / "openwrt-tests" / "labnet.yaml"
    if sibling.is_file():
        return sibling.resolve()

    print(
        "Error: No labnet.yaml found. Set LABNET_PATH or OPENWRT_TESTS_DIR, "
        "or clone aparcar/openwrt-tests next to fcefyn_testbed_utils.",
        file=sys.stderr,
    )
    sys.exit(1)


def resolve_target_file(device_name: str, labnet_path: Path | None = None) -> str:
    """
    Resolve the target file for a given device name.

    This function handles both:
    1. Direct device names (e.g., 'linksys_e8450')
    2. Device instance names (e.g., 'belkin_rt3200_1') that map to base devices

    Args:
        device_name: Name of the device or instance (e.g., 'belkin_rt3200_1' or 'linksys_e8450')
        labnet_path: Path to labnet.yaml (defaults via LABNET_PATH / OPENWRT_TESTS_DIR / sibling openwrt-tests)

    Returns:
        Path to the target file (e.g., 'targets/linksys_e8450.yaml')
    """
    if labnet_path is None:
        labnet_path = _default_labnet_path()

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
    for _lab_name, lab_config in labnet.get("labs", {}).items():
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
    print(
        f"Error: Device or instance '{device_name}' not found in {labnet_path}",
        file=sys.stderr,
    )
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
