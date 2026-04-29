"""
End-to-end connectivity tests for the LibreMesh virtual mesh lab.

Tests real data-plane connectivity between nodes: ping, HTTP, DNS, services.

Run with:  pytest tests/mesh/test_mesh_connectivity.py -v
"""

import pytest
from helpers import N_NODES, NODES, ssh_run

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _brlan_ip(port: int) -> str | None:
    """Return the br-lan IPv4 of a node (LibreMesh mesh IP)."""
    rc, out, _ = ssh_run(port, "ip -4 addr show br-lan | grep 'inet ' | awk '{print $2}' | cut -d/ -f1")
    return out.strip() if rc == 0 and out.strip() else None


# ---------------------------------------------------------------------------
# 1. Ping entre nodos via br-lan (datos reales a través de la mesh)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(N_NODES < 2, reason="Need at least 2 nodes")
def test_ping_vm1_to_vm2():
    """VM1 pings VM2's br-lan IP through the mesh."""
    target = _brlan_ip(NODES[1]["port"])
    if not target:
        pytest.skip("Could not get br-lan IP of vm2")
    rc, out, _ = ssh_run(NODES[0]["port"], f"ping -c 3 -W 3 {target}")
    assert rc == 0, f"Ping vm1->vm2 ({target}) failed:\n{out}"


@pytest.mark.skipif(N_NODES < 2, reason="Need at least 2 nodes")
def test_ping_vm2_to_vm1():
    """VM2 pings VM1's br-lan IP (bidirectional)."""
    target = _brlan_ip(NODES[0]["port"])
    if not target:
        pytest.skip("Could not get br-lan IP of vm1")
    rc, out, _ = ssh_run(NODES[1]["port"], f"ping -c 3 -W 3 {target}")
    assert rc == 0, f"Ping vm2->vm1 ({target}) failed:\n{out}"


@pytest.mark.skipif(N_NODES < 3, reason="Need at least 3 nodes")
def test_ping_all_pairs():
    """Every node can ping every other node."""
    failures = []
    for src in NODES:
        for dst in NODES:
            if src["name"] == dst["name"]:
                continue
            target = _brlan_ip(dst["port"])
            if not target:
                continue
            rc, _, _ = ssh_run(src["port"], f"ping -c 2 -W 3 {target}")
            if rc != 0:
                failures.append(f"{src['name']} -> {dst['name']} ({target})")
    assert not failures, "Ping failures:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# 2. vwifi-server alcanzable desde cada nodo
# ---------------------------------------------------------------------------


def test_vwifi_server_reachable(node):
    """Each node can reach the vwifi-server at 10.99.0.2."""
    rc, out, _ = ssh_run(node["port"], "ping -c 2 -W 3 10.99.0.2")
    assert rc == 0, f"{node['name']}: cannot reach vwifi-server (10.99.0.2):\n{out}"


# ---------------------------------------------------------------------------
# 3. uhttpd responde HTTP
# ---------------------------------------------------------------------------


def test_uhttpd_responds(node):
    """uhttpd must serve a response on port 80."""
    rc, out, _ = ssh_run(node["port"], "wget -q -O- http://localhost/ 2>/dev/null | head -1")
    assert rc == 0 and out, f"{node['name']}: uhttpd not responding on port 80"


def test_uhttpd_running(node):
    rc, out, _ = ssh_run(node["port"], "pgrep -f uhttpd")
    assert rc == 0, f"{node['name']}: uhttpd not running"


# ---------------------------------------------------------------------------
# 4. dnsmasq corriendo
# ---------------------------------------------------------------------------


def test_dnsmasq_running(node):
    rc, out, _ = ssh_run(node["port"], "pgrep -x dnsmasq")
    assert rc == 0, f"{node['name']}: dnsmasq not running"


# ---------------------------------------------------------------------------
# 5. vwifi-client proceso activo
# ---------------------------------------------------------------------------


def test_vwifi_client_process(node):
    rc, out, _ = ssh_run(node["port"], "pgrep -a vwifi-client")
    assert rc == 0 and "vwifi-client" in out, f"{node['name']}: vwifi-client not running"


# ---------------------------------------------------------------------------
# 6. Hostname LibreMesh correcto
# ---------------------------------------------------------------------------


def test_lime_hostname(node):
    """Hostname must follow LibreMesh convention: LiMe-XXXXXX."""
    rc, out, _ = ssh_run(node["port"], "uci get system.@system[0].hostname")
    assert rc == 0 and out.lower().startswith("lime-"), f"{node['name']}: unexpected hostname '{out}'"


# ---------------------------------------------------------------------------
# 7. lime-report ejecuta sin errores
# ---------------------------------------------------------------------------


def test_lime_report_runs(node):
    rc, out, _ = ssh_run(node["port"], "lime-report 2>/dev/null | head -5")
    assert rc == 0 and out, f"{node['name']}: lime-report failed or returned empty"


