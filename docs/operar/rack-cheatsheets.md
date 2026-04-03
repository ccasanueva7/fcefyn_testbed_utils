# Rack cheatsheets

Quick reference at the rack.

---

## Quick reference - all DUTs

**Gateway:** Isolated: `192.168.XXX.254` (per-VLAN). Mesh: `192.168.200.254`. Per-DUT VLAN change: `switch-vlan <dut> <vlan>` (or `--restore`). See [duts-config Internet access](../configuracion/duts-config.md#internet-access-opkg).

| DUT | Port | VLAN | Power | Ch | Serial | SSH (isolated) | Mesh IP (VLAN 200) |
|-----|------|------|-------|----|--------|----------------|--------------------|
| Belkin #1 | 11 | 100 | Relay | 0 | belkin-rt3200-1 | `ssh dut-belkin-1` | 10.13.200.11 |
| Belkin #2 | 12 | 101 | Relay | 1 | belkin-rt3200-2 | `ssh dut-belkin-2` | 10.13.200.196 |
| Belkin #3 | 13 | 102 | Relay | 2 | belkin-rt3200-3 | `ssh dut-belkin-3` | 10.13.200.118 |
| Banana Pi R4 | 14 | 103 | Relay | 3 | bpi-r4 | `ssh dut-bananapi` | 10.13.200.169 |
| OpenWRT One | 1 | 104 | PoE | - | openwrt-one | `ssh dut-openwrt-one` | 10.13.200.120 |
| Librerouter 1 | 2 | 105 | PoE splitter | - | librerouter-1 | `ssh dut-librerouter-1` | 10.13.200.77 |
| Librerouter 2 | 3 | 106 | Relay | - | - | `ssh dut-librerouter-2` | - |
| Librerouter 3 | 4 | 107 | Relay | - | - | `ssh dut-librerouter-3` | - |

**SSH (isolated)** connects via `labgrid-bound-connect` on the DUT's isolated VLAN (default state). **Mesh VLAN 200** access (e.g. test crash left DUT there): `sudo labgrid-bound-connect vlan200 <mesh_ip> 22`. Details: [SSH access to DUTs](dut-ssh-access.md). First time in the lab: `provision_mesh_ip.py --all`.

---

## OpenWrt profiles

| DUT | Subtarget | Profile |
|-----|-----------|---------|
| Belkin RT3200 | mt7622 | linksys_e8450-ubi |
| Banana Pi R4 | filogic | bananapi_bpi-r4 |
| OpenWrt One | filogic | openwrt_one |
| LibreRouter 1 | generic | librerouter_librerouter-v1 |
| Gateway TL-WDR3500 | generic | tplink_tl-wdr3500-v1 |

LibreMesh feeds, `menuconfig`, lime packages, QEMU/vwifi: [build-firmware-manual](build-firmware-manual.md).

---

## SSH: Oracle VPS and OpenWrt gateway

From the **orchestration host** (same machine as Labgrid). Requires `~/.ssh/config` per repo templates.

| System | Command | Notes |
|--------|---------|-------|
| **Oracle VPS** (Nginx / Grafana tunnel) | `ssh oracle-vps` | Host `oracle-vps`: public IP, typical user `ubuntu`, dedicated key. Provisioning: [public Grafana](../configuracion/grafana-public-access.md). |
| **Gateway** (OpenWrt on trunk, e.g. WDR3500) | `ssh gateway-openwrt` | `Host gateway-openwrt` with `HostName 192.168.100.254`, `User root`. In mesh, `192.168.200.254` also works. Detail: [gateway §5.5](../configuracion/gateway.md#55-ssh-access-to-gateway-from-host). |

---

## TP-Link SG2016P switch

| Field | Value |
|-------|-------|
| **IP** | 192.168.0.1 |
| **SSH** | `ssh switch-fcefyn` |
| **User** | admin |
| **Note** | Does not accept public keys; use password in SSH config |
| **Manual PoE** | `poe_switch_control.py off 1` / `on 1` (port 1 = OpenWRT One, 2 = Librerouter 1) |
