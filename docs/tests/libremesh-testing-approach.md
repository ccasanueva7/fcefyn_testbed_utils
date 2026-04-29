# LibreMesh Testing Approach

Overview of the testing strategy for LibreMesh on the FCEFyN HIL testbed, covering both physical DUTs and virtual QEMU nodes.

---

## 1. Goals

The LibreMesh test suite aims to validate:

- **Mesh formation**: nodes discover each other and establish L2/L3 connectivity via batman-adv and babeld
- **LibreMesh configuration**: packages are installed, services are running, and the node is reachable
- **Regression detection**: changes to LibreMesh packages or OpenWrt base do not break mesh behavior
- **Multi-node scenarios**: at least 2 nodes form a functional mesh and can ping each other across the mesh interface

---

## 2. Test Environments

LibreMesh tests run in two environments that share the same test suite (`test_mesh.py`):

| Environment | DUTs | Network | Orchestration | When used |
|-------------|------|---------|---------------|-----------|
| **Physical** | Real routers (Belkin RT3200, BananaPi R4, etc.) | VLAN 200 shared mesh | Labgrid + coordinator | Self-hosted CI, hardware validation |
| **Virtual** | QEMU x86_64 VMs | vwifi + mac80211_hwsim | Custom launcher (no Labgrid) | GitHub-hosted CI, local dev |

Both environments use the same fixture interface — the test code does not know whether it is talking to a real router or a VM.

---

## 3. Key Differences from OpenWrt Vanilla Testing

LibreMesh testing requires a different approach from standard OpenWrt tests in several ways:

### 3.1 IP addressing

OpenWrt vanilla uses a fixed `192.168.1.1` on `br-lan`, which requires strict VLAN isolation between DUTs. LibreMesh assigns a unique MAC-derived IP (`10.13.<MAC[4]>.<MAC[5]>`) to each node, so multiple DUTs can share the same L2 segment (VLAN 200) without conflicts.

### 3.2 SSH connectivity

Because the LibreMesh IP is dynamic and may vary between firmware versions, the framework provisions a deterministic fixed IP on each DUT before running tests:

1. Connect via serial console
2. Assign `10.13.200.x` (derived from `MD5(place_name) % 253 + 1`) as a secondary address on `br-lan`
3. Use this fixed IP for all subsequent SSH connections

This is handled by `scripts/provision_mesh_ip.py`.

### 3.3 Switch mode

All LibreMesh DUTs (both single-node and multi-node tests) run with the switch in **mesh mode (VLAN 200)**. This is in contrast to OpenWrt tests, which use isolated VLANs (100-108). See [hybrid-lab-proposal](../diseno/hybrid-lab-proposal.md) for the full rationale.

### 3.4 Required packages

A minimal LibreMesh image for testing must include:

| Package | Reason |
|---------|--------|
| `lime-proto-batadv` | batman-adv mesh protocol |
| `lime-proto-babeld` | babeld routing |
| `lime-proto-anygw` | anycast gateway |
| `shared-state` | distributed state between nodes |
| `wpad-basic-mbedtls` | required for mesh interfaces on mac80211_hwsim (virtual) |

See [build-firmware-manual](build-firmware-manual.md) for the full build configuration.

---

## 4. Physical Test Flow

```
1. testbed-mode libremesh          # switch → VLAN 200, start local coordinator
2. labgrid acquires place(s)       # exclusive lock on DUT(s)
3. Flash LibreMesh image via TFTP  # U-Boot tftp + boot
4. provision_mesh_ip.py            # assign 10.13.200.x via serial
5. pytest test_mesh.py             # run tests over SSH
6. labgrid releases place(s)
```

The `mesh_nodes` fixture in `conftest_mesh.py` handles steps 2–4 automatically for each DUT in the test.

---

## 5. Virtual Test Flow

```
1. virtual_mesh_launcher.py        # start vwifi-server + N QEMU VMs
2. Wait for SSH on 127.0.0.1:222x  # one port per VM
3. pytest test_mesh.py             # LG_VIRTUAL_MESH=1
4. VMs shut down after session
```

No Labgrid coordinator is involved. See [virtual-mesh-proposal](../diseno/virtual-mesh-proposal.md) for the full architecture.

---

## 6. What the Tests Validate

### 6.1 Single-node tests

- LibreMesh services are running (`lime-config`, `lime-proto-babeld`, etc.)
- `br-lan` has the expected IP scheme (`10.13.x.x`)
- `batman-adv` interface is up
- SSH is reachable after boot

### 6.2 Multi-node tests

- Nodes discover each other via batman-adv
- `batctl n` shows neighbors
- Ping between `10.13.x.x` addresses succeeds
- babeld routes are exchanged (where applicable)

---

## 7. CI Workflows

| Workflow | Trigger | Environment | Nodes |
|----------|---------|-------------|-------|
| `virtual-mesh.yml` | push, schedule, manual | ubuntu-latest | 2, 3 (matrix) |
| `daily.yml` (smoke job) | daily schedule | self-hosted | 2 |
| Physical tests | manual / self-hosted | FCEFyN lab | all DUTs |

Physical tests require the self-hosted runner and the lab to be in libremesh mode. Virtual tests run on any ubuntu-latest runner without hardware.