def test_lime_report_has_hostname(node):
    rc, out, _ = ssh_run(node["port"], "lime-report 2>/dev/null | grep hostname")
    assert rc == 0 and "LiMe" in out, f"{node['name']}: lime-report missing hostname:\n{out}"


# ---------------------------------------------------------------------------
# 8. batman-adv gateway mode
# ---------------------------------------------------------------------------


def test_batman_gw_mode(node):
    rc, out, _ = ssh_run(node["port"], "batctl gw")
    assert rc == 0, f"{node['name']}: batctl gw failed"
    # Should be 'off', 'client' or 'server'
    assert any(m in out for m in ["off", "client", "server"]), f"{node['name']}: unexpected gw mode: {out}"


# ---------------------------------------------------------------------------
# 9. Tabla ARP tiene entradas de otros nodos
# ---------------------------------------------------------------------------


@pytest.mark.skipif(N_NODES < 2, reason="Need at least 2 nodes")
def test_arp_has_mesh_neighbors():
    """After ping, vm1's ARP table must have vm2's MAC."""
    # Trigger ARP by pinging first
    target = _brlan_ip(NODES[1]["port"])
    if not target:
        pytest.skip("Could not get br-lan IP of vm2")
    ssh_run(NODES[0]["port"], f"ping -c 1 -W 2 {target}")
    rc, out, _ = ssh_run(NODES[0]["port"], "ip neigh show | grep br-lan")
    assert rc == 0 and out, f"vm1 ARP table has no br-lan neighbors:\n{out}"


# ---------------------------------------------------------------------------
# 10. Tests para 5 nodos — visibilidad completa
# ---------------------------------------------------------------------------


@pytest.mark.skipif(N_NODES < 5, reason="Need at least 5 nodes")
def test_5nodes_all_see_each_other_batman():
    """With 5 nodes, every node must appear in every other's originator table."""
    failures = []
    for src in NODES:
        _, out, _ = ssh_run(src["port"], "batctl o")
        for dst in NODES:
            if src["name"] == dst["name"]:
                continue
            node_id = f"{dst['index']:06x}"
            if f"lime_{node_id}".lower() not in out.lower():
                failures.append(f"{src['name']} does not see {dst['name']}")
    assert not failures, "Batman visibility failures:\n" + "\n".join(failures)


@pytest.mark.skipif(N_NODES < 5, reason="Need at least 5 nodes")
def test_5nodes_full_mesh_ping():
    """With 5 nodes, all-pairs ping must succeed."""
    failures = []
    for src in NODES:
        for dst in NODES:
            if src["name"] == dst["name"]:
                continue
            target = _brlan_ip(dst["port"])
            if not target:
                failures.append(f"No IP for {dst['name']}")
                continue
            rc, _, _ = ssh_run(src["port"], f"ping -c 2 -W 3 {target}")
            if rc != 0:
                failures.append(f"{src['name']} -> {dst['name']} ({target}) FAILED")
    assert not failures, "\n".join(failures)


@pytest.mark.skipif(N_NODES < 5, reason="Need at least 5 nodes")
def test_5nodes_batman_tq_all_nonzero():
    """With 5 nodes, best routes (marked with *) must have TQ > 0."""
    failures = []
    for node in NODES:
        _, out, _ = ssh_run(node["port"], "batctl o")
        for line in out.splitlines():
            line = line.strip()
            if not line.startswith("*"):
                continue  # Only check best routes (marked with *)
            parts = line.lstrip("* ").split()
            if len(parts) < 3:
                continue
            for p in parts:
                inner = p.strip("()*")
                if inner.isdigit():
                    tq = int(inner)
                    if tq == 0:
                        failures.append(f"{node['name']}: TQ=0 for {parts[0]}")
                    break
    assert not failures, "Zero TQ entries:\n" + "\n".join(failures)


@pytest.mark.skipif(N_NODES < 5, reason="Need at least 5 nodes")
def test_5nodes_vwifi_server_all_reachable():
    """All 5 nodes can reach vwifi-server."""
    failures = []
    for node in NODES:
        rc, _, _ = ssh_run(node["port"], "ping -c 2 -W 3 10.99.0.2")
        if rc != 0:
            failures.append(node["name"])
    assert not failures, f"Cannot reach vwifi-server from: {failures}"


@pytest.mark.skipif(N_NODES < 5, reason="Need at least 5 nodes")
def test_5nodes_unique_hostnames():
    """All 5 nodes must have unique hostnames."""
    hostnames = {}
    for node in NODES:
        _, out, _ = ssh_run(node["port"], "uci get system.@system[0].hostname")
        hn = out.strip()
        if hn in hostnames:
            pytest.fail(f"Duplicate hostname '{hn}' on {node['name']} and {hostnames[hn]}")
        hostnames[hn] = node["name"]
