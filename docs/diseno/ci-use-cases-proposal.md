# CI Use Cases Proposal

Proposed CI workflows for the FCEFyN testbed, covering both OpenWrt vanilla and LibreMesh testing scenarios.

---

## 1. Overview

The testbed supports two CI contexts:

| Context | Upstream repo | Runner | Hardware |
|---------|--------------|--------|----------|
| **OpenWrt vanilla** | `openwrt/openwrt-tests` | FCEFyN self-hosted + remote labs | Physical DUTs (isolated VLANs) |
| **LibreMesh** | `libremesh/libremesh-tests` (fork) | FCEFyN self-hosted + GitHub-hosted | Physical DUTs (VLAN 200) + QEMU VMs |

Both contexts can coexist on the same physical hardware using the hybrid lab architecture described in [hybrid-lab-proposal](hybrid-lab-proposal.md).

---

## 2. Use Cases

### UC-1: OpenWrt vanilla regression (physical)

**Trigger**: push or PR to `openwrt/openwrt-tests`
**Runner**: FCEFyN self-hosted (openwrt pool)
**Mode**: isolated VLANs (100-108)
**What it tests**: standard OpenWrt tests — connectivity, services, TFTP boot

```
openwrt-tests CI
    └── FCEFyN exporter (openwrt pool)
            ├── Belkin RT3200
            ├── Banana Pi R4
            └── OpenWrt One
```

This use case requires FCEFyN DUTs to be registered in the upstream `global-coordinator`. See [openwrt-tests-onboarding](openwrt-tests-onboarding.md) for the onboarding process.

---

### UC-2: LibreMesh single-node test (physical)

**Trigger**: push or PR to `libremesh-tests`
**Runner**: FCEFyN self-hosted (libremesh pool)
**Mode**: mesh (VLAN 200)
**What it tests**: LibreMesh boots, services run, SSH reachable at `10.13.200.x`

```
libremesh-tests CI
    └── FCEFyN exporter (libremesh pool)
            └── Any DUT in VLAN 200
```

Single-node tests run in mesh mode even without a second node — VLAN 200 is required because the host uses the `10.13.0.0/16` route to reach the DUT.

---

### UC-3: LibreMesh multi-node mesh test (physical)

**Trigger**: push to main / daily schedule
**Runner**: FCEFyN self-hosted
**Mode**: mesh (VLAN 200), multiple DUTs acquired simultaneously
**What it tests**: nodes discover each other, batman-adv neighbors, babeld routes, ping across mesh

```
libremesh-tests CI
    └── FCEFyN exporter (libremesh pool)
            ├── DUT 1 @ 10.13.200.1
            ├── DUT 2 @ 10.13.200.2
            └── DUT N @ 10.13.200.N
```

Labgrid acquires all N places before the test begins. If any place is unavailable, the test is skipped.

---

### UC-4: LibreMesh virtual mesh test (QEMU)

**Trigger**: push to main/develop, schedule, manual dispatch
**Runner**: ubuntu-latest (GitHub-hosted) or FCEFyN self-hosted
**Mode**: virtual — no switch, no physical hardware
**What it tests**: same mesh tests as UC-3 but on QEMU VMs with vwifi

```
virtual-mesh.yml
    └── virtual_mesh_launcher.py
            ├── vwifi-server
            ├── QEMU VM 1 → SSH 127.0.0.1:2222
            ├── QEMU VM 2 → SSH 127.0.0.1:2223
            └── QEMU VM N → SSH 127.0.0.1:222x
```

Node count is parametrized: `matrix: [2, 3]` on ubuntu-latest, up to 5 on self-hosted.

See [virtual-mesh-proposal](virtual-mesh-proposal.md) for the full architecture.

---

### UC-5: Hybrid mode — simultaneous OpenWrt + LibreMesh

**Trigger**: manual or scheduled
**Runner**: FCEFyN self-hosted
**Mode**: hybrid — DUT pool split between openwrt and libremesh exporters
**What it tests**: both OpenWrt vanilla and LibreMesh tests run in parallel on different DUT subsets

```
pool-manager.py
    ├── openwrt pool (DUTs 1-3) → isolated VLANs → upstream coordinator
    └── libremesh pool (DUTs 4-6) → VLAN 200 → local coordinator
```

This use case requires the switch to support per-port VLAN configuration and the pool-manager to apply differential VLAN changes.

---

## 3. Workflow Matrix

| Use case | Workflow file | Trigger | Runner | Nodes |
|----------|--------------|---------|--------|-------|
| UC-1 | `openwrt-tests` upstream | PR, push | FCEFyN self-hosted | physical |
| UC-2 | `libremesh.yml` | PR, push | FCEFyN self-hosted | 1 physical |
| UC-3 | `daily.yml` | daily | FCEFyN self-hosted | N physical |
| UC-4 | `virtual-mesh.yml` | push, schedule, manual | ubuntu-latest | 2–3 virtual |
| UC-4 (extended) | `daily.yml` (smoke job) | daily | FCEFyN self-hosted | 2 virtual |
| UC-5 | `hybrid.yml` (planned) | manual | FCEFyN self-hosted | split pools |

---

## 4. Resource Constraints

| Runner | Max physical DUTs | Max virtual nodes | Notes |
|--------|-------------------|-------------------|-------|
| ubuntu-latest | 0 | 3 | 2-core, 7GB RAM |
| FCEFyN self-hosted (Lenovo T430) | 6 | 5 | depends on pool split in hybrid mode |
