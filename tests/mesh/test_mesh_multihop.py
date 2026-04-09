"""
Multi-hop mesh tests using vwifi-ctrl to set a linear topology.

Topology (5 nodes in a line, ~200m apart):
  vm1(0,0,0) -- vm2(200,0,0) -- vm3(400,0,0) -- vm4(600,0,0) -- vm5(800,0,0)

Nodes more than ~250m apart cannot communicate directly — traffic must
route through intermediate nodes, exercising real multi-hop behaviour.

Requirements:
  - vwifi-server running on the host (launched by launch_debug_vms.sh)
  - 5 VMs running: VIRTUAL_MESH_NODES=5

Run with:
  VIRTUAL_MESH_NODES=5 pytest tests/mesh/test_mesh_multihop.py -v
"""

import subprocess
import time
import pytest
from helpers import ssh_run, NODES, N_NODES


pytestmark = pytest.mark.skipif(N_NODES < 5, reason="Multi-hop tests require 5 nodes")

# Distance between adjacent nodes in meters.
# vwifi free-space path loss at 2.4 GHz: PL ≈ 100 + 20·log10(d_km)
# With typical link budget ~85 dB:
#   50 m  → PL≈74 dB  → ~11 dB margin  → reliable
#   200 m → PL≈86 dB  → no margin      → packets dropped
# STEP_M=50 gives a 200 m gap between vm1 and vm5 — enough to block direct
# links while keeping adjacent hops reliable.
STEP_M = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vwifi_ctrl(*args) -> tuple[int, str]:
    """Run vwifi-ctrl with given args. Returns (returncode, stdout)."""
    result = subprocess.run(
        ["vwifi-ctrl"] + list(args),
        capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip()


def _get_client_ids() -> list[str]:
    """Return list of vwifi client IDs in order of connection (= VM order)."""
    rc, out = _vwifi_ctrl("ls")
    if rc != 0 or not out:
        return []
    # Each line: "CID X Y Z"
    return [line.split()[0] for line in out.strip().splitlines() if line.strip()]


def _brlan_ip(port: int) -> str | None:
    rc, out, _ = ssh_run(port, "ip -4 addr show br-lan | grep 'inet ' | awk '{print $2}' | cut -d/ -f1")
    return out.strip() if rc == 0 and out.strip() else None


def _set_linear_topology(client_ids: list[str]) -> None:
    """Place nodes in a line: node i at (i*STEP_M, 0, 0)."""
    for i, cid in enumerate(client_ids):
        x = i * STEP_M
        _vwifi_ctrl("set", cid, str(x), "0", "0")


def _reset_topology(client_ids: list[str]) -> None:
    """Put all nodes back at origin (all see each other)."""
    for cid in client_ids:
        _vwifi_ctrl("set", cid, "0", "0", "0")


# ---------------------------------------------------------------------------
# Fixture: set linear topology, restore after test
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def linear_topology():
    """Set linear topology once for all tests in this module."""
    cids = _get_client_ids()
    if len(cids) < 5:
        pytest.skip(f"Expected 5 vwifi clients, got {len(cids)}")

    # Enable packet loss so distance affects connectivity
    _vwifi_ctrl("loss", "yes")
    _set_linear_topology(cids)
    # Wait for batman-adv to reconverge with new topology (60s to be safe)
    time.sleep(60)
    yield cids
    # Restore: flat topology + disable loss
    _reset_topology(cids)
    _vwifi_ctrl("loss", "no")


# ---------------------------------------------------------------------------
# 1. Verificar que la topología se aplicó
# ---------------------------------------------------------------------------

def test_topology_set(linear_topology):
    """Verify vwifi-ctrl applied coordinates correctly."""
    cids = linear_topology
    rc, out = _vwifi_ctrl("ls")
    assert rc == 0, "vwifi-ctrl ls failed"
    for i, cid in enumerate(cids):
        expected_x = i * STEP_M
        for line in out.splitlines():
            if line.startswith(cid):
                parts = line.split()
                assert int(parts[1]) == expected_x, (
                    f"Node {i+1} (CID {cid}) X coord wrong: {parts[1]} != {expected_x}"
                )


# ---------------------------------------------------------------------------
# 2. Nodos adyacentes se ven directamente en batman
# ---------------------------------------------------------------------------

def test_adjacent_nodes_are_direct_neighbors(linear_topology):
    """Adjacent nodes must appear as direct batman neighbors."""
    failures = []
    for i in range(len(NODES) - 1):
        src = NODES[i]
        dst_id = f"{NODES[i+1]['index']:06x}"
        _, out, _ = ssh_run(src["port"], "batctl n")
        if f"lime_{dst_id}".lower() not in out.lower():
            failures.append(f"{src['name']} does not see {NODES[i+1]['name']} as direct neighbor")
    assert not failures, "\n".join(failures)


# ---------------------------------------------------------------------------
# 3. Nodos extremos NO son vecinos directos (multi-hop forzado)
# ---------------------------------------------------------------------------

def test_endpoints_are_not_direct_neighbors(linear_topology):
    """vm1 and vm5 must NOT be direct batman neighbors (too far apart)."""
    vm1, vm5 = NODES[0], NODES[4]
    vm5_id = f"{vm5['index']:06x}"
    _, out, _ = ssh_run(vm1["port"], "batctl n")
    # In neighbors table, entry means direct link
    # If vm5 appears here with low last-seen, they're direct neighbors — fail
    direct = [line for line in out.splitlines()
              if f"lime_{vm5_id}".lower() in line.lower() and "s" in line]
    assert not direct, (
        f"vm1 and vm5 are direct neighbors — topology not working:\n{out}"
    )


# ---------------------------------------------------------------------------
# 4. Ping extremo a extremo (vm1 → vm5) — multi-hop
# ---------------------------------------------------------------------------

def test_multihop_ping_vm1_to_vm5(linear_topology):
    """vm1 must reach vm5 through intermediate nodes."""
    target = _brlan_ip(NODES[4]["port"])
    if not target:
        pytest.skip("Could not get br-lan IP of vm5")
    rc, out, _ = ssh_run(NODES[0]["port"], f"ping -c 5 -W 4 {target}")
    assert rc == 0, f"Multi-hop ping vm1->vm5 ({target}) failed:\n{out}"


def test_multihop_ping_vm5_to_vm1(linear_topology):
    """vm5 must reach vm1 through intermediate nodes (reverse path)."""
    target = _brlan_ip(NODES[0]["port"])
    if not target:
        pytest.skip("Could not get br-lan IP of vm1")
    rc, out, _ = ssh_run(NODES[4]["port"], f"ping -c 5 -W 4 {target}")
    assert rc == 0, f"Multi-hop ping vm5->vm1 ({target}) failed:\n{out}"


# ---------------------------------------------------------------------------
# 5. Número de hops > 1 en la ruta extremo a extremo
# ---------------------------------------------------------------------------

def test_multihop_hop_count(linear_topology):
    """Route from vm1 to vm5 must go through at least 2 hops in batman."""
    _, out, _ = ssh_run(NODES[0]["port"], "batctl o")
    vm5_id = f"{NODES[4]['index']:06x}"

    # Find the best route entry for vm5
    for line in out.splitlines():
        if f"lime_{vm5_id}".lower() in line.lower():
            parts = line.lstrip("* ").split()
            if len(parts) >= 4:
                originator = parts[0]
                next_hop = parts[3] if len(parts) > 3 else ""
                # If next_hop != originator name, it's routing through another node
                assert originator != next_hop or "mesh" in next_hop.lower(), (
                    f"vm5 appears to be a direct 1-hop route: {line}"
                )
            return
    pytest.skip("vm5 not found in vm1 originator table")


# ---------------------------------------------------------------------------
# 6. Nodos intermedios aparecen en la ruta
# ---------------------------------------------------------------------------

def test_intermediate_nodes_in_originator_table(linear_topology):
    """vm1 must know routes through vm2, vm3, vm4 to reach vm5."""
    _, out, _ = ssh_run(NODES[0]["port"], "batctl o")
    missing = []
    for node in NODES[1:4]:  # vm2, vm3, vm4
        node_id = f"{node['index']:06x}"
        if f"lime_{node_id}".lower() not in out.lower():
            missing.append(node["name"])
    assert not missing, f"vm1 missing intermediate nodes in originator table: {missing}\n{out}"


# ---------------------------------------------------------------------------
# 7. Todos los pares ping (full connectivity a través de la mesh)
# ---------------------------------------------------------------------------

def test_multihop_all_pairs_ping(linear_topology):
    """All node pairs must be reachable even with linear topology."""
    failures = []
    for src in NODES:
        for dst in NODES:
            if src["name"] == dst["name"]:
                continue
            target = _brlan_ip(dst["port"])
            if not target:
                failures.append(f"No IP for {dst['name']}")
                continue
            rc, _, _ = ssh_run(src["port"], f"ping -c 3 -W 4 {target}")
            if rc != 0:
                failures.append(f"{src['name']} -> {dst['name']} ({target})")
    assert not failures, "Ping failures in linear topology:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# 8. TQ decrece con la distancia
# ---------------------------------------------------------------------------

def test_tq_decreases_with_distance(linear_topology):
    """TQ to vm2 (adjacent) must be higher than TQ to vm5 (4 hops away)."""
    _, out, _ = ssh_run(NODES[0]["port"], "batctl o")

    tq_vm2, tq_vm5 = None, None
    for line in out.splitlines():
        parts = line.lstrip("* ").split()
        if len(parts) < 3:
            continue
        name = parts[0].lower()
        for p in parts:
            inner = p.strip("()*")
            if inner.isdigit():
                tq = int(inner)
                vm2_id = f"lime_{NODES[1]['index']:06x}"
                vm5_id = f"lime_{NODES[4]['index']:06x}"
                if vm2_id in name and tq_vm2 is None:
                    tq_vm2 = tq
                if vm5_id in name and tq_vm5 is None:
                    tq_vm5 = tq
                break

    if tq_vm2 is None or tq_vm5 is None:
        pytest.skip(f"Could not find TQ values (vm2={tq_vm2}, vm5={tq_vm5})")

    assert tq_vm2 > tq_vm5, (
        f"Expected TQ(vm2)>{tq_vm5} > TQ(vm5)={tq_vm5}, got vm2={tq_vm2}"
    )
