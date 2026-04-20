# DUT configuration status

Record of state, applied configuration, and firmware per DUT. Update when flashing, changing network, or applying fixes.

---

## Summary table

| DUT              | Port | VLAN | Power        | Firmware        | SSH | Internet | Notes |
|------------------|------|------|--------------|-----------------|-----|----------|-------|
| Belkin RT3200 #1 | 11 | 100 | Relay        | OpenWrt 23.05.5 | ✓ | ✓ | |
| Belkin RT3200 #2 | 12 | 101 | Relay        | LibreMesh 2024.1 | ✓ | ✓ | |
| Belkin RT3200 #3 | 13 | 102 | Relay        | OpenWrt 23.05.5 | ✓ | ✓ | |
| Banana Pi R4     | 14 | 103 | Relay        | OpenWrt 24.10.5 | ✓ | ✓ | |
| OpenWRT One      | 1  | 104 | PoE (native) | OpenWrt 24.10.5 | ✓ | ✓ | swap eth0/eth1, port 1 |
| Librerouter 1    | 2  | 105 | Relay (ch 4)   | LibreRouterOs 23.05 + LibreMesh | ✓ | ✓ | 12V DC jack, opkg feeds 23.05.2 |
| Librerouter 2    | 3  | 106 | Relay        | - | Pending | Pending | Reserved |
| Librerouter 3    | 4  | 107 | Relay        | - | Pending | Pending | Reserved |

**Serial and SSH:** [rack-cheatsheets](../operar/rack-cheatsheets.md).

---

## Internet access (opkg)

By default each DUT is on its **isolated VLAN** (100-108) with gateway `192.168.XXX.254` (per-VLAN). When libremesh-tests moves a port to VLAN 200 (mesh), the gateway becomes `192.168.200.254`. VLAN changes are per test via `labgrid-switch-abstraction` (CI) or `switch-vlan` (manual); there are no global modes. See [Lab architecture](../diseno/lab-architecture.md).

DUT network config (gateway, DNS, secondary IP, firewall) is handled by test fixtures or `dut_gateway.py`:

- Gateway and DNS persist in UCI (`uci set` + `uci commit`)
- Secondary IP on the gateway subnet (e.g. `192.168.{vlan}.x/24` isolated, `192.168.200.x/24` mesh) so the upstream router can route replies
- Firewall stopped (`fw3`/`fw4`) since test DUTs do not need it

**Initial provisioning (once per DUT, via serial):** `provision_mesh_ip.py` adds the per-DUT mesh SSH/control IP (`10.13.200.x`) plus the `192.168.200.x` secondary address used for mesh-VLAN gateway reachability. It does not change the gateway. The real LibreMesh `br-lan` address used by mesh assertions remains the node's dynamic `10.13.x.x` address.

```bash
python3 scripts/provision_mesh_ip.py --all --dry-run   # verify IPs
python3 scripts/provision_mesh_ip.py --all              # apply IPs
```

Hardware data per DUT (switch port, isolated VLAN, serial, ssh_alias): `configs/dut-config.yaml`, `duts` section.

Relation to **manual SSH** to the DUT: [SSH access to DUTs](../operar/dut-ssh-access.md).

### opkg fails with "wget returned 5"

Many DUTs have no RTC and boot with wrong date. SSL fails. Fix before `opkg update`:

```bash
date -s "2026-02-22 16:00:00"   # current date/time
opkg update
```

To persist, enable NTP (sysntpd):

```bash
uci set system.ntp.enabled='1'
uci commit system
/etc/init.d/sysntpd restart
date   # verify
```

### opkg fails with "Failed to send request: Operation not permitted"

Typical cause: **firewall blocking outbound**. Test fixtures stop the firewall automatically, but after a DUT reboot it may return. Quick fix:

```bash
/etc/init.d/firewall stop     # fw4 (OpenWrt 24.x) or fw3 (23.x)
iptables -P OUTPUT ACCEPT 2>/dev/null   # fw3 only
opkg update
```

If `ping 8.8.8.8` fails (no route), check gateway and DUT VLAN with `dut_gateway.py`. If `ping 8.8.8.8` works but `ping downloads.openwrt.org` says "bad address", DNS is missing:

```bash
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf
opkg update
```

### LibreRouter: SNAPSHOT feeds missing

