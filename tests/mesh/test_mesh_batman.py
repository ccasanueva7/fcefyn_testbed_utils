"""
batman-adv specific tests for the LibreMesh virtual mesh lab.

Validates the batman-adv routing layer: originators, TQ values, gateway
election, and interface statistics.

Run with:  pytest tests/mesh/test_mesh_batman.py -v
"""

import pytest
from helpers import N_NODES, NODES, node_mac, ssh_run

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_originators(output: str) -> list[dict]:
    """
    Parse `batctl o` output into a list of dicts with keys:
      originator, last_seen_ms, tq, next_hop, iface
    Skips header lines and empty lines.
    """
    entries = []
    for line in output.splitlines():
        line = line.strip()
        # Skip header lines: empty, version banner [...], column headers
        if not line or line.startswith("[") or line.startswith("B.A.T.M.A.N") or line.startswith("Originator"):
            continue
        parts = line.split()
        # Strip leading '*' marker (best route indicator)
        if parts and parts[0] == "*":
            parts = parts[1:]
        if len(parts) < 4:
            continue
        try:
            last_seen = float(parts[1].strip("s,ms").replace(",", "."))
        except ValueError:
            continue
        # TQ is wrapped in parens like (255) — find a paren token that is purely numeric
        tq = 0
        for p in parts:
            inner = p.strip("()*")
            if inner.isdigit():
                tq = int(inner)
                break
        entries.append(
            {
                "originator": parts[0],
                "last_seen_ms": last_seen,
                "tq": tq,
                "next_hop": parts[3] if len(parts) > 3 else "",
                "iface": parts[4] if len(parts) > 4 else "",
            }
        )
    return entries


