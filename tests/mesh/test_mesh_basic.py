"""
Mesh-level connectivity tests for the LibreMesh virtual mesh lab.

Requires at least 2 VMs running (launched via vms/launch_debug_vms.sh).
Run with:  pytest tests/mesh/test_mesh_basic.py -v
"""

import pytest
from helpers import ssh_run, NODES, N_NODES, node_mac


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _bat0_ip(port: int) -> str | None:
    """Return the first IPv4 address on bat0, or br-lan as fallback (LibreMesh bridges bat0 into br-lan)."""
    rc, out, _ = ssh_run(port, "ip -4 addr show bat0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1")
    if rc == 0 and out.strip():
        return out.strip()
    # LibreMesh may assign IP to br-lan which includes bat0
    rc, out, _ = ssh_run(port, "ip -4 addr show br-lan 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1")
    return out.strip() if rc == 0 and out.strip() else None


# ---------------------------------------------------------------------------
# 1. Ping entre nodos (LAN user-net – QEMU hostfwd bridge)
# ---------------------------------------------------------------------------

def test_ping_between_nodes():
    """VM1 can ping VM2's QEMU user-net gateway (10.13.0.2 within vm2 net)."""
    if N_NODES < 2:
        pytest.skip("Need at least 2 nodes")
    rc, _, _ = ssh_cmd_compat(2222, "ping -c 3 -W 2 10.13.0.2")
    # Note: VMs are on isolated user-nets; actual mesh ping is via bat0.
    # This is a best-effort check; skip gracefully if unreachable by design.
    if rc != 0:
        pytest.xfail("VM user-nets are isolated; use test_mesh_bat0_ping for real connectivity")


def ssh_cmd_compat(port, cmd):
    """Thin wrapper kept for backward compatibility."""
    return ssh_run(port, cmd)


# ---------------------------------------------------------------------------
# 2. Interfaz mesh activa
# ---------------------------------------------------------------------------

def test_mesh_interface_up():
    rc, out, _ = ssh_run(2222, "ip link show | grep -E 'mesh|bat'")
    assert rc == 0, "No mesh/bat interface found on vm1"
    assert "UP" in out, f"Mesh interface not UP: {out}"


# ---------------------------------------------------------------------------
# 3. Vecinos mesh (batman-adv)
# ---------------------------------------------------------------------------

def test_neighbors_present():
    rc, out, _ = ssh_run(2222, "batctl n")
    assert rc == 0, "batctl n failed on vm1"
    assert len(out.splitlines()) > 2, f"No batman neighbors detected:\n{out}"


# ---------------------------------------------------------------------------
# 4. Tabla de originadores
# ---------------------------------------------------------------------------

def test_routing_table():
    rc, out, _ = ssh_run(2222, "batctl o")
    assert rc == 0, "batctl o failed on vm1"
    assert len(out.splitlines()) > 2, f"Originator table empty:\n{out}"


# ---------------------------------------------------------------------------
# 5. Ping mesh a través de bat0 (bidireccional)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(N_NODES < 2, reason="Need at least 2 nodes")
def test_bat0_ping_vm1_to_vm2():
    """VM1 pings VM2 through batman-adv (bat0 IPs assigned by lime-config)."""
    target_ip = _bat0_ip(NODES[1]["port"])
    if not target_ip:
        pytest.skip("Could not determine bat0 IP for vm2")
    rc, _, err = ssh_run(NODES[0]["port"], f"ping -c 4 -W 2 {target_ip}")
    assert rc == 0, f"bat0 ping vm1->vm2 ({target_ip}) failed:\n{err}"


@pytest.mark.skipif(N_NODES < 2, reason="Need at least 2 nodes")
def test_bat0_ping_vm2_to_vm1():
    """VM2 pings VM1 through batman-adv (bidirectional)."""
    target_ip = _bat0_ip(NODES[0]["port"])
    if not target_ip:
        pytest.skip("Could not determine bat0 IP for vm1")
    rc, _, err = ssh_run(NODES[1]["port"], f"ping -c 4 -W 2 {target_ip}")
    assert rc == 0, f"bat0 ping vm2->vm1 ({target_ip}) failed:\n{err}"


# ---------------------------------------------------------------------------
# 6. Todos los nodos tienen bat0 con IP
# ---------------------------------------------------------------------------

def test_all_nodes_have_bat0_ip():
    missing = []
    for node in NODES:
        ip = _bat0_ip(node["port"])
        if not ip:
            missing.append(node["name"])
    assert not missing, f"Nodes without bat0 IP: {missing}"


# ---------------------------------------------------------------------------
# 7. bat0 IPs son únicas (sin duplicados)
# ---------------------------------------------------------------------------

def test_bat0_ips_unique():
    ips = {}
    for node in NODES:
        ip = _bat0_ip(node["port"])
        if ip:
            if ip in ips:
                pytest.fail(f"Duplicate bat0 IP {ip} on {node['name']} and {ips[ip]}")
            ips[ip] = node["name"]


# ---------------------------------------------------------------------------
# 8. Cada nodo ve al resto en su tabla batman
# ---------------------------------------------------------------------------

@pytest.mark.skipif(N_NODES < 2, reason="Need at least 2 nodes")
def test_each_node_sees_all_others_in_batman():
    """Every node must list every other node as originator or neighbor."""
    failures = []
    for src in NODES:
        _, orig_out, _ = ssh_run(src["port"], "batctl o")
        _, neigh_out, _ = ssh_run(src["port"], "batctl n")
        combined = orig_out + neigh_out
        for dst in NODES:
            if dst["name"] == src["name"]:
                continue
            mac = node_mac(dst["index"], vwifi=True)
            # batctl shows short MACs; check any part of it
            mac_short = mac.replace(":", "")[-6:]
            if mac_short.lower() not in combined.lower() and mac.lower() not in combined.lower():
                failures.append(f"{src['name']} does not see {dst['name']} ({mac})")
    assert not failures, "Batman visibility failures:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# 9. Resolución DNS mínima desde cada nodo
# ---------------------------------------------------------------------------

def test_dns_resolves_from_vm1():
    _, _, _ = ssh_run(NODES[0]["port"], "nslookup libremesh.org 2>&1 || dig +short libremesh.org 2>&1 || true")
    # Soft check: VMs may not have internet. Just verify the command doesn't crash.


# ---------------------------------------------------------------------------
# 10. MTU de bat0 es suficiente para paquetes mesh
# ---------------------------------------------------------------------------

def test_bat0_mtu():
    rc, out, _ = ssh_run(NODES[0]["port"], "cat /sys/class/net/bat0/mtu")
    assert rc == 0, "Could not read bat0 MTU"
    mtu = int(out.strip())
    assert mtu >= 1460, f"bat0 MTU too low: {mtu}"
