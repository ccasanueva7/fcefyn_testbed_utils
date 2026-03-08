#!/usr/bin/env bash
# testbed-mode - Switch the FCEFYN testbed between operational modes.
#
# Usage:
#   testbed-mode.sh libremesh [--dry-run]
#       Deploy libremesh-tests config via Ansible (VLAN 200 only).
#
#   testbed-mode.sh openwrt [--dry-run]
#       Deploy openwrt-tests config via Ansible (isolated VLANs 100-108).
#       Requires openwrt-tests repo path (OPENWRT_TESTS_DIR or --openwrt-dir).
#
#   testbed-mode.sh hybrid [--dry-run] [--no-switch]
#       Apply pool-config.yaml split via pool-manager.py (switch + exporter files),
#       then deploy each exporter via Ansible.
#       Edit configs/pool-config.yaml to define the DUT split before running.

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
    echo "Usage: testbed-mode.sh <libremesh|openwrt|hybrid> [--dry-run] [--no-switch]" >&2
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

    log "Applying mesh VLAN preset on switch..."
    run_or_dry python3 "${SCRIPT_DIR}/switch_vlan_preset.py" mesh

    log "Deploying libremesh exporter via Ansible..."
    run_or_dry ansible-playbook \
        -i "${LIBREMESH_ANSIBLE}/${INVENTORY}" \
        "${LIBREMESH_ANSIBLE}/playbook_labgrid.yml" \
        --tags export

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

    log "Applying isolated VLAN preset on switch..."
    run_or_dry python3 "${SCRIPT_DIR}/switch_vlan_preset.py" isolated

    log "Deploying openwrt exporter via Ansible..."
    run_or_dry ansible-playbook \
        -i "${OPENWRT_ANSIBLE}/${INVENTORY}" \
        "${OPENWRT_ANSIBLE}/playbook_labgrid.yml" \
        --tags export

    log "Done. Testbed is in openwrt-only mode."

# ---------------------------------------------------------------------------
# Mode: hybrid
# ---------------------------------------------------------------------------
elif [[ "$MODE" == "hybrid" ]]; then
    log "Switching to hybrid mode (pool-config.yaml defines DUT split)"
    log "Config: ${POOL_CONFIG}"

    POOL_MANAGER_ARGS=("--apply")
    $NO_SWITCH && POOL_MANAGER_ARGS+=("--no-switch")

    log "Applying pool manager (switch + exporter files)..."
    run_or_dry python3 "${SCRIPT_DIR}/pool-manager.py" \
        --config "${POOL_CONFIG}" \
        "${POOL_MANAGER_ARGS[@]}"

    LM_EXPORTER="${REPO_ROOT}/configs/exporter-libremesh.yaml"
    OW_EXPORTER="${REPO_ROOT}/configs/exporter-openwrt.yaml"

    if [[ -f "$LM_EXPORTER" ]]; then
        log "Deploying libremesh exporter..."
        LIBREMESH_EXPORTER_DST="${LIBREMESH_ANSIBLE}/files/exporter/labgrid-fcefyn/exporter.yaml"
        run_or_dry cp "${LM_EXPORTER}" "${LIBREMESH_EXPORTER_DST}"
        run_or_dry ansible-playbook \
            -i "${LIBREMESH_ANSIBLE}/${INVENTORY}" \
            "${LIBREMESH_ANSIBLE}/playbook_labgrid.yml" \
            --tags export
    fi

    if [[ -f "$OW_EXPORTER" ]] && [[ -d "$OPENWRT_ANSIBLE" ]]; then
        log "Deploying openwrt exporter..."
        OW_EXPORTER_DST="${OPENWRT_ANSIBLE}/files/exporter/labgrid-fcefyn/exporter.yaml"
        run_or_dry cp "${OW_EXPORTER}" "${OW_EXPORTER_DST}"
        run_or_dry ansible-playbook \
            -i "${OPENWRT_ANSIBLE}/${INVENTORY}" \
            "${OPENWRT_ANSIBLE}/playbook_labgrid.yml" \
            --tags export
    fi

    log "Done. Testbed is in hybrid mode."
fi
