#!/usr/bin/env python3
"""
Switch VLAN Preset - Apply isolated or mesh VLAN configuration via SSH.

Switches between:
  - isolated: each DUT in its own VLAN (100-106) for OpenWrt tests
  - mesh:     all DUTs in VLAN 200 for LibreMesh multi-node tests

After changing VLANs on the switch, updates the default gateway on each DUT
via parallel SSH (using `ssh_alias` from pool-config.yaml) so internet
works in both modes:
  - isolated -> gateway 192.168.XXX.254 (per-VLAN MikroTik interface)
  - mesh     -> gateway 192.168.200.254 (shared MikroTik VLAN 200 interface)

Gateway is applied immediately (ip route replace) without network restart,
and persisted in UCI for reboots.

For hybrid mode (DUTs split across both pools), use pool-manager.py instead.
Uses switch_client.py (Netmiko) for SSH and switch_drivers/ for command building.

Requires: netmiko (pip install netmiko)
"""

import argparse
import logging
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from switch_client import SwitchClient, load_config, get_switch_driver
from dut_gateway import load_duts, update_dut_gateways
from constants import DEFAULT_SWITCH_HOST, DEFAULT_SWITCH_USER, repo_root, user_config_dir

try:
    from switch_state import save_preset_state
except ImportError:
    save_preset_state = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

VLAN_MODE_FILE = user_config_dir() / "labgrid-vlan-mode"


def _write_vlan_mode_file(preset_name: str) -> None:
    """Write current switch mode for labgrid-dut-proxy (SSH VLAN selection)."""
    try:
        VLAN_MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
        VLAN_MODE_FILE.write_text(preset_name)
    except OSError as e:
        logger.warning("Could not write %s: %s (SSH may use wrong VLAN)", VLAN_MODE_FILE, e)


def _build_dut_modes(preset_name: str, config_path: Path) -> dict[str, str]:
    """Build a dut_modes dict mapping all DUTs to the given preset mode."""
    duts = load_duts(config_path)
    return {dut["id"]: preset_name for dut in duts}


def run_preset(
    host: str,
    user: str,
    password: str,
    preset_name: str,
    config_path: Path | None = None,
    dry_run: bool = False,
) -> bool:
    """Apply VLAN preset (isolated or mesh) via SSH, then update DUT gateways via parallel SSH."""
    driver = get_switch_driver()
    try:
        commands = driver.build_preset_commands(preset_name)
    except ValueError as e:
        logger.error("%s", e)
        return False

    try:
        client = SwitchClient(host=host, user=user, password=password)
    except ValueError as e:
        logger.error("%s", e)
        return False

    success = client.send_config_commands(commands)
    if success:
        logger.info("Preset '%s' applied successfully", preset_name)
        _write_vlan_mode_file(preset_name)
        if save_preset_state:
            save_preset_state(preset_name)
        pool_cfg = config_path or (repo_root() / "configs" / "pool-config.yaml")
        dut_modes = _build_dut_modes(preset_name, pool_cfg)
        if dut_modes:
            update_dut_gateways(dut_modes, pool_cfg, dry_run=dry_run)
    return success


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply VLAN preset (isolated or mesh) on managed switch via SSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Presets:
  isolated  - Each DUT in its own VLAN (100-106). For OpenWrt tests.
  mesh      - All DUTs in VLAN 200. For LibreMesh multi-node tests.

Config: same as poe_switch_control (~/.config/poe_switch_control.conf)
  POE_SWITCH_HOST, POE_SWITCH_USER, POE_SWITCH_PASSWORD

For hybrid mode (split DUTs), use pool-manager.py instead.
        """,
    )

    config = load_config()
    driver = get_switch_driver()

    parser.add_argument(
        "preset",
        choices=list(driver.PRESETS.keys()),
        help="VLAN preset to apply",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("POE_SWITCH_HOST") or config.get("POE_SWITCH_HOST", DEFAULT_SWITCH_HOST),
        help=f"Switch IP (default: {DEFAULT_SWITCH_HOST})",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("POE_SWITCH_USER") or config.get("POE_SWITCH_USER", DEFAULT_SWITCH_USER),
        help=f"SSH username (default: {DEFAULT_SWITCH_USER})",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("POE_SWITCH_PASSWORD") or config.get("POE_SWITCH_PASSWORD", ""),
        help="Password (from config or env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show commands that would be sent, do not connect",
    )
    parser.add_argument(
        "--no-gateway",
        action="store_true",
        help="Skip DUT gateway update via SSH (only change switch VLANs)",
    )
    parser.add_argument(
        "--config",
        default=None,
        type=Path,
        help="Path to pool-config.yaml (default: configs/pool-config.yaml)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    pool_cfg = args.config or (repo_root() / "configs" / "pool-config.yaml")

    if args.dry_run:
        commands = driver.build_preset_commands(args.preset)
        print(f"Would apply preset: {args.preset}")
        for cmd in commands:
            print(f"  {cmd}")
        if not args.no_gateway:
            print("\nDUT gateway commands:")
            dut_modes = _build_dut_modes(args.preset, pool_cfg)
            if dut_modes:
                update_dut_gateways(dut_modes, pool_cfg, dry_run=True)
        return 0

    if not args.password:
        logger.error(
            "Password required. Set POE_SWITCH_PASSWORD or use --password. "
            "Config file: ~/.config/poe_switch_control.conf"
        )
        return 3

    success = run_preset(
        args.host, args.user, args.password, args.preset,
        config_path=pool_cfg if not args.no_gateway else None,
        dry_run=False,
    )
    return 0 if success else 2


if __name__ == "__main__":
    sys.exit(main())
