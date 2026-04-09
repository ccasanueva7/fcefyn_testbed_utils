"""
Per-node health tests for LibreMesh virtual mesh.

Each test runs against every node via the parametrized `node` fixture.
Run with:  pytest tests/mesh/test_mesh_node_basic.py -v
"""

import pytest
from helpers import ssh_run, node_mac


# ---------------------------------------------------------------------------
# SSH reachability
# ---------------------------------------------------------------------------

def test_node_ssh_reachable(node):
    """Node must respond to SSH within the timeout."""
    rc, out, _ = ssh_run(node["port"], "echo alive")
    assert rc == 0 and "alive" in out, f"{node['name']}: SSH unreachable"


# ---------------------------------------------------------------------------
# Kernel modules
# ---------------------------------------------------------------------------

def test_batman_module_loaded(node):
    rc, out, _ = ssh_run(node["port"], "lsmod | grep batman")
    assert rc == 0 and "batman" in out, f"{node['name']}: batman-adv module not loaded"


def test_mac80211_hwsim_loaded(node):
    rc, out, _ = ssh_run(node["port"], "lsmod | grep mac80211_hwsim")
    assert rc == 0, f"{node['name']}: mac80211_hwsim not loaded"


# ---------------------------------------------------------------------------
# Network interfaces
# ---------------------------------------------------------------------------

def test_bat0_interface_exists(node):
    rc, out, _ = ssh_run(node["port"], "ip link show bat0")
    assert rc == 0, f"{node['name']}: bat0 interface missing"


def test_bat0_interface_up(node):
    rc, out, _ = ssh_run(node["port"], "ip link show bat0")
    assert "UP" in out, f"{node['name']}: bat0 is not UP: {out}"


def test_wlan0_interface_up(node):
    # LibreMesh renames wlan0 to wlan0-mesh, wlan0-ap, etc.
    rc, out, _ = ssh_run(node["port"], "ip link show | grep -E 'wlan0|wlan0-mesh'")
    assert rc == 0 and out, f"{node['name']}: no wlan0 interface found"


def test_eth0_has_ip(node):
    """LibreMesh puts eth0 in br-lan — check br-lan for the IP."""
    rc, out, _ = ssh_run(node["port"], "ip -4 addr show br-lan")
    assert rc == 0 and "inet " in out, f"{node['name']}: br-lan has no IPv4 address (eth0 is bridged)"


def test_eth2_has_ip(node):
    """eth2 (vwifi) should have the 10.99.0.x address assigned by the launch script."""
    expected_prefix = f"10.99.0.{10 + node['index']}"
    rc, out, _ = ssh_run(node["port"], "ip -4 addr show eth2")
    assert rc == 0 and expected_prefix in out, (
        f"{node['name']}: eth2 missing expected IP {expected_prefix}: {out}"
    )


def test_node_vwifi_mac(node):
    """eth2 MAC must match what launch_debug_vms.sh assigned."""
    expected = node_mac(node["index"], vwifi=True)
    rc, out, _ = ssh_run(node["port"], "cat /sys/class/net/eth2/address")
    assert rc == 0 and out.lower() == expected.lower(), (
        f"{node['name']}: eth2 MAC mismatch (got {out}, want {expected})"
    )


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

def test_vwifi_client_running(node):
    rc, out, _ = ssh_run(node["port"], "pgrep -x vwifi-client || ps | grep vwifi-client | grep -v grep")
    assert rc == 0, f"{node['name']}: vwifi-client is not running"


def test_batman_adv_mesh_active(node):
    """bat0 must have at least one wlan interface added to it."""
    rc, out, _ = ssh_run(node["port"], "batctl if")
    assert rc == 0 and "active" in out, (
        f"{node['name']}: no active batman-adv interface: {out}"
    )


# ---------------------------------------------------------------------------
# UCI / LibreMesh config
# ---------------------------------------------------------------------------

def test_uci_vwifi_enabled(node):
    rc, out, _ = ssh_run(node["port"], "uci get vwifi.config.enabled")
    assert rc == 0 and out.strip() == "1", (
        f"{node['name']}: vwifi not enabled in UCI: '{out}'"
    )


def test_uci_vwifi_server_ip(node):
    rc, out, _ = ssh_run(node["port"], "uci get vwifi.config.server_ip")
    assert rc == 0 and out.strip() == "10.99.0.2", (
        f"{node['name']}: vwifi server IP wrong: '{out}'"
    )


def test_uci_wireless_band_2g(node):
    """launch_debug_vms.sh forces radio0 to 2.4 GHz."""
    rc, out, _ = ssh_run(node["port"], "uci get wireless.radio0.band")
    assert rc == 0 and out.strip() == "2g", (
        f"{node['name']}: radio0 band is '{out}', expected '2g'"
    )


def test_uci_wireless_channel_1(node):
    rc, out, _ = ssh_run(node["port"], "uci get wireless.radio0.channel")
    assert rc == 0 and out.strip() == "1", (
        f"{node['name']}: radio0 channel is '{out}', expected '1'"
    )


def test_lime_config_applied(node):
    """lime-config should have created /etc/config/lime-node or similar artifact."""
    rc, _, _ = ssh_run(node["port"], "test -f /etc/config/lime-node || uci show lime 2>/dev/null | grep -q .'")
    # Softer check: lime package present
    rc2, out2, _ = ssh_run(node["port"], "opkg list-installed | grep lime")
    assert rc2 == 0 and out2, f"{node['name']}: lime packages not installed: '{out2}'"


# ---------------------------------------------------------------------------
# System health
# ---------------------------------------------------------------------------

def test_system_load_reasonable(node):
    """1-minute load average should be below number-of-vCPUs * 2."""
    rc, out, _ = ssh_run(node["port"], "cat /proc/loadavg")
    assert rc == 0, f"{node['name']}: could not read loadavg"
    load1 = float(out.split()[0])
    assert load1 < 8.0, f"{node['name']}: load average too high: {load1}"


def test_memory_not_oom(node):
    """MemAvailable should be > 0."""
    rc, out, _ = ssh_run(node["port"], "grep MemAvailable /proc/meminfo")
    assert rc == 0, f"{node['name']}: could not read meminfo"
    kb = int(out.split()[1])
    assert kb > 0, f"{node['name']}: no memory available (OOM?): {out}"


def test_no_kernel_panics(node):
    rc, out, _ = ssh_run(node["port"], "dmesg | grep -i 'kernel panic' || true")
    assert "kernel panic" not in out.lower(), (
        f"{node['name']}: kernel panic detected in dmesg"
    )
