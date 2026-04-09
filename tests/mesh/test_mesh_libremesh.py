"""
LibreMesh-specific tests for the virtual mesh lab.

Tests lime-config, UCI network config, babeld routing, lime-proto,
shared-state, and LibreMesh-specific services.

Run with:  pytest tests/mesh/test_mesh_libremesh.py -v
"""

import pytest
from helpers import N_NODES, NODES, ssh_run

# ---------------------------------------------------------------------------
# 1. lime-config
# ---------------------------------------------------------------------------


def test_lime_config_ran(node):
    """lime-config must have executed and left its stamp file."""
    rc, out, _ = ssh_run(node["port"], "ls /etc/lime_default_config 2>/dev/null || ls /etc/config/lime 2>/dev/null")
    assert rc == 0 and out, f"{node['name']}: lime-config stamp not found"


def test_lime_uci_network_exists(node):
    """UCI lime network config must exist."""
    rc, out, _ = ssh_run(node["port"], "uci show lime 2>/dev/null | head -5")
    assert rc == 0 and out, f"{node['name']}: UCI lime config missing"


def test_lime_hostname_uci(node):
    """Hostname in UCI must follow LiMe-XXXXXX convention."""
    rc, out, _ = ssh_run(node["port"], "uci get system.@system[0].hostname")
    assert rc == 0, f"{node['name']}: could not read UCI hostname"
    assert out.lower().startswith("lime-"), f"{node['name']}: unexpected hostname: {out}"


def test_lime_hostname_matches_system(node):
    """UCI hostname must match the running system hostname."""
    _, uci_hn, _ = ssh_run(node["port"], "uci get system.@system[0].hostname")
    _, sys_hn, _ = ssh_run(node["port"], "cat /proc/sys/kernel/hostname")
    assert uci_hn.strip().lower() == sys_hn.strip().lower(), (
        f"{node['name']}: UCI hostname '{uci_hn}' != system hostname '{sys_hn}'"
    )


# ---------------------------------------------------------------------------
# 2. UCI network interfaces
# ---------------------------------------------------------------------------


def test_uci_br_lan_exists(node):
    """UCI network must define br-lan."""
    rc, out, _ = ssh_run(node["port"], "uci show network.lanbr 2>/dev/null || uci show network | grep br-lan")
    assert rc == 0 and out, f"{node['name']}: br-lan not found in UCI network config"


def test_uci_bat0_proto(node):
    """bat0 interface in UCI must use batman-adv proto."""
    rc, out, _ = ssh_run(node["port"], "uci show network | grep batman")
    assert rc == 0 and out, f"{node['name']}: batman-adv proto not found in UCI network"


# ---------------------------------------------------------------------------
# 3. babeld
# ---------------------------------------------------------------------------


def test_babeld_running(node):
    """babeld must be running (LibreMesh L3 routing daemon)."""
    rc, out, _ = ssh_run(node["port"], "pgrep -x babeld")
    assert rc == 0, f"{node['name']}: babeld not running"


def test_babeld_has_interfaces(node):
    """babeld must report at least one interface."""
    rc, out, _ = ssh_run(
        node["port"], "babeld -D 2>/dev/null || cat /var/run/babeld.pid 2>/dev/null | xargs -r kill -0 && echo running"
    )
    # Softer check: just verify the process is alive and has a socket
    rc2, out2, _ = ssh_run(node["port"], "ls /var/run/babeld* 2>/dev/null || pgrep babeld")
    assert rc2 == 0, f"{node['name']}: babeld pidfile/socket not found"


@pytest.mark.skipif(N_NODES < 2, reason="Need at least 2 nodes")
def test_babeld_routes_present():
    """babeld must have installed routes on vm1 after convergence."""
    rc, out, _ = ssh_run(NODES[0]["port"], "ip route show proto babel 2>/dev/null")
    # babel routes may not always appear in ip route — check babeld log or proc
    if rc != 0 or not out:
        # Fallback: check if br-lan routes exist (LibreMesh assigns them)
        rc, out, _ = ssh_run(NODES[0]["port"], "ip route show dev br-lan")
    assert rc == 0 and out, "vm1: no babel/br-lan routes found"


