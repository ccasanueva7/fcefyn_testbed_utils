#!/usr/bin/env python3
"""
pool-manager - Generate labgrid exporter configs and configure the switch
               based on pool-config.yaml DUT assignments.

Supports three testbed modes derived from pool-config.yaml:
  - libremesh-only: all DUTs in libremesh pool (VLAN 200)
  - openwrt-only:   all DUTs in openwrt pool (isolated VLANs 100-108)
  - hybrid:         DUTs split across both pools simultaneously

After configuring VLANs on the switch, updates each DUT's default gateway
via parallel SSH so that internet works regardless of pool assignment:
  - openwrt pool  -> gateway 192.168.XXX.254 (per-VLAN MikroTik interface)
  - libremesh pool -> gateway 192.168.200.254 (shared MikroTik VLAN 200 interface)

Usage:
  pool-manager.py --generate                    # Print generated configs (dry run)
  pool-manager.py --apply                       # Apply switch + deploy to /etc/labgrid/ (default)
  pool-manager.py --apply --export-to-configs   # Write to configs/ only (for manual Ansible)
  pool-manager.py --apply --no-switch           # Skip switch config
  pool-manager.py --apply --no-gateway          # Skip DUT gateway update via SSH
  pool-manager.py --apply --force               # Full switch apply; skip DUT-in-use check

Differential apply: When re-applying hybrid config, only changed ports are configured.
If state matches desired (no diff), full config is applied to correct any switch staleness.
State is stored in ~/.config/labgrid-switch-state.yaml. Use --force to bypass.

Default (--apply): deploys exporters to /etc/labgrid/, restarts services. No files in configs/.

With --export-to-configs: writes exporter YAMLs and dut-proxy.yaml to configs/ (next to
pool-config.yaml) for manual copy to Ansible. Does not deploy to /etc/labgrid/.
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from switch_client import SwitchClient, load_switch_password, get_switch_driver
from dut_gateway import update_dut_gateways
from constants import VLAN_MESH, repo_root, user_config_dir

try:
    from switch_state import (
        load_switch_state,
        save_hybrid_state,
        is_hybrid_state_valid_for_diff,
    )
except ImportError:
    load_switch_state = None
    save_hybrid_state = None
    is_hybrid_state_valid_for_diff = None

REPO_ROOT = repo_root()
CONFIG_DIR = REPO_ROOT / "configs"
POOL_CONFIG_PATH = CONFIG_DIR / "pool-config.yaml"
TFTP_IP_MESH = "192.168.200.1"

# Default SSH alias when ssh_alias not in pool-config
DEFAULT_SSH_ALIAS: dict[str, str] = {
    "belkin_rt3200_1": "belkin-1",
    "belkin_rt3200_2": "belkin-2",
    "belkin_rt3200_3": "belkin-3",
    "bananapi_bpi-r4": "bananapi",
    "openwrt_one": "openwrt-one",
    "librerouter_1": "librerouter-1",
    "librerouter_2": "librerouter-2",
    "librerouter_3": "librerouter-3",
}

HYBRID_SERVICE_OPENWRT = "labgrid-exporter-openwrt"
HYBRID_SERVICE_LIBREMESH = "labgrid-exporter-libremesh"
SINGLE_SERVICE = "labgrid-exporter"

EXPORTER_DIR = Path("/etc/labgrid")
SYSTEMD_DIR = Path("/etc/systemd/system")


def _get_config_path(filename: str) -> Path:
    """Return path to a config file in ~/.config/, respecting SUDO_USER."""
    return user_config_dir() / filename


# ---------------------------------------------------------------------------
# Config loading and validation
# ---------------------------------------------------------------------------

def load_pool_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def validate_config(config: dict) -> list[str]:
    """Return list of error strings (empty → valid)."""
    errors = []
    duts_db = config.get("duts", {})
    pools = config.get("pools", {})

    assigned: dict[str, str] = {}
    for pool_name, pool in pools.items():
        for dut in pool.get("duts", []):
            if dut not in duts_db:
                errors.append(f"Pool '{pool_name}': DUT '{dut}' not in duts database")
            if dut in assigned:
                errors.append(
                    f"DUT '{dut}' assigned to both '{assigned[dut]}' and '{pool_name}'"
                )
            assigned[dut] = pool_name

    return errors


# ---------------------------------------------------------------------------
# Exporter YAML generation
# ---------------------------------------------------------------------------

def _dut_block_base(dut_name: str, hw: dict) -> dict:
    """Build the common exporter block fields for a DUT."""
    block: dict = {
        "location": hw["location"],
        "RawSerialPort": {
            "port": hw["serial_port"],
            "speed": hw["serial_speed"],
        },
        "PDUDaemonPort": {
            "host": hw["pdu_host"],
            "pdu": hw["pdu_name"],
            "index": hw["pdu_index"],
        },
    }
    return block


def generate_libremesh_exporter(dut_names: list[str], duts_db: dict) -> str:
    """Generate exporter YAML for the libremesh pool (all DUTs on VLAN 200)."""
    lines: list[str] = []

    for dut_name in dut_names:
        hw = duts_db[dut_name]
        fixed_ip = hw["libremesh_fixed_ip"]
        tftp_path = hw["tftp_path"]
        entry_name = f"labgrid-fcefyn-{dut_name}"

        lines.append(f"{entry_name}:")
        lines.append(f"  location: {hw['location']}")
        lines.append("  RawSerialPort:")
        lines.append(f"    port: \"{hw['serial_port']}\"")
        lines.append(f"    speed: {hw['serial_speed']}")
        lines.append("  PDUDaemonPort:")
        lines.append(f"    host: {hw['pdu_host']}")
        lines.append(f"    pdu: {hw['pdu_name']}")
        lines.append(f"    index: {hw['pdu_index']}")
        lines.append("  TFTPProvider:")
        lines.append(f"    internal: \"/srv/tftp/{tftp_path}\"")
        lines.append(f"    external: \"{tftp_path}\"")
        lines.append(f"    external_ip: \"{TFTP_IP_MESH}\"")
        lines.append("  NetworkService:")
        lines.append(f"    address: \"{fixed_ip}%vlan{VLAN_MESH}\"")
        lines.append("    username: \"root\"")
        lines.append("")

    return "\n".join(lines)


def generate_openwrt_exporter(dut_names: list[str], duts_db: dict) -> str:
    """Generate exporter YAML for the openwrt pool (each DUT in isolated VLAN)."""
    lines: list[str] = []

    for dut_name in dut_names:
        hw = duts_db[dut_name]
        vlan = hw["switch_vlan_isolated"]
        tftp_path = hw["tftp_path"]
        tftp_ip = f"192.168.{vlan}.1"
        entry_name = f"labgrid-fcefyn-{dut_name}"

        lines.append(f"{entry_name}:")
        lines.append(f"  location: {hw['location']}")
        lines.append("  RawSerialPort:")
        lines.append(f"    port: \"{hw['serial_port']}\"")
        lines.append(f"    speed: {hw['serial_speed']}")
        lines.append("  PDUDaemonPort:")
        lines.append(f"    host: {hw['pdu_host']}")
        lines.append(f"    pdu: {hw['pdu_name']}")
        lines.append(f"    index: {hw['pdu_index']}")
        lines.append("  TFTPProvider:")
        lines.append(f"    internal: \"/srv/tftp/{tftp_path}\"")
        lines.append(f"    external: \"{tftp_path}\"")
        lines.append(f"    external_ip: \"{tftp_ip}\"")
        lines.append("  NetworkService:")
        lines.append(f"    address: \"192.168.1.1%vlan{vlan}\"")
        lines.append("    username: \"root\"")
        lines.append("")

    return "\n".join(lines)


def _ssh_alias_for_dut(dut_name: str, hw: dict) -> str:
    """Get SSH alias for DUT. Prefer pool-config ssh_alias, else default mapping."""
    return hw.get("ssh_alias") or DEFAULT_SSH_ALIAS.get(
        dut_name,
        dut_name.replace("_", "-"),
    )


def generate_dut_proxy_config(
    dut_names: list[str],
    duts_db: dict,
    openwrt_duts: list[str] | None = None,
    libremesh_duts: list[str] | None = None,
) -> str:
    """Generate dut-proxy.yaml for labgrid-dut-proxy (SSH alias -> vlan/ip per mode).

    When both openwrt_duts and libremesh_duts are provided (hybrid mode), each device
    entry includes an `active` key reflecting its current pool assignment.  labgrid-dut-proxy
    uses `active` with priority over the global labgrid-vlan-mode file, so SSH works
    transparently across both pools without manual mode changes.
    """
    is_hybrid = bool(openwrt_duts) and bool(libremesh_duts)
    openwrt_set = set(openwrt_duts or [])
    libremesh_set = set(libremesh_duts or [])

    header_comment = (
        "# labgrid-dut-proxy device map. Generated from pool-config.\n"
        "# device_id = SSH alias (e.g. belkin-1). Used by ProxyCommand in ~/.ssh/config.\n"
    )
    if is_hybrid:
        header_comment += (
            "# hybrid mode: 'active' key reflects current pool assignment and takes\n"
            "# priority over labgrid-vlan-mode in labgrid-dut-proxy.\n"
        )

    lines = header_comment.splitlines()
    lines += ["", "devices:"]

    for dut_name in dut_names:
        hw = duts_db[dut_name]
        alias = _ssh_alias_for_dut(dut_name, hw)
        vlan = hw["switch_vlan_isolated"]
        fixed_ip = hw.get("libremesh_fixed_ip", "")
        lines.append(f"  {alias}:")
        lines.append(f"    isolated: {{ vlan: {vlan}, ip: \"192.168.1.1\" }}")
        lines.append(f"    mesh: {{ vlan: {VLAN_MESH}, ip: \"{fixed_ip}\" }}")
        if is_hybrid:
            if dut_name in openwrt_set:
                lines.append(f"    active: {{ vlan: {vlan}, ip: \"192.168.1.1\" }}")
            elif dut_name in libremesh_set:
                lines.append(f"    active: {{ vlan: {VLAN_MESH}, ip: \"{fixed_ip}\" }}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Switch configuration for hybrid mode
# ---------------------------------------------------------------------------

def _get_port_assignments(
    openwrt_duts: list[str],
    libremesh_duts: list[str],
    duts_db: dict,
) -> tuple[list[tuple[int, str, int]], set[int]]:
    """Return (port_assignments, active_isolated_vlans)."""
    active_isolated_vlans: set[int] = set()
    port_assignments: list[tuple[int, str, int]] = []

    for dut_name in openwrt_duts:
        hw = duts_db[dut_name]
        vlan = hw["switch_vlan_isolated"]
        active_isolated_vlans.add(vlan)
        port_assignments.append((hw["switch_port"], "isolated", vlan))
        if "switch_port_poe" in hw:
            port_assignments.append((hw["switch_port_poe"], "isolated", vlan))

    for dut_name in libremesh_duts:
        hw = duts_db[dut_name]
        vlan = hw["switch_vlan_isolated"]
        port_assignments.append((hw["switch_port"], "mesh", vlan))
        if "switch_port_poe" in hw:
            port_assignments.append((hw["switch_port_poe"], "mesh", vlan))

    return port_assignments, active_isolated_vlans


def compute_desired_hybrid_state(
    openwrt_duts: list[str],
    libremesh_duts: list[str],
    duts_db: dict,
    uplink_ports: list[int],
) -> tuple[dict, list[int]]:
    """
    Compute desired hybrid state as (ports dict, uplink_tagged_vlans list).
    ports: {"11": {"pool": "libremesh", "vlan": 200}, ...}
    """
    port_assignments, active_isolated_vlans = _get_port_assignments(
        openwrt_duts, libremesh_duts, duts_db
    )
    ports: dict = {}
    for port, pool, isolated_vlan in port_assignments:
        vlan = VLAN_MESH if pool == "mesh" else isolated_vlan
        ports[str(port)] = {"pool": pool, "vlan": vlan}

    uplink_tagged_vlans = sorted(active_isolated_vlans)
    if libremesh_duts:
        uplink_tagged_vlans.append(VLAN_MESH)
        uplink_tagged_vlans = sorted(set(uplink_tagged_vlans))

    return ports, uplink_tagged_vlans


def build_hybrid_switch_commands(
    openwrt_duts: list[str],
    libremesh_duts: list[str],
    duts_db: dict,
    uplink_ports: list[int],
    ports_to_include: set[int] | None = None,
    include_uplinks: bool = True,
) -> list[str]:
    """Build switch CLI commands for hybrid VLAN assignment.

    Delegates vendor-specific command building to the driver.
    """
    port_assignments, active_isolated_vlans = _get_port_assignments(
        openwrt_duts, libremesh_duts, duts_db
    )

    driver = get_switch_driver()
    return driver.build_hybrid_commands(
        port_assignments=port_assignments,
        active_isolated_vlans=active_isolated_vlans,
        has_libremesh_duts=bool(libremesh_duts),
        uplink_ports=uplink_ports,
        vlan_mesh=VLAN_MESH,
        ports_to_include=ports_to_include,
        include_uplinks=include_uplinks,
    )


# ---------------------------------------------------------------------------
# Testbed mode detection
# ---------------------------------------------------------------------------

def detect_mode(pools: dict) -> str:
    openwrt_duts = pools.get("openwrt", {}).get("duts", [])
    libremesh_duts = pools.get("libremesh", {}).get("duts", [])
    if openwrt_duts and libremesh_duts:
        return "hybrid"
    if openwrt_duts:
        return "openwrt-only"
    if libremesh_duts:
        return "libremesh-only"
    return "empty"


# ---------------------------------------------------------------------------
# Pool state (track which DUTs belong to which pool for rebalance detection)
# ---------------------------------------------------------------------------

def load_pool_state() -> dict:
    """Load last-applied pool assignments from state file."""
    path = _get_config_path("labgrid-pool-state.yaml")
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def save_pool_state(openwrt_duts: list[str], libremesh_duts: list[str]) -> None:
    path = _get_config_path("labgrid-pool-state.yaml")
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "openwrt": sorted(openwrt_duts),
        "libremesh": sorted(libremesh_duts),
    }
    with open(path, "w") as f:
        yaml.dump(state, f, default_flow_style=False)


def get_duts_changing_pool(
    openwrt_duts: list[str],
    libremesh_duts: list[str],
) -> dict[str, tuple[str, str]]:
    """
    Return dict of DUTs that changed pool: {dut_name: (old_pool, new_pool)}.
    old_pool/new_pool are 'openwrt', 'libremesh', or 'unassigned'.
    """
    prev = load_pool_state()
    prev_ow = set(prev.get("openwrt", []))
    prev_lm = set(prev.get("libremesh", []))
    new_ow = set(openwrt_duts)
    new_lm = set(libremesh_duts)

    changes: dict[str, tuple[str, str]] = {}
    all_duts = prev_ow | prev_lm | new_ow | new_lm
    for dut in all_duts:
        old = "openwrt" if dut in prev_ow else ("libremesh" if dut in prev_lm else "unassigned")
        new = "openwrt" if dut in new_ow else ("libremesh" if dut in new_lm else "unassigned")
        if old != new and old != "unassigned":
            changes[dut] = (old, new)
    return changes


# ---------------------------------------------------------------------------
# DUT-in-use safety check
# ---------------------------------------------------------------------------

def _query_coordinator_places(coordinator_url: str) -> dict[str, str]:
    """
    Query a labgrid coordinator for place acquisition status.
    Returns {place_name: status} where status is 'acquired', 'reserved', etc.
    Returns empty dict if coordinator is unreachable.
    """
    env = os.environ.copy()
    if not coordinator_url.startswith("ws://"):
        coordinator_url = f"ws://{coordinator_url}"
    env["LG_COORDINATOR"] = coordinator_url

    try:
        result = subprocess.run(
            ["labgrid-client", "places", "-v"],
            capture_output=True, text=True, timeout=15, env=env,
        )
    except FileNotFoundError:
        logger.warning("labgrid-client not found, cannot check place status")
        return {}
    except subprocess.TimeoutExpired:
        logger.warning("Timeout querying coordinator %s", coordinator_url)
        return {}

    if result.returncode != 0:
        logger.warning(
            "labgrid-client places failed for %s: %s",
            coordinator_url, result.stderr.strip(),
        )
        return {}

    places: dict[str, str] = {}
    current_place = None
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("Place '"):
            current_place = stripped.split("'")[1]
        elif current_place and "acquired:" in stripped.lower():
            value = stripped.split(":", 1)[1].strip()
            if value and value.lower() not in ("", "none"):
                places[current_place] = "acquired"
            current_place = None
    return places


def check_duts_in_use(
    changing_duts: dict[str, tuple[str, str]],
    coordinators: dict[str, str],
) -> list[str]:
    """
    Check if any DUTs that are changing pool are currently in use.
    Returns list of error messages (empty = all clear).
    """
    if not changing_duts:
        return []

    errors: list[str] = []
    coord_places: dict[str, dict[str, str]] = {}

    for pool_name, coord_url in coordinators.items():
        duts_leaving_this_pool = [
            dut for dut, (old, _new) in changing_duts.items() if old == pool_name
        ]
        if not duts_leaving_this_pool:
            continue

        if pool_name not in coord_places:
            coord_places[pool_name] = _query_coordinator_places(coord_url)

        acquired = coord_places[pool_name]
        for dut in duts_leaving_this_pool:
            place_name = f"labgrid-fcefyn-{dut}"
            if place_name in acquired:
                errors.append(
                    f"DUT '{dut}' (place '{place_name}') is acquired on "
                    f"coordinator {coord_url} — cannot move to another pool"
                )
    return errors


# ---------------------------------------------------------------------------
# Deploy local: write to /etc/labgrid and manage systemd services
# ---------------------------------------------------------------------------

def _install_hybrid_units() -> bool:
    """Install hybrid exporter systemd units if not already present."""
    templates_dir = CONFIG_DIR / "templates"
    units = {
        f"{HYBRID_SERVICE_OPENWRT}.service": templates_dir / "labgrid-exporter-openwrt.service",
        f"{HYBRID_SERVICE_LIBREMESH}.service": templates_dir / "labgrid-exporter-libremesh.service",
    }
    installed_any = False
    for unit_name, source in units.items():
        dest = SYSTEMD_DIR / unit_name
        if dest.exists():
            continue
        if not source.exists():
            logger.error("Hybrid unit source not found: %s", source)
            return False
        logger.info("Installing %s → %s", source, dest)
        try:
            shutil.copy2(source, dest)
            installed_any = True
        except PermissionError:
            logger.error(
                "Permission denied writing %s. Run with sudo or "
                "install the units manually.", dest,
            )
            return False

    if installed_any:
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        logger.info("systemd daemon-reload done")
    return True


def _systemctl(action: str, service: str) -> bool:
    result = subprocess.run(
        ["systemctl", action, service],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        logger.warning(
            "systemctl %s %s failed: %s", action, service, result.stderr.strip(),
        )
        return False
    return True


def _stop_single_exporter() -> None:
    """Stop the single labgrid-exporter service used in non-hybrid modes."""
    result = subprocess.run(
        ["systemctl", "is-active", f"{SINGLE_SERVICE}.service"],
        capture_output=True, text=True,
    )
    if result.stdout.strip() == "active":
        logger.info("Stopping single exporter (%s) for hybrid mode", SINGLE_SERVICE)
        _systemctl("stop", f"{SINGLE_SERVICE}.service")


def _stop_hybrid_exporters() -> None:
    """Stop hybrid exporter services when switching to single-exporter mode."""
    for svc in (HYBRID_SERVICE_OPENWRT, HYBRID_SERVICE_LIBREMESH):
        result = subprocess.run(
            ["systemctl", "is-active", f"{svc}.service"],
            capture_output=True, text=True,
        )
        if result.stdout.strip() == "active":
            logger.info("Stopping hybrid exporter (%s) for single-exporter mode", svc)
            _systemctl("stop", f"{svc}.service")


def deploy_local(
    mode: str,
    lm_exporter: str,
    ow_exporter: str,
    dut_proxy_yaml: str = "",
) -> bool:
    """
    Write exporter configs to /etc/labgrid/ and restart the appropriate services.
    Enables/disables services so the last mode persists across host reboots.
    """
    if mode == "hybrid":
        if not _install_hybrid_units():
            return False

        _stop_single_exporter()
        _systemctl("disable", f"{SINGLE_SERVICE}.service")

        if lm_exporter:
            dest = EXPORTER_DIR / "exporter-libremesh.yaml"
            dest.write_text(lm_exporter)
            logger.info("Written: %s", dest)

        if ow_exporter:
            dest = EXPORTER_DIR / "exporter-openwrt.yaml"
            dest.write_text(ow_exporter)
            logger.info("Written: %s", dest)
        else:
            stale = EXPORTER_DIR / "exporter-openwrt.yaml"
            if stale.exists():
                stale.unlink()
                logger.info("Removed stale: %s", stale)

        if dut_proxy_yaml:
            dest = EXPORTER_DIR / "dut-proxy.yaml"
            dest.write_text(dut_proxy_yaml)
            logger.info("Written: %s", dest)

        if lm_exporter:
            _systemctl("enable", f"{HYBRID_SERVICE_LIBREMESH}.service")
            _systemctl("restart", f"{HYBRID_SERVICE_LIBREMESH}.service")
            logger.info("Restarted %s", HYBRID_SERVICE_LIBREMESH)
        else:
            _systemctl("stop", f"{HYBRID_SERVICE_LIBREMESH}.service")
            _systemctl("disable", f"{HYBRID_SERVICE_LIBREMESH}.service")

        if ow_exporter:
            _systemctl("enable", f"{HYBRID_SERVICE_OPENWRT}.service")
            _systemctl("restart", f"{HYBRID_SERVICE_OPENWRT}.service")
            logger.info("Restarted %s", HYBRID_SERVICE_OPENWRT)
        else:
            _systemctl("stop", f"{HYBRID_SERVICE_OPENWRT}.service")
            _systemctl("disable", f"{HYBRID_SERVICE_OPENWRT}.service")

    elif mode == "libremesh-only":
        _stop_hybrid_exporters()
        _systemctl("disable", f"{HYBRID_SERVICE_OPENWRT}.service")
        _systemctl("disable", f"{HYBRID_SERVICE_LIBREMESH}.service")
        dest = EXPORTER_DIR / "exporter.yaml"
        dest.write_text(lm_exporter)
        logger.info("Written: %s", dest)
        _systemctl("enable", f"{SINGLE_SERVICE}.service")
        _systemctl("restart", f"{SINGLE_SERVICE}.service")
        logger.info("Restarted %s", SINGLE_SERVICE)

    elif mode == "openwrt-only":
        _stop_hybrid_exporters()
        _systemctl("disable", f"{HYBRID_SERVICE_OPENWRT}.service")
        _systemctl("disable", f"{HYBRID_SERVICE_LIBREMESH}.service")
        dest = EXPORTER_DIR / "exporter.yaml"
        dest.write_text(ow_exporter)
        logger.info("Written: %s", dest)
        _systemctl("enable", f"{SINGLE_SERVICE}.service")
        _systemctl("restart", f"{SINGLE_SERVICE}.service")
        logger.info("Restarted %s", SINGLE_SERVICE)

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate labgrid exporter configs from pool-config.yaml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        default=str(POOL_CONFIG_PATH),
        help=f"Path to pool-config.yaml (default: {POOL_CONFIG_PATH})",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Print generated exporter configs and switch commands (no changes)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write exporter files and configure the switch",
    )
    parser.add_argument(
        "--no-switch",
        action="store_true",
        help="Skip switch SSH configuration (write exporter files only)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Always apply full switch config (ignore state file, no differential). "
             "Also skips DUT-in-use safety check.",
    )
    parser.add_argument(
        "--export-to-configs",
        action="store_true",
        help="Write exporter YAMLs and dut-proxy.yaml to configs/ for manual Ansible deploy. "
             "Does not deploy to /etc/labgrid/ or restart services.",
    )
    parser.add_argument(
        "--ansible-export-dir",
        metavar="PATH",
        help="Also write exporter and dut-proxy files to ansible files/exporter/<host>/",
    )
    parser.add_argument(
        "--no-gateway",
        action="store_true",
        help="Skip DUT gateway update via SSH after switch configuration",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.generate and not args.apply:
        parser.print_help()
        return 1

    config_path = Path(args.config)
    config = load_pool_config(config_path)
    out_dir = config_path.parent

    errors = validate_config(config)
    if errors:
        for err in errors:
            logger.error("Config error: %s", err)
        return 2

    duts_db = config["duts"]
    pools = config.get("pools", {})
    openwrt_duts = pools.get("openwrt", {}).get("duts", [])
    libremesh_duts = pools.get("libremesh", {}).get("duts", [])
    switch_cfg = config.get("switch", {})
    uplink_ports = switch_cfg.get("uplink_ports", [])

    mode = detect_mode(pools)
    logger.info("Detected testbed mode: %s", mode)
    logger.info("  OpenWrt pool:   %s", openwrt_duts or "(empty)")
    logger.info("  LibreMesh pool: %s", libremesh_duts or "(empty)")

    lm_exporter = generate_libremesh_exporter(libremesh_duts, duts_db) if libremesh_duts else ""
    ow_exporter = generate_openwrt_exporter(openwrt_duts, duts_db) if openwrt_duts else ""
    all_pool_duts = sorted(set(openwrt_duts + libremesh_duts))
    dut_proxy_yaml = (
        generate_dut_proxy_config(
            all_pool_duts, duts_db,
            openwrt_duts=openwrt_duts,
            libremesh_duts=libremesh_duts,
        )
        if all_pool_duts else ""
    )
    desired_ports, desired_uplink_vlans = compute_desired_hybrid_state(
        openwrt_duts, libremesh_duts, duts_db, uplink_ports
    )
    switch_cmds = build_hybrid_switch_commands(
        openwrt_duts, libremesh_duts, duts_db, uplink_ports
    )

    if args.generate:
        if lm_exporter:
            print("=== exporter-libremesh.yaml ===")
            print(lm_exporter)
        if ow_exporter:
            print("=== exporter-openwrt.yaml ===")
            print(ow_exporter)
        if dut_proxy_yaml:
            print("=== dut-proxy.yaml ===")
            print(dut_proxy_yaml)
        print("=== Switch commands ===")
        for cmd in switch_cmds:
            print(f"  {cmd}")
        return 0

    if args.apply:
        coordinators = config.get("coordinators", {})

        # Safety check: verify DUTs changing pools are not in use (when deploying)
        if not args.export_to_configs and not args.force:
            changing = get_duts_changing_pool(openwrt_duts, libremesh_duts)
            if changing:
                logger.info(
                    "DUTs changing pool: %s",
                    {d: f"{old}→{new}" for d, (old, new) in changing.items()},
                )
                in_use_errors = check_duts_in_use(changing, coordinators)
                if in_use_errors:
                    for err in in_use_errors:
                        logger.error(err)
                    logger.error(
                        "Aborting: DUTs are in use. Wait for them to be released, "
                        "or use --force to skip this check."
                    )
                    return 5

        # Write to configs/ only when --export-to-configs (for manual Ansible flow)
        if args.export_to_configs:
            if lm_exporter:
                out_file = out_dir / "exporter-libremesh.yaml"
                out_file.write_text(lm_exporter)
                logger.info("Written: %s", out_file)
            if ow_exporter:
                out_file = out_dir / "exporter-openwrt.yaml"
                out_file.write_text(ow_exporter)
                logger.info("Written: %s", out_file)
            else:
                stale = out_dir / "exporter-openwrt.yaml"
                if stale.exists():
                    stale.unlink()
                    logger.info("Removed stale exporter-openwrt.yaml (openwrt pool is empty)")
            if dut_proxy_yaml:
                out_file = out_dir / "dut-proxy.yaml"
                out_file.write_text(dut_proxy_yaml)
                logger.info("Written: %s", out_file)
                if args.ansible_export_dir:
                    ansible_dir = Path(args.ansible_export_dir)
                    ansible_dir.mkdir(parents=True, exist_ok=True)
                    ansible_file = ansible_dir / "dut-proxy.yaml"
                    ansible_file.write_text(dut_proxy_yaml)
                    logger.info("Written: %s", ansible_file)

        # Switch configuration
        if not args.no_switch:
            password = load_switch_password()
            if not password:
                logger.error(
                    "Switch password not found. Set POE_SWITCH_PASSWORD in "
                    "~/.config/poe_switch_control.conf or via env var."
                )
                return 3

            apply_cmds = switch_cmds
            if (
                not args.force
                and load_switch_state
                and save_hybrid_state
                and is_hybrid_state_valid_for_diff
            ):
                current_state = load_switch_state()
                if is_hybrid_state_valid_for_diff(current_state):
                    current_ports = current_state.get("hybrid_ports") or {}
                    current_uplink_vlans = current_state.get("uplink_tagged_vlans") or []
                    ports_changed: set[int] = set()
                    for port_str, desired_cfg in desired_ports.items():
                        current_cfg = current_ports.get(port_str)
                        if current_cfg != desired_cfg:
                            ports_changed.add(int(port_str))
                    uplinks_changed = sorted(desired_uplink_vlans) != sorted(
                        current_uplink_vlans
                    )
                    if not ports_changed and not uplinks_changed:
                        # State matches desired, but switch may be out of sync (e.g. from
                        # a prior differential that only touched some ports while others were
                        # already wrong). Apply full config to correct any staleness.
                        logger.info(
                            "State matches desired; applying full config to ensure switch sync"
                        )
                        apply_cmds = switch_cmds
                    else:
                        apply_cmds = build_hybrid_switch_commands(
                            openwrt_duts,
                            libremesh_duts,
                            duts_db,
                            uplink_ports,
                            ports_to_include=ports_changed,
                            include_uplinks=uplinks_changed,
                        )
                        logger.info(
                            "Differential apply: %d ports, uplinks=%s",
                            len(ports_changed),
                            uplinks_changed,
                        )
            if apply_cmds:
                try:
                    client = SwitchClient(
                        host=switch_cfg.get("host", "192.168.0.1"),
                        user=switch_cfg.get("user", "admin"),
                        password=password,
                    )
                except ValueError as e:
                    logger.error("%s", e)
                    return 3

                success = client.send_config_commands(apply_cmds)
                if not success:
                    logger.error("Switch configuration failed")
                    return 4
                if save_hybrid_state and (openwrt_duts or libremesh_duts):
                    save_hybrid_state(desired_ports, desired_uplink_vlans)
            else:
                success = True
        else:
            logger.info("Switch configuration skipped (--no-switch)")
            logger.info("Would send %d commands to switch", len(switch_cmds))

        # Deploy to /etc/labgrid/ and restart services (default); or show Next steps
        if not args.export_to_configs:
            if not deploy_local(mode, lm_exporter, ow_exporter, dut_proxy_yaml or ""):
                logger.error("Deploy failed")
                return 6
            save_pool_state(openwrt_duts, libremesh_duts)
            logger.info("Deploy complete. Mode: %s", mode)
        else:
            save_pool_state(openwrt_duts, libremesh_duts)
            print()
            print("Next steps:")
            if mode in ("libremesh-only", "hybrid"):
                print("  1. Deploy libremesh exporter and dut-proxy via Ansible:")
                print("     cp configs/exporter-libremesh.yaml "
                      "<libremesh-tests>/ansible/files/exporter/labgrid-fcefyn/exporter.yaml")
                if dut_proxy_yaml:
                    print("     cp configs/dut-proxy.yaml "
                          "<libremesh-tests>/ansible/files/exporter/labgrid-fcefyn/dut-proxy.yaml")
                print("     cd <libremesh-tests>/ansible && ansible-playbook -i inventory.ini "
                      "playbook_labgrid.yml --tags export")
            if mode in ("openwrt-only", "hybrid"):
                print("  2. Deploy openwrt exporter via Ansible (libremesh-tests repo):")
                print("     cp configs/exporter-openwrt.yaml "
                      "<libremesh-tests>/ansible/files/exporter/labgrid-fcefyn/exporter.yaml")
                print("     cd <libremesh-tests>/ansible && ansible-playbook -i inventory.ini "
                      "playbook_labgrid.yml --tags export")
            print()
            print("  Tip: Omit --export-to-configs to deploy directly to /etc/labgrid/.")

        # Update DUT gateways via parallel SSH
        if not args.no_gateway and not args.no_switch:
            dut_modes: dict[str, str] = {}
            for dut in openwrt_duts:
                dut_modes[dut] = "isolated"
            for dut in libremesh_duts:
                dut_modes[dut] = "mesh"
            if dut_modes:
                update_dut_gateways(dut_modes, config_path)

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
