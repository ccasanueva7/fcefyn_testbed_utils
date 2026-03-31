# Lab hardware catalog

**Photos and main characteristics** of the physical testbed equipment.

## Sponsors and acknowledgments {: #sponsors-and-acknowledgments }

Part of the equipment arrived as **donations** from manufacturers and institutions:

| Sponsor | Equipment |
|---------|-----------|
| [**Banana Pi**](https://banana-pi.org/) | **OpenWrt One** and **Banana Pi R4** boards. |
| [**Nisuta**](https://nisuta.com/) | **USB hub** connected to the host. |
| [**AlterMundi**](https://altermundi.net/) | Several **LibreRouter** units; **TP-Link TL-WDR3500** testbed **gateway** router. |
| [**LibreMesh**](https://libremesh.org/) / [**aparcar**](https://github.com/aparcar) | **Belkin RT3200** DUT routers (LibreMesh ecosystem; hardware via community / typical contact **aparcar**). |
| [**FCEFyN**](https://fcefyn.unc.edu.ar/) | **Lenovo ThinkPad T430** orchestration host (**university** equipment). |
| [**GL.iNet**](https://www.gl-inet.com/) | **Mango** router; **not yet** integrated in the rack (hardware too limited for the usual DUT role in the lab). |

<div class="catalog-sponsors" markdown="0">
<div class="catalog-sponsors__row">
<a href="https://banana-pi.org/" class="catalog-sponsors__link" title="Banana Pi"><img src="../../img/logos/bananapi.png" alt="Banana Pi logo" loading="lazy" decoding="async"></a>
<a href="https://nisuta.com/" class="catalog-sponsors__link" title="Nisuta"><img src="../../img/logos/nisuta.png" alt="Nisuta logo" loading="lazy" decoding="async"></a>
<a href="https://altermundi.net/" class="catalog-sponsors__link" title="AlterMundi"><img src="../../img/logos/altermundi.png" alt="AlterMundi logo" loading="lazy" decoding="async"></a>
<a href="https://www.fcefyn.unc.edu.ar/" class="catalog-sponsors__link" title="FCEFyN - UNC"><img src="../../img/logos/fcefyn.png" alt="FCEFyN logo" loading="lazy" decoding="async"></a>
<a href="https://www.argentina.gob.ar/inti" class="catalog-sponsors__link" title="INTI"><img src="../../img/logos/inti.png" alt="INTI logo" loading="lazy" decoding="async"></a>
<a href="https://www.gl-inet.com/" class="catalog-sponsors__link" title="GL.iNet"><img src="../../img/logos/glinet.png" alt="GL.iNet logo" loading="lazy" decoding="async"></a>
</div>
</div>

## Arduino-controlled rack relays {: #arduino-rack-relays }

The **Arduino Nano** switches power to DUTs and rack infrastructure (cooler, PSU) via **11** USB-serial channels; it does **not** switch the network switch feed. Details: [arduino-relay.md](arduino-relay.md).

### Arduino Nano

<div class="catalog-hardware-row catalog-hardware-row--balanced" markdown="block">

| Attribute | Detail |
|-----------|--------|
| MCU | Microchip **ATmega328P** |
| Logic voltage | 5 V |
| USB | Mini-USB or USB depending on clone (serial to PC) |
| Clock | 16 MHz (typical) |
| In the lab | Custom firmware; **11 outputs** to SSR modules and mechanical relays |

![Arduino Nano (relay control)](../img/hardware/arduino-nano.jpg)

</div>

### 4-channel SSR module (Omron G3MB-202P)

**CH2** feeds the AC cooler (channel 9). **CH1** (channel 8, D10) has signal on the UTP but **no load** in the current build: it does not switch the network switch feed (SG2016P stays on fixed mains). **CH3** and **CH4**: wiring per [arduino-relay.md](arduino-relay.md).

<div class="catalog-hardware-row catalog-hardware-row--balanced" markdown="block">

| Parameter | Value |
|-----------|-------|
| Relay | Omron G3MB-202P per channel; phototriac; zero-cross |
| Control | 5 V DC; active low (~0-2.5 V, ~2 mA); module up to ~48 mA |
| Load | 100-240 V AC, 0.1-2 A per channel; fuse |
| Board / connections | ~57 x 55 x 25 mm; **DC+** / **DC-**; **CH1-CH4** |
| In the lab | CH1 no load (D10 wired); CH2 cooler; CH3-CH4 per [arduino-relay](arduino-relay.md) |

![4-channel Omron G3MB-202P SSR module](../img/hardware/ssr-omron.png)

</div>

### Fotek SSR-25DA (channel 10)

This SSR cuts phase to the **AC** load on channel 10 (rack PSU). In Arduino firmware logic is **active high** (channel 10: HIGH = ON; channels 0-9: LOW = ON).

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--micro-photo" markdown="block">

| Parameter | Value |
|-----------|-------|
| Type | DC in → AC out, high voltage |
| Input | 4-32 V DC |
| Output | 90-480 V AC, up to 25 A (per manufacturer and wiring) |

![Fotek SSR-25DA](../img/hardware/ssr-fotek.png)

</div>

### 8-relay module

Used for channels **0 to 7** (Arduino pins **D2-D9**): optocoupled electromechanical relays, **5 V DC** supply.

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--relay8" markdown="block">

| Parameter | Value |
|-----------|-------|
| Supply | 5 V DC; opto; SMD LED per channel |
| Contacts | Up to 10 A @ 250 V AC or 30 V DC / 10 A (per module) |
| Firmware | Same digital drive pattern as other inputs |

![8-channel electromechanical relay module](../img/hardware/8-channel-relay.png)

</div>

**AC to rack outlet boxes:** modular switch with **phase break**; visual reference under [Electrical safety and connection](#electrical-safety-and-connection).

## Electrical safety and connection {: #electrical-safety-and-connection }

Reference parts for **AC** (outlet), **12 V DC** positive from DUT relays toward jacks, **common GND** from PSU toward jacks, and **DC connector** assembly per DUT. Wiring detail: [arduino-relay](arduino-relay.md).

| Part | Role in the rack |
|------|------------------|
| Modular switch / flush outlet | **AC** branch toward outlet boxes; **phase break**. |
| Polyamide terminal block | **12 V+** from DUT relay outputs toward cables to barrel jacks. |
| DIN-rail unipolar distributor (ground) | **GND** from **12 V** PSU toward barrel jack return per DUT. |
| Male DC plug with screw terminals | **Barrel jack** body feeding each DUT (workshop assembly). |

<div class="rack-gallery rack-gallery--catalog-safety" data-rack-gallery tabindex="0">
  <div class="rack-gallery__viewport">
    <figure class="rack-gallery__slide" data-caption="Modular outlet (phase break, AC branch).">
      <img src="../../img/hardware/caja-toma.png" alt="Modular flush outlet reference" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Polyamide terminal block: 12 V+ from DUT relays to jacks.">
      <img src="../../img/hardware/bornera-poliamida.png" alt="Polyamide pass-through terminal for 12 V positive" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="GND distributor on DIN rail: 12 V PSU to jacks.">
      <img src="../../img/hardware/borneradin.png" alt="Unipolar ground distributor on DIN rail" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Male DC plug with screw terminals: barrel jack per DUT.">
      <img src="../../img/hardware/plug_dc_macho.png" alt="Male DC connector with screw terminals for barrel jack" loading="lazy" decoding="async">
    </figure>
    <div class="rack-gallery__overlay">
      <span class="rack-gallery__counter" data-rack-counter aria-live="polite"></span>
      <button type="button" class="rack-gallery__btn" data-rack-prev aria-label="Previous image">&#8249;</button>
      <button type="button" class="rack-gallery__btn" data-rack-next aria-label="Next image">&#8250;</button>
    </div>
  </div>
  <p class="rack-gallery__caption" data-rack-caption></p>
</div>

## AC supply (channel 10 load) {: #ac-supply-channel-10-load }

The PSU feeding that **AC** branch plugs behind the **Fotek**; channel 10 role in the rack is explained in [arduino-relay](arduino-relay.md).

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--psu-photo" markdown="block">

| Specification | Value |
|---------------|-------|
| Brand / model | Coper Light metal case |
| Power | 480 W |
| Input | 12-110 VAC, 50/60 Hz |
| Output | 12-220 V |
| Operating temperature | 0-40 °C |
| Protection | Short circuit |

![Coper Light metal PSU](../img/hardware/psu.png)

</div>

## Bosser 120 mm AC fan {: #bosser-120mm-rack-fan }

**120 mm** frame axial fan at **220 V** mains at the **rack base** (not the Arduino 12 V supply). Pushes air into the curved printed duct; assembly with 3D parts is in [Physical rack](../diseno/rack-diseno-3d.md).

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--cooler-photo" markdown="block">

| Attribute | Value |
|-----------|-------|
| Brand | Bosser |
| Line | 220 V coolers |
| Model | **CBO-12038B-220** |
| Supply | AC **220 V** |
| Current | 0.09 A |
| Frequency | 50 / 60 Hz |
| Bearing | Ball |
| Form factor | **120 x 120 mm** frame |

![Bosser 120 mm fan (product reference)](../img/hardware/cooler_bosser.png)

</div>

In the lab the cooler is switched via **SSR** (channel 9); detail in [arduino-relay](arduino-relay.md).

## USB hub

Mounted in the rack and connected to the orchestration host: **metal enclosure** hub with several USB 3.0 ports.

*Donation **Nisuta** (see [sponsors table](#sponsors-and-acknowledgments)).*

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--hub-photo" markdown="block">

| Attribute | Detail |
|-----------|--------|
| USB ports | 10 x USB 3.0 (5 Gbps), type A female |
| Fast charge | 1 x QC3.0 port (5 V / 3 A; 9 V / 2 A; 12 V / 1.5 A) |
| Compatibility | USB 2.0 and older |
| Enclosure | Metal |
| Included cable | USB 3.0 A male - B male, 1 m (to PC) |
| External PSU | 12 V, 5.4 A |
| Per USB 3.0 port | Up to 5 V, 0.9 A max per port |

![10-port USB 3.0 hub with PSU](../img/hardware/hubusb-NSUH113Q.png)

</div>

With several serial adapters and peripherals, the hub runs with **external PSU connected** in addition to the PC USB bus.

## Managed switch (TP-Link SG2016P)

**L2+** lab switch: trunk to host and gateway, access ports to DUTs, some ports **PoE**. Configuration: [switch-config.md](switch-config.md). **Switch power does not go through the Arduino or rack SSR module** (fixed mains); see [arduino-relay](arduino-relay.md).

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--switch-photo" markdown="block">

| Attribute | Detail |
|-----------|--------|
| Model | **TP-Link SG2016P** |
| Ports | **16 x Gigabit Ethernet** |
| PoE | **8 ports** with PoE (802.3af/at per manufacturer datasheet) |
| Management | Web / SNMP; VLAN 802.1Q, trunk and access |
| In the lab | Port 9 trunk **host** (Lenovo), 10 trunk **gateway**, 1-4 and 11-16 to DUTs (see switch-config) |

![TP-Link SG2016P](../img/hardware/tp-link-sg2016p-switch.png)

</div>

## Orchestration host (Lenovo ThinkPad T430)

Lab orchestration host is a **Lenovo ThinkPad T430** notebook with **Ubuntu**: Labgrid, dnsmasq/TFTP, switch scripts, PDUDaemon, and CI runner. Documentation: [host-config.md](host-config.md).

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--dut-board" markdown="block">

| Attribute | Detail |
|-----------|--------|
| Model | **Lenovo ThinkPad T430** (14" chassis, **T430** generation) |
| Platform | Intel **QM77** chipset; **Ivy Bridge** mobile dual-core CPU (SKU varies) |
| RAM | **DDR3L** 1600 MHz; up to **16 GB** (2 x SO-DIMM) |
| Storage | **2.5" SATA** bay (SSD/HDD per lab unit) |
| Ethernet | **1 x GbE** Intel (e.g. **82579LM**), RJ-45 to switch (802.1Q trunk; typical iface `enp0s25`) |
| USB | **2 x USB 3.0** + **2 x USB 2.0** |
| Display | **14"** (resolution per panel) |
| Video outputs | VGA, **Mini DisplayPort** |
| Expansion | **ExpressCard/54** |
| OS in lab | **Ubuntu** (LTS); Netplan + NetworkManager: [host-config](host-config.md) |
| Lab role | Labgrid, dnsmasq/TFTP, switch scripts, PDUDaemon, SSH to DUTs, CI runners |

![Lenovo ThinkPad T430 (lab host)](../img/hardware/lenovo-t430.png)

</div>

*Host **Lenovo**: **faculty** property (FCEFyN / UNC). **INTI** contributes **project hours** (no hardware donation); **INTI** logo in the strip below is acknowledgment only.*

## USB-TTL serial adapters

**USB-UART TTL** converters for DUT console. Symlinks under `/dev/` and **udev** rules: [host-config](host-config.md#7-udev-rules-for-serial-adapters).

| Type | In the lab |
|------|------------|
| **FT232RNL** | Preferred: **one USB serial per unit**; **udev** may not depend on hub port. |
| **CH340** | Acceptable budget option; clones share **VID/PID**. TTL level per jumper (**3.3 V** / **5 V**). |
| **CH341** | Budget; **not** reliable on **LibreRouter** console in the rack: during boot serial showed garbage and **U-Boot prompt could not be captured** with labgrid/minicom at 115200, breaking TFTP boot and tests. After **replacing the adapter** with an FT232RNL, console became readable. |
| **Three cheap generics** (last 3 carousel photos) | **Not** used in rack: no DUT console; after DUT reboot **USB must be re-plugged** to recover serial; overheating or sporadic failures under test. |

<div class="rack-gallery rack-gallery--catalog-ttl" data-rack-gallery tabindex="0">
  <div class="rack-gallery__viewport">
    <figure class="rack-gallery__slide" data-caption="FT232RNL (preferred).">
      <img src="../../img/hardware/usb-ttl-Ft232rnl.png" alt="FTDI FT232RNL USB-TTL adapter" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="CH340.">
      <img src="../../img/hardware/usb-ttl-ch340.png" alt="CH340 USB-TTL adapter" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="CH341 (budget): unreadable console on lab LibreRouter at boot; see table.">
      <img src="../../img/hardware/ch341.jpg" alt="CH341 USB-TTL adapter" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Cheap generic: not recommended.">
      <img src="../../img/hardware/usb-ttl-bad1.jpg" alt="Cheap generic USB-TTL adapter 1" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Cheap generic: not recommended.">
      <img src="../../img/hardware/usb-ttl-bad2.jpg" alt="Cheap generic USB-TTL adapter 2" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Cheap generic: not recommended.">
      <img src="../../img/hardware/usb-ttl-bad3.jpg" alt="Cheap generic USB-TTL adapter 3" loading="lazy" decoding="async">
    </figure>
    <div class="rack-gallery__overlay">
      <span class="rack-gallery__counter" data-rack-counter aria-live="polite"></span>
      <button type="button" class="rack-gallery__btn" data-rack-prev aria-label="Previous image">&#8249;</button>
      <button type="button" class="rack-gallery__btn" data-rack-next aria-label="Next image">&#8250;</button>
    </div>
  </div>
  <p class="rack-gallery__caption" data-rack-caption></p>
</div>

For **logs** when boot fails in multi-node tests (libremesh-tests, `mesh_boot_node`), see [LibreMesh testing approach](https://github.com/francoriba/libremesh-tests/blob/main/docs/libremesh-testing-approach.md#mesh-boot-logs) (libremesh-tests repo).

## Testbed gateway (TP-Link TL-WDR3500)

**OpenWrt** router on switch trunk: DUT VLANs, `.254` gateway per subnet. Detail in [gateway.md](gateway.md).

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--gateway-photo" markdown="block">

| Attribute | Detail |
|-----------|--------|
| Manufacturer | TP-Link |
| SoC | Qualcomm Atheros **AR9344** (MIPS 74Kc) ~560 MHz |
| Architecture | MIPS |
| RAM | 128 MB |
| Flash | 8 MB NOR |
| Ethernet | 5 x **100 Mbit/s** (1 WAN + 4 LAN, integrated AR934x switch) |
| Wi-Fi | Dual-band **N600**: 2.4 GHz 2x2 + 5 GHz 2x2 (802.11n) |
| PoE | No |
| USB | 1 x USB 2.0 |
| OpenWrt | **ath79**; in lab as gateway (e.g. 24.x / 25.x). [TOH / techdata](https://openwrt.org/toh/hwdata/tp-link/tp-link_tl-wdr3500_v1) |

![TP-Link TL-WDR3500 (testbed gateway)](../img/hardware/dut-tlwdr3500.jpg)

</div>

!!! note "TL-WDR3500 role in the testbed"
    For current standards CPU and Fast Ethernet are limiting; the unit is adequate as **VLAN/gateway router** for the lab, not as a high-performance DUT.

*Donation **AlterMundi**.*

## Devices under test (DUTs)

Rack status, switch ports, VLANs, firmware: [duts-config.md](duts-config.md). Technical sheets per model in use; data may vary by board revision. General reference: [OpenWrt Techdata](https://openwrt.org/toh/start).

### OpenWrt One

**Official OpenWrt community** board (Banana Pi hardware); dual NAND + NOR flash oriented to recovery.

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--dut-board" markdown="block">

| Attribute | Detail |
|-----------|--------|
| Manufacturer / design | Banana Pi (hardware) + **OpenWrt** (official project design) |
| SoC | MediaTek **MT7981B** (Filogic 820), dual-core Cortex-A53 @ 1.3 GHz |
| Architecture | ARM64 |
| RAM | 1 GB DDR4 |
| Storage | **256 MB** SPI NAND + **16 MB** SPI NOR (recovery) |
| Expansion | **M.2** 2242/2230 **NVMe** (PCIe Gen2 x1) |
| Ethernet | 1 x **2.5 GbE** (WAN) + 1 x **1 GbE** (LAN) |
| Wi-Fi | Wi-Fi 6, **MT7976C**: 2.4 GHz **2x2** + 5 GHz **3x3** |
| PoE | **Yes** (802.3af/at on WAN input, per product docs) |
| USB | 1 x USB 2.0 type A + **USB-C** (power / data, per SKU) |
| Other | RTC with battery, **mikroBUS**, MMCX antennas |
| OpenWrt | **Official** support (`mediatek/filogic` images) |

![OpenWrt One](../img/hardware/dut-openwrt-one.jpg)

</div>

*Donation **Banana Pi**.*

### Banana Pi BPI-R4

Powerful router with **10G** and optional Wi-Fi 7 via miniPCIe modules; used in the lab as a high-performance DUT.

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--dut-board" markdown="block">

| Attribute | Detail |
|-----------|--------|
| Manufacturer | Banana Pi (Sinovoip) |
| SoC | MediaTek **MT7988A** (Filogic 880), quad-core Cortex-A73 @ 1.8 GHz |
| Architecture | ARM64 |
| RAM | **4 GB or 8 GB** DDR4 (per commercial variant) |
| Storage | **8 GB eMMC** + SPI-NAND (**128 MB or 256 MB**, per revision) |
| Expansion | microSD + **M.2 NVMe** (KEY-M) + M.2 KEY-B (cellular, per board) |
| Ethernet | **4 x 1 GbE** + **2 x 10 GbE SFP+** (RJ45/SFP combo variants exist) |
| Wi-Fi | No on-board radio; **2 x miniPCIe** (PCIe 3.0) for modules (e.g. Wi-Fi 7) |
| PoE | Not integrated on base board |
| USB | 1 x **USB 3.2** |
| OpenWrt | **Yes** (`mediatek/filogic`); in lab as DUT with 10G links |

![Banana Pi BPI-R4](../img/hardware/dut-bpi-r4.jpg)

</div>

*Donation **Banana Pi**.*

### Libre Router (AlterMundi / LibreRouter.org)

Open hardware for **community networks** and LibreMesh; in the lab with case or bare board per unit.

<div class="catalog-hardware-row catalog-hardware-row--double-img" markdown="block">

| Attribute | Detail |
|-----------|--------|
| Manufacturer / project | **AlterMundi** / **LibreRouter** community |
| SoC | Qualcomm Atheros **QCA9558** MIPS ~720 MHz |
| Architecture | MIPS |
| RAM | 128 MB DDR2 |
| Flash | 16 MB NOR |
| Ethernet | 2 x **1 GbE** (QCA8337 switch), **PoE** and **passthrough** per design |
| Wi-Fi | Integrated 2.4 GHz **2x2** + up to **2 x miniPCIe** for 5 GHz radios (e.g. 802.11an/ac) |
| USB | **2 x USB 2.0** on PCB (may be inaccessible in some enclosures) |
| Other | Published schematics/Gerbers, GPIO, watchdog |
| OpenWrt / LibreMesh | **Yes**; in lab often **LibreRouterOS** / LibreMesh derived from OpenWrt |

<div class="catalog-hardware-row__stack">
<p><img src="../../img/hardware/dut-librerouter-case.png" alt="Libre Router (rack unit)" /></p>
<p><img src="../../img/hardware/dut-librerouter.jpg" alt="Libre Router (board)" /></p>
</div>

</div>

*Donation **AlterMundi** (LibreRouter project).*

### Belkin RT3200 / Linksys E8450

Same hardware under **Belkin** (RT3200) and **Linksys** (E8450) brands. OpenWrt uses **UBI** layout.

<div class="catalog-hardware-row catalog-hardware-row--double-img" markdown="block">

| Attribute | Detail |
|-----------|--------|
| Commercial OEM | **Belkin** (RT3200) / **Linksys** (E8450) |
| SoC | MediaTek **MT7622BV** (dual Cortex-A53) + **MT7915E** (Wi-Fi 6) |
| Architecture | ARM64 |
| RAM | 512 MB DDR3 |
| Flash | 128 MB SPI-NAND (**UBI** layout on OpenWrt) |
| Ethernet | 5 x **1 GbE** (1 WAN + 4 LAN) |
| Wi-Fi | Dual-band **AX3200** (per manufacturer spec) |
| PoE | No |
| USB | 1 x USB 2.0 on chassis |
| OpenWrt | Install and **UBI** migration: [TOH E8450 / RT3200](https://openwrt.org/toh/linksys/e8450) |

<div class="catalog-hardware-row__stack">
<p><img src="../../img/hardware/dut-belkinrt3200.png" alt="Belkin RT3200" /></p>
<p><img src="../../img/hardware/dut-linksyse8450.png" alt="Linksys E8450 (same hardware)" /></p>
</div>

</div>

*Hardware **LibreMesh** community / **aparcar** channel (see [sponsors](#sponsors-and-acknowledgments)).*