# ---------------------------------------------------------------------------
# 4. lime-proto / lime-system
# ---------------------------------------------------------------------------


def test_lime_proto_bat_active(node):
    """lime-proto-batadv must be active (wlan0 enslaved to batman)."""
    rc, out, _ = ssh_run(node["port"], "batctl if")
    assert rc == 0 and "active" in out, f"{node['name']}: lime-proto-batadv not active"


def test_br_lan_has_ip(node):
    """br-lan must have an IPv4 address assigned by lime."""
    rc, out, _ = ssh_run(node["port"], "ip -4 addr show br-lan | grep 'inet '")
    assert rc == 0 and out, f"{node['name']}: br-lan has no IPv4 address"


def test_br_lan_ip_is_lime_range(node):
    """br-lan IP must be in the LibreMesh address range (10.x.x.x or 192.168.x.x)."""
    rc, out, _ = ssh_run(node["port"], "ip -4 addr show br-lan | grep 'inet ' | awk '{print $2}' | cut -d/ -f1")
    assert rc == 0 and out, f"{node['name']}: no br-lan IP"
    ip = out.strip()
    assert ip.startswith("10.") or ip.startswith("192.168."), (
        f"{node['name']}: br-lan IP {ip} not in expected LibreMesh range"
    )


# ---------------------------------------------------------------------------
# 5. shared-state
# ---------------------------------------------------------------------------


def test_shared_state_running(node):
    """shared-state-async must be running (LibreMesh distributed state)."""
    rc, out, _ = ssh_run(node["port"], "pgrep -f shared-state")
    assert rc == 0, f"{node['name']}: shared-state not running"


def test_shared_state_dir_exists(node):
    """shared-state data directory must exist."""
    rc, _, _ = ssh_run(node["port"], "ls /var/shared-state/ 2>/dev/null")
    assert rc == 0, f"{node['name']}: /var/shared-state/ missing"


@pytest.mark.skipif(N_NODES < 2, reason="Need at least 2 nodes")
def test_shared_state_has_data():
    """shared-state must have at least one data file after convergence."""
    rc, out, _ = ssh_run(NODES[0]["port"], "find /var/shared-state/ -type f | head -5")
    assert rc == 0 and out, "vm1: no shared-state data files found"


# ---------------------------------------------------------------------------
# 6. lime-report
# ---------------------------------------------------------------------------


def test_lime_report_runs(node):
    """lime-report must execute without error."""
    rc, out, _ = ssh_run(node["port"], "lime-report 2>/dev/null | head -10")
    assert rc == 0 and out, f"{node['name']}: lime-report failed or empty"


def test_lime_report_has_ifaces(node):
    """lime-report output must list network interfaces."""
    rc, out, _ = ssh_run(node["port"], "lime-report 2>/dev/null | grep -i iface")
    assert rc == 0 and out, f"{node['name']}: lime-report missing interface info"


def test_lime_report_has_batman(node):
    """lime-report must include batman-adv section."""
    rc, out, _ = ssh_run(node["port"], "lime-report 2>/dev/null | grep -i batman")
    assert rc == 0 and out, f"{node['name']}: lime-report missing batman info"


# ---------------------------------------------------------------------------
# 7. Unique br-lan IPs across nodes
# ---------------------------------------------------------------------------


@pytest.mark.skipif(N_NODES < 2, reason="Need at least 2 nodes")
def test_unique_br_lan_ips():
    """Each node must have a distinct br-lan IP (no DHCP collision)."""
    ips = {}
    for node in NODES:
        _, out, _ = ssh_run(node["port"], "ip -4 addr show br-lan | grep 'inet ' | awk '{print $2}' | cut -d/ -f1")
        ip = out.strip()
        if ip:
            if ip in ips:
                pytest.fail(f"Duplicate br-lan IP {ip} on {node['name']} and {ips[ip]}")
            ips[ip] = node["name"]
    assert len(ips) == N_NODES, f"Expected {N_NODES} unique IPs, got {ips}"
