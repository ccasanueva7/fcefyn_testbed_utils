# Virtual mesh tests

Pytest suite for the LibreMesh QEMU + vwifi virtual lab. Source in `tests/mesh/` (branch `test`).

---

## Setup

**vwifi-server** must be running on the host before starting the VMs. See [Virtual mesh](../diseno/virtual-mesh.md) for setup.

Install Python deps if you haven't:

```bash
pip install -r requirements.txt
```

Start the VMs:

```bash
# 2 nodes
VIRTUAL_MESH_NODES=2 bash vms/launch_debug_vms.sh

# 5 nodes (needed for multi-hop tests)
VIRTUAL_MESH_NODES=5 bash vms/launch_debug_vms.sh
```

Wait until SSH is reachable on the expected ports (2222, 2223, …) before running anything.

---

## Running

```bash
# All tests, 2 nodes
pytest tests/mesh/ -v

# Specific module
pytest tests/mesh/test_mesh_batman.py -v

# With 5 nodes
VIRTUAL_MESH_NODES=5 pytest tests/mesh/ -v

# Multi-hop only
VIRTUAL_MESH_NODES=5 pytest tests/mesh/test_mesh_multihop.py -v
```

Key env vars:

| Variable | Default | Description |
|----------|---------|-------------|
| `VIRTUAL_MESH_NODES` | `2` | Number of running VMs |
| `VIRTUAL_MESH_SSH_BASE_PORT` | `2222` | SSH port of VM 1 |
| `VIRTUAL_MESH_SSH_TIMEOUT` | `30` | Connection timeout (seconds) |

---

## What's tested

**`test_mesh_node_basic.py`** — per-node health checks. Runs against every node: interfaces up (`wlan0-mesh`, `bat0`, `br-lan`), batman-adv loaded, `wlan0` enslaved and active, `vwifi-client` connected, `lime-config` applied, hostname in `LiMe-XXXXXX` format, MTU ≥ 1460.

**`test_mesh_basic.py`** — basic mesh connectivity. All nodes have a `bat0`/`br-lan` IP, IPs are unique, every node sees every other in the batman tables, bidirectional ping between vm1 and vm2 via `bat0`.

**`test_mesh_batman.py`** — batman-adv routing layer. Originator table not empty, TQ > 0 for all entries, peers visible by `LiMe_XXXXXX` hostname, neighbors seen within 10 s, `batctl s` shows TX/RX counters, no inactive batman interfaces.

**`test_mesh_connectivity.py`** — end-to-end data plane. `br-lan` pings between all pairs, `vwifi-server` reachable at `10.99.0.2`, `uhttpd` and `dnsmasq` running, `lime-report` output has hostname, ARP table populated after ping. Includes a block of 5-node specific tests: full-mesh ping, all-pairs batman visibility, unique hostnames, TQ > 0 on best routes.

**`test_mesh_multihop.py`** — multi-hop topology (requires 5 nodes). Uses `vwifi-ctrl` to place nodes in a line with 50 m between each and packet loss enabled. At that distance vm1 and vm5 are out of direct range (~200 m apart) and must route through the intermediate nodes.

```
vm1(0,0,0) -- vm2(50,0,0) -- vm3(100,0,0) -- vm4(150,0,0) -- vm5(200,0,0)
```

Checks: coordinates applied, adjacent nodes are direct batman neighbors, endpoints are not, end-to-end ping both ways, hop count > 1, intermediate nodes in originator table, all-pairs reachable, TQ decreases with distance.

The fixture restores a flat topology and disables packet loss after each run.

---

## Firmware

Tests use the image at `firmwares/qemu/libremesh/lime-vwifi-x86-64-ext4-combined.img`, built with `vwifi-client`, `kmod-mac80211-hwsim`, and `wpad-basic-mbedtls`. See [Build firmware](build-firmware-manual.md) if you need to rebuild it.
