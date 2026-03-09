#!/usr/bin/env bash
# testbed-mode - Switch the FCEFYN testbed between operational modes.
#
# Run as:  ./testbed-mode.sh <mode>   OR   sudo ./testbed-mode.sh <mode>
#   All three modes work with either. Hybrid prompts for sudo when needed if run without.
#
# Usage:
#   testbed-mode.sh libremesh [--dry-run] [--no-switch]
#       Deploy libremesh-tests config via Ansible (VLAN 200 only).
#
#   testbed-mode.sh openwrt [--dry-run] [--no-switch]
#       Deploy openwrt-tests config via Ansible (isolated VLANs 100-108).
#       Requires openwrt-tests repo path (OPENWRT_TESTS_DIR or --openwrt-dir).
#
#   testbed-mode.sh hybrid [--dry-run] [--no-switch]
#       Apply pool-config.yaml split via pool-manager.py --deploy-local.
#       Writes exporter configs to /etc/labgrid/, configures switch, and
#       restarts two exporter services (openwrt + libremesh).
#       No Ansible is used. Edit configs/pool-config.yaml first.
#
#   --no-switch          Skip switch VLAN config (only deploy exporter/config).
#                       Useful when switch is already correct or unavailable.
#   --ask-become-pass    Pass -K to ansible-playbook (prompt for sudo password).
#                       Use if the user does not have passwordless sudo.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
POOL_CONFIG="${REPO_ROOT}/configs/pool-config.yaml"

# Paths to the Ansible playbooks (adjust to your local setup)
LIBREMESH_ANSIBLE="${LIBREMESH_TESTS_DIR:-${HOME}/pi/fork-openwrt-tests}/ansible"
OPENWRT_ANSIBLE="${OPENWRT_TESTS_DIR:-${HOME}/pi/openwrt-tests}/ansible"

INVENTORY="inventory.ini"
DRY_RUN=false
NO_SWITCH=false
MODE=""
OPENWRT_DIR_OVERRIDE=""
ANSIBLE_EXTRA_ARGS=()

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        libremesh|openwrt|hybrid)
            MODE="$1"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-switch)
            NO_SWITCH=true
            shift
            ;;
        --ask-become-pass)
            ANSIBLE_EXTRA_ARGS+=("--ask-become-pass")
            shift
            ;;
        --openwrt-dir)
            OPENWRT_DIR_OVERRIDE="$2"
            shift 2
            ;;
        -h|--help)
            sed -n '/^# testbed-mode/,/^[^#]/p' "$0" | head -n -1 | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$MODE" ]]; then
    echo "Usage: testbed-mode.sh <libremesh|openwrt|hybrid> [--dry-run] [--no-switch] [--ask-become-pass]" >&2
    exit 1
fi

[[ -n "$OPENWRT_DIR_OVERRIDE" ]] && OPENWRT_ANSIBLE="${OPENWRT_DIR_OVERRIDE}/ansible"

log() { echo "[testbed-mode] $*"; }
run_or_dry() {
    if $DRY_RUN; then
        echo "[DRY-RUN] $*"
    else
        "$@"
    fi
}

# ---------------------------------------------------------------------------
# Mode: libremesh
# ---------------------------------------------------------------------------
if [[ "$MODE" == "libremesh" ]]; then
    log "Switching to libremesh-only mode (VLAN 200 for all DUTs)"

    log "Stopping hybrid exporters (use single labgrid-exporter)..."
    run_or_dry sudo systemctl stop labgrid-exporter-openwrt labgrid-exporter-libremesh 2>/dev/null || true
    run_or_dry sudo systemctl disable labgrid-exporter-openwrt labgrid-exporter-libremesh 2>/dev/null || true

    if $NO_SWITCH; then
        log "Skipping switch config (--no-switch)"
    else
        log "Applying mesh VLAN preset on switch..."
        run_or_dry python3 "${SCRIPT_DIR}/switch/switch_vlan_preset.py" mesh
    fi

    log "Deploying libremesh exporter via Ansible..."
    run_or_dry ansible-playbook \
        -i "${LIBREMESH_ANSIBLE}/${INVENTORY}" \
        "${LIBREMESH_ANSIBLE}/playbook_labgrid.yml" \
        --tags export \
        "${ANSIBLE_EXTRA_ARGS[@]}"

    log "Done. Testbed is in libremesh-only mode."

# ---------------------------------------------------------------------------
# Mode: openwrt
# ---------------------------------------------------------------------------
elif [[ "$MODE" == "openwrt" ]]; then
    log "Switching to openwrt-only mode (isolated VLANs per DUT)"

    if [[ ! -d "$OPENWRT_ANSIBLE" ]]; then
        echo "ERROR: openwrt-tests Ansible directory not found: ${OPENWRT_ANSIBLE}" >&2
        echo "Set OPENWRT_TESTS_DIR or pass --openwrt-dir <path>" >&2
        exit 1
    fi

    log "Stopping hybrid exporters (use single labgrid-exporter)..."
    run_or_dry sudo systemctl stop labgrid-exporter-openwrt labgrid-exporter-libremesh 2>/dev/null || true
    run_or_dry sudo systemctl disable labgrid-exporter-openwrt labgrid-exporter-libremesh 2>/dev/null || true

    if $NO_SWITCH; then
        log "Skipping switch config (--no-switch)"
    else
        log "Applying isolated VLAN preset on switch..."
        run_or_dry python3 "${SCRIPT_DIR}/switch/switch_vlan_preset.py" isolated
    fi

    log "Deploying openwrt exporter via Ansible..."
    run_or_dry ansible-playbook \
        -i "${OPENWRT_ANSIBLE}/${INVENTORY}" \
        "${OPENWRT_ANSIBLE}/playbook_labgrid.yml" \
        --tags export \
        "${ANSIBLE_EXTRA_ARGS[@]}"

    log "Done. Testbed is in openwrt-only mode."

# ---------------------------------------------------------------------------
# Mode: hybrid (pool-manager only, no Ansible)
# ---------------------------------------------------------------------------
elif [[ "$MODE" == "hybrid" ]]; then
    log "Switching to hybrid mode (pool-config.yaml defines DUT split)"
    log "Config: ${POOL_CONFIG}"

    POOL_MANAGER_ARGS=("--apply" "--deploy-local")
    $NO_SWITCH && POOL_MANAGER_ARGS+=("--no-switch")

    log "Applying pool manager (switch + deploy-local)..."
    # deploy-local writes to /etc/labgrid/ and restarts systemd services; requires sudo
    run_or_dry sudo python3 "${SCRIPT_DIR}/switch/pool-manager.py" \
        --config "${POOL_CONFIG}" \
        "${POOL_MANAGER_ARGS[@]}"

    log "Done. Testbed is in hybrid mode."
fi
