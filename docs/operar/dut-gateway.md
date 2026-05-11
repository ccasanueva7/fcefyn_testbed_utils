# DUT gateway management (`dut_gateway.py`)

`scripts/switch/dut_gateway.py` updates the default gateway and DNS on all
physical DUTs over parallel SSH immediately after a VLAN switch. It is called
automatically by the `labgrid-switch-abstraction` library when `switch-vlan`
changes the network mode — operators normally do not invoke it directly.

---

## 1. Why a separate gateway step?

When a DUT moves between VLANs its upstream router changes:

| Mode | VLAN | Gateway | DNS |
|------|------|---------|-----|
| **Isolated** (OpenWrt tests) | 100–105 per DUT | `192.168.<vlan>.254` (per-VLAN gateway) | same |
| **Mesh** (LibreMesh tests) | 200 | `192.168.200.254` (`MESH_GATEWAY`) | `192.168.200.254` |

A simple VLAN change on the switch port is not enough: OpenWrt keeps the old
default route in memory. `dut_gateway.py` pushes a shell script to each DUT
that:

1. Persists the new gateway and DNS in UCI (`uci set network.lan.gateway`, `uci commit`)
2. Applies the route instantly with `ip route replace default via <gw>` (no reboot needed)
3. Ensures a source IP in the gateway subnet exists on `br-lan` so the gateway
   can route replies back to the DUT

---

## 2. How it is called

The function `update_dut_gateways(mode, ...)` is called by
`switch_abstraction` after every VLAN transition:

```python
from switch.dut_gateway import update_dut_gateways

update_dut_gateways(
    mode="mesh",           # "mesh" or "isolated"
    config_path=Path("configs/dut-config.yaml"),
    settle_seconds=5,      # wait for VLAN propagation before SSH
)
```

The `settle_seconds` delay (default 5 s) absorbs the time for the managed
switch to apply the VLAN change before SSH connections are attempted.

---

## 3. Shell script pushed to each DUT

For **mesh mode** (`MESH_GATEWAY = 192.168.200.254`):

```sh
uci delete network.lan.gateway 2>/dev/null; true
uci set network.lan.gateway='192.168.200.254'
uci set network.lan.dns='192.168.200.254'
uci commit network
ip route replace default via 192.168.200.254 dev br-lan src 10.13.200.11
```

For **isolated mode** (e.g. DUT on VLAN 100):

```sh
uci delete network.lan.gateway 2>/dev/null; true
uci set network.lan.gateway='192.168.100.254'
uci set network.lan.dns='192.168.100.254'
uci commit network
ip route replace default via 192.168.100.254 dev br-lan src 10.13.200.11
```

---

## 4. Parallel SSH execution

All DUTs are updated in parallel using `subprocess` with a 10-second
SSH timeout. SSH options used:

```
-o StrictHostKeyChecking=no
-o UserKnownHostsFile=/dev/null
-o ConnectTimeout=10
-o LogLevel=ERROR
```

Each DUT is identified by its `ssh_alias` field from `dut-config.yaml`
(e.g. `dut-belkin-1`). See [SSH access to DUTs](dut-ssh-access.md) for
how aliases are configured.

---

## 5. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| SSH timeout on one DUT | DUT still in isolated VLAN, SSH not reachable yet | Increase `settle_seconds` or check switch VLAN assignment |
| `Connection refused` | DUT powered off or sshd not running | Power on DUT, check serial console |
| Gateway not applied after SSH succeeds | Script ran but UCI/route failed | SSH into DUT manually, check `logread`, re-run `switch-vlan` |
| All DUTs fail immediately | `dut-config.yaml` not found or `ssh_alias` missing | Verify `configs/dut-config.yaml` and DUT entries |

---

## See also

- [Mesh IP provisioning](provision-mesh-ip.md) — one-time setup of mesh IPs via serial
- [Unified pool architecture](../diseno/unified-pool.md) — dynamic VLAN model
- `scripts/switch/dut_gateway.py` — source
- `configs/dut-config.yaml` — DUT ssh_alias and VLAN mapping