If `opkg update` fails with `23.05-SNAPSHOT` URLs: move to 23.05.2 and comment non-existent feeds. See [Librerouter 1](#librerouter-1).

---

## Belkin RT3200 / Linksys E8450 - General notes

All three Belkin RT3200 units (Linksys E8450 equivalent) share target `mediatek/mt7622` and `aarch64_cortex-a53`.

**U-Boot:** Interrupt char `\x03` (Ctrl-C). Must be a single byte for Labgrid's proactive interrupt mode. Previous value `"0\n"` (two chars) disabled proactive mode and caused U-Boot activation timeouts.

### SPI-NAND layout change in OpenWrt 24.10+

From **OpenWrt 24.10**, SPI-NAND flash layout for E8450/RT3200 changed from **image version 1.0 to 2.0**. That implies:

- **No direct `sysupgrade`** from 23.05.x (layout 1.0) to 24.10+ (layout 2.0). The image is rejected with: *image is incompatible for sysupgrade based on the image version (1.0->2.0)*.
- **Bootloader update required:** run **UBI installer 1.1.0+** (unsigned) before flashing 24.10+. See [OpenWrt wiki: Linksys E8450](https://openwrt.org/toh/linksys/e8450).

For now devices stay on **OpenWrt 23.05.x** until 24.10+ is needed. If upgrading, plan bootloader update (via U-Boot or recovery).

---

## Belkin RT3200 #1

**Serial:** `/dev/belkin-rt3200-1`. Port/VLAN mapping: [summary table](#summary-table).

**Firmware (detail):** mediatek/mt7622, `aarch64_cortex-a53`.

**Network:** [Internet access](#internet-access-opkg) template.

---

## Belkin RT3200 #2

**Serial:** `/dev/belkin-rt3200-2`. Mapping: [summary table](#summary-table).

**Firmware (detail):** LibreMesh 2024.1 on OpenWrt 23.05.5, mediatek/mt7622.

**Network:** [Internet access](#internet-access-opkg) template.

---

## Belkin RT3200 #3

**Serial:** `/dev/belkin-rt3200-3`. Mapping: [summary table](#summary-table).

**Firmware (detail):** mediatek/mt7622 (same OpenWrt line as table).

**Network:** [Internet access](#internet-access-opkg) template.

If config does not persist after reboot: see [Corrupt overlay](#corrupt-overlay-rootfs_data-belkin-rt3200-linksys-e8450).

### Corrupt overlay (rootfs_data) - Belkin RT3200 / Linksys E8450

**Symptoms:** Network/UCI config does not persist after `reboot`. Each boot: default config, opkg "Operation not permitted", SSH host key changes. `firstboot -y` does not fix (UBIFS corruption remains).

**Diagnosis:**

```bash
mount | grep overlay
```

If you see `ubifs (ro,...)` and `upperdir=/tmp/root/upper` → overlay is corrupt; system uses ramoverlay (tmpfs) and nothing persists.

```bash
dmesg | grep -i -E "ubi|ubifs|overlay|read-only|error"
```

Typical errors: `bad node type`, `switched to read-only mode`, `fallback to ramoverlay`.

**Fix - Re-flash with sysupgrade:**

Belkin uses UBI layout; mtd "rootfs_data" is not a separate mtd (UBI volume 5). Reliable repair is re-flash:

1. **Configure network manually** (so DUT can download):

   ```bash
   ip route del default 2>/dev/null; true
   ip addr add 192.168.102.108/24 dev br-lan 2>/dev/null; true
   ip route add default via 192.168.102.254
   echo "nameserver 8.8.8.8" > /etc/resolv.conf
   date -s "2026-03-12 12:00:00"   # current date
   ```

2. **Download and flash on DUT** (use `.itb`, not `.bin`):

   ```bash
   cd /tmp
   wget https://downloads.openwrt.org/releases/23.05.5/targets/mediatek/mt7622/openwrt-23.05.5-mediatek-mt7622-linksys_e8450-ubi-squashfs-sysupgrade.itb
   sysupgrade -F -v /tmp/openwrt-23.05.5-mediatek-mt7622-linksys_e8450-ubi-squashfs-sysupgrade.itb
   ```

   `-F` forces flash even if metadata missing. Router reboots; after boot overlay should mount rw.

3. **If overlay still broken after sysupgrade:** may need manual UBI volume delete:

   ```bash
   mount -o remount,rw /overlay
   umount /overlay
   ubirmvol /dev/ubi0 -n 5
   reboot
   ```

   On next boot init creates a new volume and overlay should work.

4. **After repair:** apply [Internet access](#internet-access-opkg) template (VLAN 102 for Belkin #3) and verify persistence with `reboot`.

## Kiss of Death (OKD) on Belkin RT3200 / Linksys E8450

### What is Kiss of Death?

**Kiss of Death (OKD)** is a common brick on Belkin RT3200 (Linksys E8450) running OpenWrt. The router becomes fully unresponsive: no lights, no LEDs, no response after power cycle, power loss, or normal reboot.

**Root cause:** Bootloader bug (TF-A BL2 v2.9/v2.10). On boot it reads NAND and a correctable error (common bad block) causes fatal failure. Not hardware; bootloader firmware in flash.

**Typical trigger:** Power cycle via relays, power loss, or reboot after tests (including initramfs in RAM). RAM tests do not write flash but coincide with power cycles that trigger the bug.

**Reference:** [OpenWrt Wiki - Recovery from OpenWrt Kiss of Death (OKD) - Linksys E8450](https://openwrt.org/toh/linksys/e8450#recovery_from_openwrt_kiss_of_death_okd)

### Recovery (procedure used March 2026)

Use [**mtk_uartboot**](https://github.com/981213/mtk_uartboot) + serial + TFTP to rewrite fixed bootloader, no JTAG.

#### Prerequisites

- **USB-serial adapter:** Use a **reliable** 3.3 V TTL adapter for this flow. **CH340** adapters often complete the BootROM handshake then **time out** while uploading the BL2 payload (`sending payload...` / panic in `bootrom.rs`) because they drop bytes under sustained traffic. **FT232RNL** (or another genuine **FTDI** / **CP210x** known to work at **460800+**) is strongly recommended. Plug the adapter **directly** into the PC when possible; long chains of **USB hubs** make CH340 failures more likely. See [USB-TTL serial adapters](catalogo-hardware.md#usb-ttl-serial-adapters).
- 3.3V USB-serial TTL on J10 (router TX → adapter RX, RX → TX, common GND; do not connect VCC).
- Ethernet cable LAN 1 to PC.
- Files in a folder (e.g. `~/recoverBelkin`):
  - [`mt7622-ram-1ddr-bl2.bin`](https://github.com/981213/mtk_uartboot/raw/master/mt7622-ram-1ddr-bl2.bin) - RAM loader (mtk_uartboot).
  - [`openwrt-mediatek-mt7622-linksys_e8450-ubi-preloader.bin`](https://downloads.openwrt.org/releases/22.03.7/targets/mediatek/mt7622/openwrt-22.03.7-mediatek-mt7622-linksys_e8450-ubi-preloader.bin) - fixed preloader (22.03.7, renamed).
  - [`openwrt-23.05.5-mediatek-mt7622-linksys_e8450-ubi-bl31-uboot.fip`](https://downloads.openwrt.org/releases/23.05.5/targets/mediatek/mt7622/openwrt-23.05.5-mediatek-mt7622-linksys_e8450-ubi-bl31-uboot.fip) - FIP with fixed U-Boot.
  - [`mtk_uartboot`](https://github.com/981213/mtk_uartboot) - Linux binary.
- TFTP: `sudo apt install tftpd-hpa`. Configure `/etc/default/tftpd-hpa` with `TFTP_DIRECTORY="/srv/tftpboot"`, `TFTP_ADDRESS=":69"`, `TFTP_OPTIONS="--secure"`.
- Copy preloader and FIP to `/srv/tftpboot/`.
- Static IP 192.168.1.254/24 on Ethernet: `sudo ip addr add 192.168.1.254/24 dev <interface>; sudo ip link set <interface> up`.
- Serial permissions: `sudo usermod -a -G dialout $USER` (logout/login).
- Restart TFTP: `sudo systemctl restart tftpd-hpa`.

#### Step by step

1. **Run mtk_uartboot** (adjust `/dev/ttyUSB0` if needed). If the serial adapter is marginal, try `--brom-load-baudrate 115200 --bl2-load-baudrate 115200` (slower but sometimes enough for CH340; **FT232RNL** usually needs no flags):

   ```bash
   sudo ./mtk_uartboot -s /dev/ttyUSB0 -a -p mt7622-ram-1ddr-bl2.bin -f openwrt-23.05.5-mediatek-mt7622-linksys_e8450-ubi-bl31-uboot.fip
   ```

   After you see **Received FIP** / U-Boot output, open the console in a **second** terminal: `screen /dev/ttyUSB0 115200` (avoid `&& screen` in one line if the tool exits with a non-zero code).

2. **Power on the router** right after pressing Enter. In a few seconds the handshake should complete and BL2 should start loading the FIP.

3. **In screen:** press down arrow to interrupt autoboot and enter U-Boot menu.

4. **Write preloader (option 8):** choose "8. Load BL2 preloader via TFTP then write to flash". Wait "Loading..." → "Erasing..." → "Writing 131072 byte(s)..." four times (offsets 0x0, 0x20000, 0x40000, 0x60000). Press Enter to return to menu.

5. **Write FIP (option 7):** choose "7. Load BL31+U-Boot FIP via TFTP then write to flash". Wait same write flow. Press Enter to return.

6. **Reboot:** option "9. Reboot" or wait for auto reboot.

7. **Disconnect** serial and Ethernet. Power router from PSU only. Should boot with lights and OpenWrt/LibreMesh banner.

#### Notes

- If **mtk_uartboot** panics with **Operation timed out** right after `sending payload...`, the cause is almost always the **USB-serial chip** (CH340 + hubs) or wiring; switching to **FT232RNL** fixed this in lab practice (April 2026).
- If ARP retry fails: in U-Boot run `setenv ethaddr 00:11:22:33:44:55; saveenv`.
- If it does not boot after process, repeat 1-6 (sometimes two attempts).
- Verify: after boot, `grep "(release)" /dev/mtd0ro` should show v2.4 or fixed version.
- Once applied, fix is permanent and OKD should not recur.

---

## Banana Pi R4

**Serial:** `/dev/bpi-r4`. Mapping: [summary table](#summary-table).

**Firmware (detail):** mediatek/filogic.

**U-Boot:** Interrupt char `\x1b` (ESC). The boot menu requires a single-byte interrupt for proactive capture by Labgrid. Multi-byte sequences (e.g. `\\x0` literal) disable proactive mode and cause timeouts.

**Network:** [Internet access](#internet-access-opkg) template. No special UCI.

---

## OpenWRT One

**Serial:** `/dev/openwrt-one`. Switch ports (PoE + data LAN) and VLAN: [summary table](#summary-table) and [switch-config 5.2](switch-config.md#52-openwrt-one-two-cables-poe-lan-for-u-boot-tftp).

**Firmware (detail):** OpenWrt 24.10.0-rc2, mediatek/filogic (update summary table if version bumps).

**U-Boot:** Interrupt char `\x1b` (ESC). Same single-byte proactive interrupt requirement as Banana Pi R4. `login_timeout: 30`.

**Swap eth0/eth1:** OpenWRT One has PoE on one port only (eth0). Default eth0=WAN, eth1=LAN. If cable is on PoE port, host cannot reach 192.168.1.1 because br-lan (eth1) has no link. Swap:

```bash
uci delete network.@device[0].ports
uci add_list network.@device[0].ports='eth0'
uci set network.wan.device='eth1'
uci set network.wan6.device='eth1'
uci commit network
/etc/init.d/network restart
```

Result: eth0 (PoE) → br-lan → 192.168.1.1. Connect switch cable to PoE port.

After swap: [Internet access](#internet-access-opkg) template.

**U-Boot TFTP with PoE:** PoE power-cycle could make U-Boot fail with external PHY timeout (EN8811H). Fix: connect **both** ports to switch - WAN (PoE) to port 1 for power; LAN to port 16 for data (VLAN 104). U-Boot uses LAN link (internal PHY) and avoids timeout. See [switch-config 5.2](switch-config.md#52-openwrt-one-two-cables-poe-lan-for-u-boot-tftp).

---

## Librerouter 1

**Serial:** `/dev/librerouter-1`. Mapping: [summary table](#summary-table).

**Power:** 12V DC barrel jack via Arduino relay channel 4 (`arduino_relay_control.py on/off 4`). PDU: `fcefyn-arduino`, index 4.

**Firmware (detail):** LibreRouterOs 23.05-SNAPSHOT + LibreMesh (line summarized in table).

**Network:** [Internet access](#internet-access-opkg) template.

**opkg feeds:** `23.05-SNAPSHOT` feeds do not exist. Move to 23.05.2 and comment missing feeds:

```bash
sed -i 's/23.05-SNAPSHOT/23.05.2/g' /etc/opkg/distfeeds.conf
sed -i -e '/librerouteros_libremesh/s/^/#/' -e '/librerouteros_librerouter/s/^/#/' -e '/librerouteros_tmate/s/^/#/' /etc/opkg/distfeeds.conf
opkg update
```

**SSH:** `ssh dut-librerouter-1` (needs `~/.ssh/config` entry from `configs/templates/ssh_config_fcefyn` and `labgrid-bound-connect`).

---

## Librerouter 2

Mapping and state: [summary table](#summary-table) (port 3, VLAN 106). **Serial:** - (fill when cabled).

**Firmware:** *(TBD)*

---

## Librerouter 3

Mapping and state: [summary table](#summary-table) (port 4, VLAN 107). **Serial:** - (fill when cabled).

**Firmware:** *(TBD)*

---

## Maintaining the DUT table

1. Update **summary table** first (port, VLAN, power, short firmware, SSH/Internet, notes).
2. In the DUT section: only detail that does not fit the table (serial, arch, UCI, feeds, troubleshooting).
3. `cat /etc/os-release` on DUT if firmware line changes.
4. Record non-obvious UCI or procedures.
