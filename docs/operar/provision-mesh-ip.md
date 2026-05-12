# Mesh IP provisioning (`provision_mesh_ip.py`)

!!! tip "Prefer `provision_dut.py` for new setups"
    [`provision_dut.py`](provision-dut.md) does everything this script does **plus** gateway, DNS, firewall, NTP, and per-device hooks in a single command.

One-time setup script that configures each physical DUT with the addresses
needed for SSH access and test control in mesh mode (VLAN 200). Run once
after a DUT is factory-reset or reflashed with a clean OpenWrt image.

---

## 1. What it configures

The script connects to the DUT over **USB serial** (no network access needed)
and applies the following via UCI:

| UCI section | Interface | Address | Purpose |
|-------------|-----------|---------|---------|
| `network.lan_mesh` | `br-lan` | `10.13.200.x/24` | Mesh SSH/control IP — permanent alias |
| `network.mesh_route` | `lan` | route `10.13.0.0/16 via 0.0.0.0` | On-link route so the host can reach any `10.13.x.x` address |
| `network.lan` (ipaddr list) | `br-lan` | `192.168.200.x/24` | Secondary IP in the gateway subnet (MikroTik reachability in mesh) |

All UCI sections use named keys, so the script is **idempotent** — re-running
it on an already-provisioned DUT is safe.

!!! note "Gateway is managed separately"
    This script does **not** touch the default gateway. Gateway and DNS are
    updated by `dut_gateway.py` each time the VLAN is switched between
    isolated (OpenWrt tests) and mesh (LibreMesh tests).

---

## 2. IP address map

Fixed IPs come from `configs/dut-config.yaml` (`libremesh_fixed_ip` field).
Built-in fallback map:

| Serial device | Mesh IP (`10.13.200.x`) |
|---------------|------------------------|
| `/dev/belkin-rt3200-1` | `10.13.200.11` |
| `/dev/belkin-rt3200-2` | `10.13.200.196` |
| `/dev/belkin-rt3200-3` | `10.13.200.118` |
| `/dev/bpi-r4` | `10.13.200.169` |
| `/dev/openwrt-one` | `10.13.200.120` |
| `/dev/librerouter-1` | `10.13.200.77` |

---

## 3. Usage

```bash
# Single DUT (by serial device path or short name)
python scripts/provision_mesh_ip.py --device /dev/belkin-rt3200-1
python scripts/provision_mesh_ip.py --device belkin-rt3200-1

# All DUTs listed in dut-config.yaml
python scripts/provision_mesh_ip.py --all

# Dry-run: print UCI commands without connecting to the DUT
python scripts/provision_mesh_ip.py --device /dev/belkin-rt3200-1 --dry-run
```

**Dependencies:** `pyserial`, `pyyaml` (install via `pip install -r requirements.txt`).

---

## 4. When to run

- After **factory reset** or clean OpenWrt flash (mesh IPs are not in the
  upstream firmware).
- After **replacing a DUT** with a new unit of the same type.
- After provisioning via `playbook_labgrid.yml` if TFTP-boot tests are run
  without a prior mesh provisioning step.

!!! tip "Shortcut: provision all at once"
    `--all` reads `configs/dut-config.yaml` and provisions every DUT that has
    both a `serial_port` and a `libremesh_fixed_ip`. Run from the orchestration
    host while all DUTs are powered and at the OpenWrt shell prompt.

---

## 5. How it works

```
Host serial port (/dev/belkin-rt3200-1, 115200 baud)
  └─► send UCI commands one by one
      ├─ uci set network.lan_mesh=interface
      ├─ uci set network.lan_mesh.ipaddr='10.13.200.11'
      ├─ uci set network.mesh_route=route ...
      ├─ uci add_list network.lan.ipaddr='192.168.200.11/24'
      └─ uci commit network
```

Each command is sent and the script waits for the shell prompt before
proceeding. After the final `uci commit`, the script optionally calls
`/etc/init.d/network restart` to apply immediately.

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Permission denied: /dev/belkin-rt3200-1` | User not in `dialout` group | `sudo usermod -aG dialout $USER` (log out and back in) |
| `No such file or directory: /dev/belkin-rt3200-1` | udev rule not applied or USB not connected | Check `lsusb`, re-apply `ansible --tags arduino` |
| Script hangs after connecting | DUT not at shell prompt (in U-Boot or booting) | Wait for boot to finish, press Enter to get prompt |
| `ERROR: pyserial required` | Missing dependency | `pip install pyserial` |

---

## See also

- [Full DUT provisioning](provision-dut.md) — mesh IPs + gateway + DNS + firewall + NTP in one command (recommended over this script)
- [DUT gateway management](dut-gateway.md) — updating the default gateway after VLAN switches
- [Adding a DUT](dut-onboarding.md) — full onboarding procedure for new hardware
- `configs/dut-config.yaml` — per-DUT serial port and mesh IP
