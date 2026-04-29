# DUT Proxy by Mode

How the Labgrid proxy and SSH connection to each DUT changes depending on the active testbed mode.

---

## 1. What is the DUT proxy?

In Labgrid, connecting to a DUT over SSH goes through a `ProxyCommand` called `labgrid-bound-connect`. This command routes the connection through the labgrid exporter, which holds the physical connection to the DUT (serial, power, network).

In virtual mode, there is no Labgrid exporter — VMs are accessed directly over loopback port-forwards.

---

## 2. Proxy per Mode

### 2.1 OpenWrt physical (isolated VLANs)

- **Switch**: ports in isolated mode (VLAN 100-108, one per DUT)
- **DUT IP**: `192.168.1.1` (same on all DUTs, isolated by VLAN)
- **Host interface**: `vlan10x` with address `192.168.x.254`
- **Labgrid proxy**: `labgrid-bound-connect` via the exporter bound to that place
- **SSH command**:
  ```
  ssh -o ProxyCommand="labgrid-bound-connect %h %p" root@192.168.1.1
  ```

Each place in `places.yaml` has its own `NetworkService` pointing to `192.168.1.1`, isolated by VLAN.

### 2.2 LibreMesh physical (shared VLAN 200)

- **Switch**: all mesh DUT ports on VLAN 200
- **DUT IP**: `10.13.200.x` (fixed, provisioned via serial before SSH)
- **Host interface**: `vlan200` with route `10.13.0.0/16`
- **Labgrid proxy**: `labgrid-bound-connect` via the libremesh exporter
- **SSH command**:
  ```
  ssh -o ProxyCommand="labgrid-bound-connect %h %p" root@10.13.200.x
  ```

The `NetworkService` in `places.yaml` uses the deterministic `10.13.200.x` address. See [ssh-dual-mode-flow](ssh-dual-mode-flow.md) for how this address is provisioned.

### 2.3 LibreMesh virtual (QEMU)

- **No switch involved**
- **DUT IP**: `127.0.0.1` (loopback port-forward)
- **Port**: `2221 + node_index` (VM 1 → 2222, VM 2 → 2223, …)
- **No Labgrid proxy** — direct SSH connection
- **SSH command**:
  ```
  ssh -o StrictHostKeyChecking=no \
      -o UserKnownHostsFile=/dev/null \
      -p 2222 root@127.0.0.1
  ```

The `virtual_mesh_launcher.py` returns a list of `{host, port}` pairs consumed directly by the fixture.

---

## 3. Summary Table

| Mode | Switch config | DUT address | Labgrid proxy | Port |
|------|--------------|-------------|---------------|------|
| OpenWrt physical | Isolated (VLAN 100-108) | `192.168.1.1` | `labgrid-bound-connect` | 22 |
| LibreMesh physical | Mesh (VLAN 200) | `10.13.200.x` | `labgrid-bound-connect` | 22 |
| LibreMesh virtual | N/A | `127.0.0.1` | None (direct) | 2222+ |

---

## 4. Switching Between Modes

The testbed mode is changed with `testbed-mode`:

```bash
testbed-mode openwrt     # switch → isolated VLANs, start openwrt exporter
testbed-mode libremesh   # switch → VLAN 200, start libremesh exporter
```

In hybrid mode, two exporters run simultaneously — one per pool — each serving a different coordinator. The pool-manager handles VLAN assignment and exporter config generation per pool. See [hybrid-lab-proposal](../diseno/hybrid-lab-proposal.md) for details.

---

## 5. places.yaml NetworkService

The `NetworkService` entry in `places.yaml` defines the address used by `labgrid-bound-connect`:

```yaml
# OpenWrt place
- name: dut-belkin-rt3200
  resources:
    - cls: NetworkService
      params:
        address: 192.168.1.1
        port: 22

# LibreMesh place
- name: lime-belkin-rt3200
  resources:
    - cls: NetworkService
      params:
        address: 10.13.200.1
        port: 22
```

In virtual mode, `places.yaml` is not used — the launcher generates the connection info at runtime.