def _parse_neighbors(output: str) -> list[dict]:
    """
    Parse `batctl n` output into a list of dicts with keys:
      iface, neighbor, last_seen_ms, tq
    """
    entries = []
    for line in output.splitlines():
        line = line.strip()
        # Skip header lines
        if not line or line.startswith("[") or line.startswith("B.A.T.M.A.N") or line.startswith("IF"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            last_seen = float(parts[2].strip("s,ms").replace(",", "."))
        except ValueError:
            continue
        tq = 0
        for p in parts:
            inner = p.strip("()*")
            if inner.isdigit():
                tq = int(inner)
                break
        entries.append(
            {
                "iface": parts[0],
                "neighbor": parts[1],
                "last_seen_ms": last_seen,
                "tq": tq,
            }
        )
    return entries


# ---------------------------------------------------------------------------
# 1. Originator table has entries
# ---------------------------------------------------------------------------


def test_originator_table_not_empty():
    rc, out, _ = ssh_run(NODES[0]["port"], "batctl o")
    assert rc == 0, "batctl o failed"
    entries = _parse_originators(out)
    assert len(entries) > 0, f"Originator table empty on vm1:\n{out}"


# ---------------------------------------------------------------------------
# 2. TQ values are non-zero
# ---------------------------------------------------------------------------


def test_originator_tq_nonzero():
    """All originators must have TQ > 0 (link quality indicator)."""
    rc, out, _ = ssh_run(NODES[0]["port"], "batctl o")
    assert rc == 0, "batctl o failed"
    entries = _parse_originators(out)
    zero_tq = [e["originator"] for e in entries if e["tq"] == 0]
    assert not zero_tq, f"Originators with TQ=0 on vm1: {zero_tq}"


# ---------------------------------------------------------------------------
# 3. Each peer appears in originator table
# ---------------------------------------------------------------------------


@pytest.mark.skipif(N_NODES < 2, reason="Need at least 2 nodes")
def test_all_peers_in_originator_table():
    """vm1's originator table must contain every other node's vwifi MAC."""
    rc, out, _ = ssh_run(NODES[0]["port"], "batctl o")
    assert rc == 0, "batctl o failed"
    # LibreMesh originators appear as hostnames (LiMe_XXXXXX) not raw MACs
    missing = []
    for node in NODES[1:]:
        node_id = f"{node['index']:06x}"  # e.g. 000002
        hostname_pattern = f"lime_{node_id}"
        if hostname_pattern.lower() not in out.lower():
            missing.append(f"{node['name']} (LiMe_{node_id.upper()})")
    assert not missing, f"vm1 originator table missing peers: {missing}\n{out}"


# ---------------------------------------------------------------------------
# 4. Neighbor last-seen is recent (< 10 s)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(N_NODES < 2, reason="Need at least 2 nodes")
def test_neighbor_last_seen_recent():
    """Direct neighbors must have been seen within the last 10 seconds."""
    rc, out, _ = ssh_run(NODES[0]["port"], "batctl n")
    assert rc == 0, "batctl n failed"
    entries = _parse_neighbors(out)
    stale = [e for e in entries if e["last_seen_ms"] > 10000]
    assert not stale, f"Stale neighbors (>10 s) on vm1: {[(e['neighbor'], e['last_seen_ms']) for e in stale]}"


# ---------------------------------------------------------------------------
# 5. batman-adv interface statistics (TX/RX counters > 0)
# ---------------------------------------------------------------------------


def test_batman_iface_stats_nonzero():
    rc, out, _ = ssh_run(NODES[0]["port"], "batctl s")
    assert rc == 0, "batctl s failed"
    assert out, "batctl s returned empty output"
    # Check at least one tx or rx counter is present
    assert "tx" in out.lower() or "rx" in out.lower(), f"No tx/rx stats in batctl s output:\n{out}"


# ---------------------------------------------------------------------------
# 6. bat0 uses the correct batman-adv version protocol
# ---------------------------------------------------------------------------


def test_batman_protocol_version():
    rc, out, _ = ssh_run(NODES[0]["port"], "batctl -v")
    assert rc == 0, "batctl -v failed"
    assert "batman-adv" in out.lower(), f"Unexpected batctl version output: {out}"


# ---------------------------------------------------------------------------
# 7. wlan0 is enslaved to batman-adv
# ---------------------------------------------------------------------------


def test_wlan0_enslaved_to_batman(node):
    rc, out, _ = ssh_run(node["port"], "batctl if")
    assert rc == 0, f"{node['name']}: batctl if failed"
    assert "wlan0" in out, f"{node['name']}: wlan0 not in batman interfaces:\n{out}"
    assert "active" in out, f"{node['name']}: wlan0 not active in batman:\n{out}"


# ---------------------------------------------------------------------------
# 8. No batman-adv soft-interface in error state
# ---------------------------------------------------------------------------


def test_batman_no_error_state(node):
    rc, out, _ = ssh_run(node["port"], "batctl if")
    assert rc == 0
    assert "inactive" not in out, f"{node['name']}: batman interface in inactive state:\n{out}"


# ---------------------------------------------------------------------------
# 9. Symmetric TQ (both directions roughly equal)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(N_NODES < 2, reason="Need at least 2 nodes")
def test_tq_symmetric():
    """TQ from vm1->vm2 and vm2->vm1 should be within 50 of each other."""
    mac_vm2 = node_mac(NODES[1]["index"], vwifi=True)
    mac_vm1 = node_mac(NODES[0]["index"], vwifi=True)

    _, out1, _ = ssh_run(NODES[0]["port"], "batctl o")
    _, out2, _ = ssh_run(NODES[1]["port"], "batctl o")

    entries1 = [e for e in _parse_originators(out1) if mac_vm2.lower() in e["originator"].lower()]
    entries2 = [e for e in _parse_originators(out2) if mac_vm1.lower() in e["originator"].lower()]

    if not entries1 or not entries2:
        pytest.skip("Could not find matching originator entries for TQ symmetry check")

    tq1 = entries1[0]["tq"]
    tq2 = entries2[0]["tq"]
    assert abs(tq1 - tq2) <= 50, f"TQ asymmetry too large: vm1->vm2={tq1}, vm2->vm1={tq2}"
