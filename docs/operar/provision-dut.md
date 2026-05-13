# Full DUT provisioning (`provision_dut.py`)

One-command setup that leaves an OpenWrt DUT ready for tests **and** internet access after a clean flash. Connects via **USB serial** (no SSH/network required).

---

## 1. What it configures

| Step | What | UCI / commands | Persists reboot? |
|------|------|---------------|-----------------|
| 1 | Mesh SSH/control IP | `network.lan_mesh` = `10.13.200.x` on `br-lan` | Yes |
| 2 | Mesh route | `network.mesh_route` = `10.13.0.0/16` on-link | Yes |
| 3 | Gateway-subnet IP | `network.lan.ipaddr` += `192.168.200.x/24` | Yes |
| 4 | Default gateway | `network.lan.gateway` = `192.168.<vlan>.254` | Yes |
| 5 | DNS | `network.lan.dns` + `/etc/resolv.conf` (8.8.8.8) | Yes (UCI) |
| 6 | Firewall | `/etc/init.d/firewall disable` + stop | Yes |
| 7 | NTP | `system.ntp.enabled=1`, restart sysntpd | Yes |
| 8 | Per-device hooks | OpenWrt One: eth swap. LibreRouter: opkg feeds | Yes |

All UCI sections use **named keys** (idempotent; safe to re-run).

---

## 2. Usage

```bash
# All DUTs (close screen/minicom sessions first)
python scripts/provision_dut.py --all

# Single DUT
python scripts/provision_dut.py --device belkin-rt3200-1

# Preview without connecting
python scripts/provision_dut.py --all --dry-run

# Internet only (skip mesh IPs -- already provisioned)
python scripts/provision_dut.py --all --skip-mesh-ip

# Mesh IPs only (skip gateway/DNS/firewall/NTP)
python scripts/provision_dut.py --all --skip-internet
```

**Dependencies:** `pyserial`, `pyyaml`.

---

## 3. When to run

- After **factory reset** or clean OpenWrt flash.
- After **replacing** a DUT with a new unit.
- After **reflashing** with a different firmware version.
- Whenever `opkg update` fails and the DUT needs gateway/DNS/NTP fixed.

---

## 4. Config source

All DUT data comes from [`configs/dut-config.yaml`](../../configs/dut-config.yaml):

| Field | Used for |
|-------|----------|
| `serial_port` | USB serial device path |
| `serial_speed` | Baud rate (default 115200) |
| `switch_vlan_isolated` | Derives gateway `192.168.<vlan>.254` |
| `libremesh_fixed_ip` | Mesh SSH/control IP (`10.13.200.x`) |
| `device_type` | Selects per-device hooks |

---

## 5. Per-device hooks

Hooks run automatically based on `device_type` in `dut-config.yaml`:

| `device_type` | What it does |
|---------------|-------------|
| `openwrt_one` | Swap eth0/eth1 so PoE port becomes br-lan |
| `librerouter_v1` | Fix SNAPSHOT opkg feeds to 23.05.2, disable missing feeds |

To add hooks for a new device type: add an entry to `DEVICE_HOOKS` in `scripts/provision_dut.py`.

---

## 6. Adding a new DUT

1. Add entry to `configs/dut-config.yaml` with `serial_port`, `switch_vlan_isolated`, `libremesh_fixed_ip`, `device_type`.
2. If it needs special commands: add entry to `DEVICE_HOOKS` in `provision_dut.py`.
3. Run `python scripts/provision_dut.py --device <name>`.

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `device not found` | Serial port missing or USB not connected | Check `ls /dev/belkin-*`, udev rules |
| `no shell prompt` | DUT not booted or stuck in U-Boot | Wait for boot; press Enter on serial |
| `Permission denied` | User not in `dialout` group | `sudo usermod -aG dialout $USER` |
| Gateway unreachable after provision | DUT on wrong VLAN or gateway router down | Check `switch-vlan <dut> --restore`, ping gateway from host |
| `pyserial required` | Missing dependency | `pip install pyserial` |

---

## 8. Relation to other scripts

| Script | Purpose | Transport | When |
|--------|---------|-----------|------|
| **`provision_dut.py`** | Full one-time setup after flash | Serial | Once per flash |
| `provision_mesh_ip.py` | Mesh IPs only (subset of above) | Serial | Legacy; use `provision_dut.py` instead |
| `dut_gateway.py` | Update gateway after VLAN switch | SSH | Automatic on every `switch-vlan` |

---

## See also

- [DUT exporter setup](setup-dut-exporter.md) - next step: install Prometheus node exporter (run after this script)
- [DUT configuration status](../configuracion/duts-config.md) - per-DUT firmware and notes
- [Mesh IP provisioning](provision-mesh-ip.md) - legacy mesh-only script
- [DUT gateway management](dut-gateway.md) - dynamic gateway updates
- [Adding a DUT](dut-onboarding.md) - full onboarding checklist
