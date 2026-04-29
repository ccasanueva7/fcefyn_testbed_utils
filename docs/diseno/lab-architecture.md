# Lab architecture (dynamic VLAN per test) {: #lab-architecture }

**Technical design document** for the current HIL lab: one global coordinator, one exporter, shared DUT inventory, and VLAN as a per-test attribute. Context: [openwrt-tests](https://github.com/openwrt/openwrt-tests) and [LibreMesh](https://libremesh.org/) workloads on the same hardware.

---

## 1. Scope

- All DUTs are scheduled from a **single Labgrid inventory** (`dut-config.yaml` `duts` as hardware DB).
- VLAN changes apply only where a test requires them (e.g. mesh); openwrt-tests runs on isolated VLANs by default.

---

## 2. Design principle

The VLAN on a DUT port follows the **test run that holds the Labgrid lock**: the test applies the VLAN it needs at start and restores the port on teardown. Labgrid locking serializes access so two jobs do not reconfigure the same port at once.

---

## 3. Architecture

### 3.1 One coordinator, one exporter

| Component | Role |
|-----------|------|
| Coordinator | One global (datacenter VM, via WireGuard) |
| Exporter | One `labgrid-exporter` process for all DUTs |
| DUT inventory | `dut-config.yaml` `duts` (hardware database for Labgrid) |
| VLAN / scheduling | Per-test VLAN where needed; Labgrid lock serializes access |

The global coordinator is the single source of locks. libremesh-tests points `LG_COORDINATOR` at the coordinator WireGuard IP instead of `localhost:20408`. For the full connection topology (runners, WireGuard, LG_PROXY) see [Integration overview](integration-overview.md).

```mermaid
flowchart LR
    subgraph lab ["FCEFyN lab host"]
        EXP["labgrid-exporter"]
        SW["Switch TP-Link\n(VLANs 100-108, 200)"]
        DUTs["DUTs"]
    end

    COORD["labgrid-coordinator\n(datacenter VM)"]

    EXP -->|"WebSocket via WireGuard\n(register resources)"| COORD
    SW -->|"access port\n(isolated or VLAN 200)"| DUTs
```

### 3.2 Default state: isolated (fail-safe)

All switch ports start on their **isolated VLAN** (100-108):

- openwrt-tests needs no VLAN changes
- If a test fails or the runner crashes, the DUT stays isolated (no cross-talk)

### 3.3 Dynamic VLAN: the test that needs it changes it

Only libremesh-tests needs VLAN 200. Flow:

```mermaid
sequenceDiagram
    participant CI as libremesh runner
    participant COORD as Global Coordinator
    participant SW as Switch
    participant DUT as DUT port

    CI->>COORD: reserve device=belkin_rt3200
    COORD-->>CI: place allocated
    CI->>COORD: lock place
    CI->>SW: set_port_vlan port 12 vlan 200
    SW->>DUT: Port moves to VLAN 200
    Note over CI,DUT: Test runs - serial flash SSH
    CI->>SW: set_port_vlan port 12 vlan 101
    SW->>DUT: Port restored to isolated VLAN
    CI->>COORD: unlock place
```

Switching overhead: 2-5 s (SSH to switch + CLI). Negligible vs flash + boot (minutes).

### 3.4 Static infrastructure (all VLANs always on)

Configured once and left alone:

| Component | Permanent configuration |
|-----------|-------------------------|
| Switch uplinks (ports 9, 10) | Trunk of ALL VLANs (100-108 + 200) |
| Host netplan | vlan100-108 AND vlan200 up |
| dnsmasq | Instances for all VLANs (DHCP + TFTP) |
| Gateway | Interfaces for all VLANs |

## 4. Key component: `vlan_manager` API (labgrid-switch-abstraction)

Implementation lives in the **labgrid-switch-abstraction** package (`switch_abstraction.vlan_manager`). It uses `SwitchClient` + the existing driver:

```python
def set_port_vlan(dut_name, vlan_id, *, config_path=None):
    """Switch a DUT port to the target VLAN. Thread-safe via flock."""
```

The primitive already exists on the driver interface: `assign_port_vlan_commands(port, vlan_id, mode, remove_vlans)`. Expose it as a high-level function with DUT-to-port resolution from `dut-config.yaml`.

### Pytest fixture (libremesh-tests)

```python
@pytest.fixture
def mesh_vlan(request):
    """Switch DUT port to VLAN 200 before test, restore on teardown."""
    set_port_vlan(dut_name, VLAN_MESH)
    yield
    set_port_vlan(dut_name, isolated_vlan)
```

## 5. Repository split

The split between openwrt-tests and libremesh-tests **does not change**:

| Repo | Responsibility | What changes |
|------|----------------|--------------|
| **openwrt-tests** (upstream) | Vanilla OpenWrt tests, single-node | Nothing |
| **libremesh-tests** (ours) | LibreMesh single and multi-node | VLAN fixture; `LG_COORDINATOR` to global |
| **fcefyn_testbed_utils** (ours) | Lab infra, switch drivers, scripts | Static config; host: `switch-vlan` CLI |

## 6. Layers and upstream contribution

```mermaid
flowchart TB
    subgraph layer1 [Layer 1 - Switch Abstraction - contributable]
        DRV[switch_drivers/\ntplink_jetstream openwrt_ubus]
        SC[SwitchClient\nNetmiko]
        VM["vlan_manager API\n(set_port_vlan)"]
        DRV --> SC
        SC --> VM
    end

    subgraph layer2 [Layer 2 - Topology Fixture - contributable]
        TF["topology_fixture\ngeneric pytest\nVLAN per test restore teardown"]
    end

    subgraph layer3a [Layer 3a - libremesh-tests]
        MF["conftest_mesh.py\nVLAN 200 N devices"]
    end

    subgraph layer3b [Layer 3b - openwrt-tests future]
        WF["multi-device fixture\nWiFi speed test"]
    end

    VM --> TF
    TF --> MF
    TF --> WF
```

**Layer 1** supports an abstract layer for switches or network topologies.

**Layer 2** enables multi-device tests for openwrt-tests (WiFi speed, golden-device pattern).

## 7. Relation to Switch Topology Daemon (future)

The `vlan_manager` module in **labgrid-switch-abstraction** is the library base for a daemon. If an HTTP API is needed (like PDUDaemon), add an HTTP server on top of `set_port_vlan()`. Internal logic stays the same.

## 8. Trade-offs

| Aspect | Value | Mitigation |
|--------|-------|------------|
| WireGuard dependency | All testing depends on the tunnel | Stable WireGuard with keepalive; temporary local coordinator fallback |
| Coordinator API latency | Lock/unlock via WireGuard | Light messages; SSH to DUTs is local |
| dnsmasq complexity | 9+ VLANs at once | One-time config; independent instances |
| VLAN switching overhead | 2-5 s per test (libremesh only) | Negligible vs flash+boot |

## 9. What is reused

- `SwitchClient` + `tplink_jetstream.py` driver
- `assign_port_vlan_commands()` (driver interface)
- `dut-config.yaml` `duts` section (DUT to switch port map)
- PDUDaemon and `poe_switch_control.py`
- Serial, TFTP, SSH proxy infra
