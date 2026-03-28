# Catálogo de hardware del lab

Se presentan **imágenes y características principales** del equipamiento físico del banco de pruebas.

## Aportes y agradecimientos {: #aportes-y-agradecimientos }

Parte del equipamiento llegó como **aporte** de fabricantes e instituciones:

| Aportante                                      | Equipamiento                                                                                                  |
|------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| [**Banana Pi**](https://banana-pi.org/)        | Placas **OpenWrt One** y **Banana Pi R4**.                                                                    |
| [**Nisuta**](https://nisuta.com/)              | **Hub USB** conectado al host.                                                                                |
| [**AlterMundi**](https://altermundi.net/)      | Varias unidades **LibreRouter**.                                                                              |
| [**INTI**](https://www.argentina.gob.ar/inti)  | Notebook **Lenovo ThinkPad T430** (host); routers **Belkin RT3200**; router gateway **TP-Link TL-WDR3500**.   |
| [**GL.iNet**](https://www.gl-inet.com/)        | Router **Mango**; **aún no** integrado al rack (hardware muy limitado para el rol habitual de DUT en el banco). |

<div class="catalog-sponsors" markdown="0">
<div class="catalog-sponsors__row">
<a href="https://banana-pi.org/" class="catalog-sponsors__link" title="Banana Pi"><img src="../../img/logos/bananapi.png" alt="Logo Banana Pi" loading="lazy" decoding="async"></a>
<a href="https://nisuta.com/" class="catalog-sponsors__link" title="Nisuta"><img src="../../img/logos/nisuta.png" alt="Logo Nisuta" loading="lazy" decoding="async"></a>
<a href="https://altermundi.net/" class="catalog-sponsors__link" title="AlterMundi"><img src="../../img/logos/altermundi.png" alt="Logo AlterMundi" loading="lazy" decoding="async"></a>
<a href="https://www.argentina.gob.ar/inti" class="catalog-sponsors__link" title="INTI"><img src="../../img/logos/inti.png" alt="Logo INTI" loading="lazy" decoding="async"></a>
<a href="https://www.gl-inet.com/" class="catalog-sponsors__link" title="GL.iNet"><img src="../../img/logos/glinet.png" alt="Logo GL.iNet" loading="lazy" decoding="async"></a>
</div>
</div>

## Relés controlados por microcontrolador Arduino

El **Arduino Nano** controla la potencia de los DUTs y de cargas de infra del rack (cooler, fuente) vía **11 canales** USB-Serial; **no** conmuta la alimentación del switch de red. Detalle: [arduino-relay.md](arduino-relay.md).

### Arduino Nano

<div class="catalog-hardware-row catalog-hardware-row--balanced" markdown="block">

| Característica | Detalle |
|----------------|---------|
| MCU | Microchip **ATmega328P** |
| Voltaje lógico | 5 V |
| USB | Mini-USB o USB según clon (serial hacia el PC) |
| Reloj | 16 MHz (típico) |
| En el lab | Firmware propio; **11 salidas** hacia módulos SSR y relés mecánicos |

![Arduino Nano (control de relés)](../img/hardware/arduino-nano.jpg)

</div>

### Módulo SSR de 4 canales (Omron G3MB-202P)

**CH2** alimenta el cooler AC (canal 9). **CH1** (canal 8, D10) tiene señal en el UTP pero **sin carga** en el montaje actual: no conmuta la alimentación del switch de red (el SG2016P va a red fija). **CH3** y **CH4**: cableado según [arduino-relay.md](arduino-relay.md).

<div class="catalog-hardware-row catalog-hardware-row--balanced" markdown="block">

| Parámetro | Valor |
|-----------|--------|
| Relé | Omron G3MB-202P por canal; fototriac; zero-cross |
| Control | 5 V DC; activo en bajo (~0-2,5 V, ~2 mA); módulo hasta ~48 mA |
| Carga | 100-240 V AC, 0,1-2 A por canal; fusible |
| Placa / conexiones | ~57 x 55 x 25 mm; **DC+** / **DC-**; **CH1-CH4** |
| En el lab | CH1 sin carga (D10 cableado); CH2 cooler; CH3-CH4 según [arduino-relay](arduino-relay.md) |

![Módulo SSR de 4 canales Omron G3MB-202P](../img/hardware/ssr-omron.png)

</div>

### Fotek SSR-25DA (canal 10)

Este relé corta la fase hacia la carga en **CA** del canal 10 (la fuente del rack). En el firmware del Arduino la lógica es **activa en alto** (canal 10: HIGH = ON; canales 0-9: LOW = ON).

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--micro-photo" markdown="block">

| Parámetro | Valor |
|-----------|--------|
| Tipo | CC → CA, alto voltaje |
| Entrada | 4-32 V DC |
| Salida | 90-480 V AC, hasta 25 A (según fabricante y cableado) |

![Fotek SSR-25DA](../img/hardware/ssr-fotek.png)

</div>

### Módulo de 8 relés

Sirve para los canales **0 a 7** (pines **D2-D9** del Arduino): relés electromecánicos optoacoplados, alimentación **5 V DC**.

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--relay8" markdown="block">

| Parámetro | Valor |
|-----------|--------|
| Alimentación | 5 V DC; opto; LED SMD por canal |
| Contactos | Hasta 10 A @ 250 V AC o 30 V DC / 10 A (según módulo) |
| Firmware | Mismo patrón de disparo digital que el resto de entradas |

![Módulo de 8 relés electromecánicos](../img/hardware/8-channel-relay.png)

</div>

**AC hacia cajas de toma del rack:** llave modular con **corte de fase**; referencia visual en [Seguridad eléctrica y conexión](#seguridad-electrica-y-conexion).

## Seguridad eléctrica y conexión {: #seguridad-electrica-y-conexion }

Piezas de referencia para **AC** (toma), **12 V DC** positivo desde relés DUT hacia jacks, **GND** común desde la fuente hacia jacks, y armado de **conectores DC** por DUT. Detalle de cableado: [arduino-relay](arduino-relay.md).

| Pieza | Función en el rack |
|-------|-------------------|
| Llave modular / toma empotrada | Rama **AC** hacia cajas de toma; **corte de fase**. |
| Bornera pasacable (poliamida) | **12 V+** desde salidas de relés DUT hacia cables hacia jacks barrel. |
| Distribuidor unipolar riel DIN (tierra) | **GND** desde fuente **12 V** hacia retorno de jacks barrel por DUT. |
| Plug DC macho con bornera | Cuerpo del conector **jack barrel** que alimenta cada DUT (armado en taller). |

<div class="rack-gallery rack-gallery--catalog-safety" data-rack-gallery tabindex="0">
  <div class="rack-gallery__viewport">
    <figure class="rack-gallery__slide" data-caption="Toma modular (corte de fase, rama AC).">
      <img src="../../img/hardware/caja-toma.png" alt="Llave modular toma empotrada referencia rack" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Bornera poliamida: 12 V+ relés DUT hacia jacks.">
      <img src="../../img/hardware/bornera-poliamida.png" alt="Bornera pasacable poliamida para 12 V positivo" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Distribuidor GND en riel DIN: fuente 12 V a jacks.">
      <img src="../../img/hardware/borneradin.png" alt="Distribuidor unipolar tierra riel DIN" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Plug DC macho con bornera: jack barrel por DUT.">
      <img src="../../img/hardware/plug_dc_macho.png" alt="Conector DC macho con bornera para jack barrel" loading="lazy" decoding="async">
    </figure>
    <div class="rack-gallery__overlay">
      <span class="rack-gallery__counter" data-rack-counter aria-live="polite"></span>
      <button type="button" class="rack-gallery__btn" data-rack-prev aria-label="Imagen anterior">&#8249;</button>
      <button type="button" class="rack-gallery__btn" data-rack-next aria-label="Imagen siguiente">&#8250;</button>
    </div>
  </div>
  <p class="rack-gallery__caption" data-rack-caption></p>
</div>

## Fuente AC (carga canal 10)

La fuente que alimenta esa rama de **CA** se enchufa detrás del **Fotek**; el papel del canal 10 en el rack se explica en [arduino-relay](arduino-relay.md).

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--psu-photo" markdown="block">

| Especificación | Valor |
|----------------|-------|
| Marca/Modelo | Coper Light Metálica |
| Potencia | 480 W |
| Entrada | 12-110 VAC, 50/60 Hz |
| Salida | 12-220 V |
| Temperatura de funcionamiento | 0-40 °C |
| Protección | Cortocircuito |

![Fuente Coper Light metálica](../img/hardware/psu.png)

</div>

## Ventilador AC Bosser 120 mm

Axial de marco **120 mm** a **220 V** de red en la **base del rack** (no es alimentación 12 V del Arduino). Empuja aire hacia el conducto curvo impreso; el ensamble con piezas 3D está en [Rack físico](../diseno/rack-diseno-3d.md).

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--cooler-photo" markdown="block">

| Característica | Valor |
|----------------|-------|
| Marca | Bosser |
| Línea | Coolers 220 V |
| Modelo | **CBO-12038B-220** |
| Alimentación | AC **220 V** |
| Corriente | 0,09 A |
| Frecuencia | 50 / 60 Hz |
| Rodamiento | Ruleman |
| Formato | Marco **120 × 120 mm** |

![Ventilador Bosser 120 mm (referencia del producto)](../img/hardware/cooler_bosser.png)

</div>

En el lab el encendido del cooler va por **SSR** (canal 9); detalle en [arduino-relay](arduino-relay.md).

## Hub USB

Ubicado en el rack y conectado al host de orquestacón hay un hub de **carcasa metálica** con varios puertos USB 3.0.

*Aporte **Nisuta** (ver [tabla de aportes](#aportes-y-agradecimientos)).*

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--hub-photo" markdown="block">

| Característica | Detalle |
|----------------|---------|
| Puertos USB | 10 x USB 3.0 (5 Gbps), tipo A hembra |
| Carga rápida | 1 puerto QC3.0 (5 V / 3 A; 9 V / 2 A; 12 V / 1,5 A) |
| Compatibilidad | USB 2.0 y versiones anteriores |
| Carcaza | Metálica |
| Cable incluido | USB 3.0 A macho - B macho, 1 m (hacia la PC) |
| Fuente externa | 12 V, 5,4 A |
| Por puerto USB 3.0 | Hasta 5 V, 0,9 A máx. por puerto |

![Hub USB 10 puertos USB 3.0 con alimentación](../img/hardware/hubusb-NSUH113Q.png)

</div>

Con varios adaptadores seriales y periféricos, el hub se usa con **fuente externa conectada** además del bus USB de la PC.

## Switch gestionado (TP-Link SG2016P)

Switch **L2+** del lab: trunk al host y al gateway, puertos access a DUTs, parte de los puertos con **PoE**. Configuración: [switch-config.md](switch-config.md). La **alimentación del switch no pasa por el Arduino ni por el módulo SSR** del rack (red fija); ver [arduino-relay](arduino-relay.md).

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--switch-photo" markdown="block">

| Característica | Detalle |
|----------------|---------|
| Modelo | **TP-Link SG2016P** |
| Puertos | **16× Gigabit Ethernet** |
| PoE | **8 puertos** con PoE (802.3af/at según datasheet del fabricante) |
| Gestión | Web / SNMP; VLAN 802.1Q, trunk y access |
| En el lab | Puerto 9 trunk **host** (Lenovo), 10 trunk **gateway**, 1-4 y 11-16 a DUTs (ver switch-config) |

![TP-Link SG2016P](../img/hardware/tp-link-sg2016p-switch.png)

</div>

## Host de orquestación (Lenovo ThinkPad T430)

El host de orquestación del laboratorio es una notebook **Lenovo ThinkPad T430** con **Ubuntu**: Labgrid, dnsmasq/TFTP, scripts del switch, PDUDaemon y runner de CI. Documentación: [host-config.md](host-config.md).

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--dut-board" markdown="block">

| Característica | Detalle |
|----------------|---------|
| Modelo | **Lenovo ThinkPad T430** (chasis 14", generación **T430**) |
| Plataforma | Chipset Intel **QM77**; CPU **Ivy Bridge** móvil dual-core (SKU según unidad) |
| RAM | **DDR3L** 1600 MHz; hasta **16 GB** (2× SO-DIMM) |
| Almacenamiento | Bahía **2,5" SATA** (SSD/HDD según el equipo del lab) |
| Ethernet | **1× GbE** Intel (p. ej. **82579LM**), RJ-45 al switch (trunk 802.1Q; interfaz típica `enp0s25`) |
| USB | **2× USB 3.0** + **2× USB 2.0** |
| Pantalla | **14"** (resolución según panel) |
| Salidas de video | VGA, **Mini DisplayPort** |
| Expansión | **ExpressCard/54** |
| SO en el lab | **Ubuntu** (LTS); Netplan + NetworkManager: [host-config](host-config.md) |
| Rol en el lab | Labgrid, dnsmasq/TFTP, scripts del switch, PDUDaemon, SSH a DUTs, runners CI |

![Lenovo ThinkPad T430 (host del lab)](../img/hardware/lenovo-t430.png)

</div>

*Aporte **INTI** (Instituto Nacional de Tecnología Industrial).*

## Adaptadores seriales USB-TTL

Conversores **USB-UART TTL** para consola en DUTs. Symlinks bajo `/dev/` y reglas **udev**: [host-config](host-config.md#7-reglas-udev-para-adaptadores-seriales).

| Tipo | En el lab                                                                                                                                                                                                                                                                                                                                                    |
|------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **FT232RNL** | Preferido: serial USB **único por unidad**; **udev** puede no depender del puerto del hub.                                                                                                                                                                                                                                                                   |
| **CH340** | Económico aceptable; clones comparten **VID/PID**. Nivel TTL según jumper (**3,3 V** / **5 V**).                                                                                                                                                                                                                                                             |
| **CH341** | Económico; **no** resultó fiable en consola del **LibreRouter** del rack: durante el arranque la salida serial mostró caracteres ilegibles (basura) y **no** se pudo capturar el prompt de U-Boot con labgrid/minicom a 115200, por lo que fallaban TFTP boot y tests. Tras **cambiar el adaptador** por uno de los FT232RNL, la consola pasó a ser legible. |
| **Tres genéricos baratos** (últimas 3 fotos del carrusel) | **No** se usan en rack: sin consola en DUTs; tras reinicio del DUT hace falta **re-enchufar** el USB para recuperar serial; sobrecalentamiento o fallos esporádicos bajo tests.                                                                                                                                                                              |

<div class="rack-gallery rack-gallery--catalog-ttl" data-rack-gallery tabindex="0">
  <div class="rack-gallery__viewport">
    <figure class="rack-gallery__slide" data-caption="FT232RNL (preferido).">
      <img src="../../img/hardware/usb-ttl-Ft232rnl.png" alt="Adaptador USB-TTL FTDI FT232RNL" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="CH340.">
      <img src="../../img/hardware/usb-ttl-ch340.png" alt="Adaptador USB-TTL CH340" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="CH341 (económico): en LibreRouter del lab, consola ilegible al boot; ver tabla.">
      <img src="../../img/hardware/ch341.jpg" alt="Adaptador USB-TTL CH341" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Genérico barato: no recomendado.">
      <img src="../../img/hardware/usb-ttl-bad1.jpg" alt="Adaptador USB-TTL genérico no recomendado 1" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Genérico barato: no recomendado.">
      <img src="../../img/hardware/usb-ttl-bad2.jpg" alt="Adaptador USB-TTL genérico no recomendado 2" loading="lazy" decoding="async">
    </figure>
    <figure class="rack-gallery__slide" data-caption="Genérico barato: no recomendado.">
      <img src="../../img/hardware/usb-ttl-bad3.jpg" alt="Adaptador USB-TTL genérico no recomendado 3" loading="lazy" decoding="async">
    </figure>
    <div class="rack-gallery__overlay">
      <span class="rack-gallery__counter" data-rack-counter aria-live="polite"></span>
      <button type="button" class="rack-gallery__btn" data-rack-prev aria-label="Imagen anterior">&#8249;</button>
      <button type="button" class="rack-gallery__btn" data-rack-next aria-label="Imagen siguiente">&#8250;</button>
    </div>
  </div>
  <p class="rack-gallery__caption" data-rack-caption></p>
</div>

Para revisar **logs** cuando falla el boot en tests multi-nodo (libremesh-tests, `mesh_boot_node`), ver [Enfoque de tests LibreMesh](../tests/libremesh-testing-approach.md#mesh-boot-logs).

## Gateway del testbed (TP-Link TL-WDR3500)

Router **OpenWrt** en el trunk al switch: VLANs de DUTs, gateway `.254` por subred. Detalle en [gateway.md](gateway.md).

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--gateway-photo" markdown="block">

| Característica | Detalle |
|----------------|---------|
| Fabricante | TP-Link |
| SoC | Qualcomm Atheros **AR9344** (MIPS 74Kc) ~560 MHz |
| Arquitectura | MIPS |
| RAM | 128 MB |
| Flash | 8 MB NOR |
| Ethernet | 5× **100 Mbit/s** (1 WAN + 4 LAN, switch integrado AR934x) |
| Wi-Fi | Doble banda **N600**: 2,4 GHz 2×2 + 5 GHz 2×2 (802.11n) |
| PoE | No |
| USB | 1× USB 2.0 |
| OpenWrt | **ath79**; en el lab como gateway (p. ej. 24.x / 25.x). [TOH / techdata](https://openwrt.org/toh/hwdata/tp-link/tp-link_tl-wdr3500_v1) |

![TP-Link TL-WDR3500 (gateway del testbed)](../img/hardware/dut-tlwdr3500.jpg)

</div>

!!! note "Rol del TL-WDR3500 en el banco"
    Para estándares actuales el CPU y el Ethernet Fast Ethernet son limitantes; el equipo basta como **router VLAN/gateway** del banco, no como DUT de alto rendimiento.

*Aporte **INTI** (Instituto Nacional de Tecnología Industrial).*

## Dispositivos de prueba (DUTs)

Estado en rack, puertos del switch, VLANs y firmware: [duts-config.md](duts-config.md). Siguen fichas técnicas por modelo en uso; los datos pueden variar según revisión de placa. Referencia general: [OpenWrt Techdata](https://openwrt.org/toh/start).

### OpenWrt One

Placa **oficial de la comunidad OpenWrt** (hardware Banana Pi); doble flash NAND + NOR orientada a recuperación.

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--dut-board" markdown="block">

| Característica | Detalle |
|----------------|---------|
| Fabricante / diseño | Banana Pi (hardware) + **OpenWrt** (diseño oficial del proyecto) |
| SoC | MediaTek **MT7981B** (Filogic 820), dual-core Cortex-A53 @ 1,3 GHz |
| Arquitectura | ARM64 |
| RAM | 1 GB DDR4 |
| Almacenamiento | **256 MB** SPI NAND + **16 MB** SPI NOR (recuperación) |
| Expansión | **M.2** 2242/2230 **NVMe** (PCIe Gen2 x1) |
| Ethernet | 1× **2,5 GbE** (WAN) + 1× **1 GbE** (LAN) |
| Wi-Fi | Wi-Fi 6, chip **MT7976C**: 2,4 GHz **2×2** + 5 GHz **3×3** |
| PoE | **Sí** (802.3af/at en entrada WAN, según documentación del producto) |
| USB | 1× USB 2.0 tipo A + **USB-C** (alimentación / datos, según SKU) |
| Otras | RTC con pila, **mikroBUS**, antenas MMCX |
| OpenWrt | Soporte **oficial** (imágenes `mediatek/filogic`) |

![OpenWrt One](../img/hardware/dut-openwrt-one.jpg)

</div>

*Aporte **Banana Pi**.*

### Banana Pi BPI-R4

Router potente con **10G** y opción Wi-Fi 7 por módulos miniPCIe; usado en el lab como DUT de alto rendimiento.

<div class="catalog-hardware-row catalog-hardware-row--balanced catalog-hardware-row--dut-board" markdown="block">

| Característica | Detalle |
|----------------|---------|
| Fabricante | Banana Pi (Sinovoip) |
| SoC | MediaTek **MT7988A** (Filogic 880), quad-core Cortex-A73 @ 1,8 GHz |
| Arquitectura | ARM64 |
| RAM | **4 GB u 8 GB** DDR4 (según variante comercial) |
| Almacenamiento | **8 GB eMMC** + SPI-NAND (**128 MB o 256 MB**, según revisión) |
| Expansión | microSD + **M.2 NVMe** (KEY-M) + M.2 KEY-B (celular, según placa) |
| Ethernet | **4× 1 GbE** + **2× 10 GbE SFP+** (existen variantes combo RJ45/SFP según SKU) |
| Wi-Fi | Sin radio integrada en la placa base; **2× miniPCIe** (PCIe 3.0) para módulos (p. ej. Wi-Fi 7) |
| PoE | No integrado en la placa base |
| USB | 1× **USB 3.2** |
| OpenWrt | **Sí** (`mediatek/filogic`); en el lab como DUT con enlaces 10G |

![Banana Pi BPI-R4](../img/hardware/dut-bpi-r4.jpg)

</div>

*Aporte **Banana Pi**.*

### Libre Router (AlterMundi / LibreRouter.org)

Hardware abierto orientado a **redes comunitarias** y LibreMesh; en el lab con carcasa o placa según unidad.

<div class="catalog-hardware-row catalog-hardware-row--double-img" markdown="block">

| Característica | Detalle |
|----------------|---------|
| Fabricante / proyecto | **AlterMundi** / comunidad **LibreRouter** |
| SoC | Qualcomm Atheros **QCA9558** MIPS @ ~720 MHz |
| Arquitectura | MIPS |
| RAM | 128 MB DDR2 |
| Flash | 16 MB NOR |
| Ethernet | 2× **1 GbE** (switch QCA8337), **PoE** y **passthrough** según diseño |
| Wi-Fi | 2,4 GHz **2×2** integrado + hasta **2× miniPCIe** para radios 5 GHz (p. ej. 802.11an/ac) |
| USB | **2× USB 2.0** en PCB (pueden no quedar accesibles según carcasa) |
| Otras | Esquemas/Gerbers publicados, GPIO, watchdog |
| OpenWrt / LibreMesh | **Sí**; en el lab a menudo **LibreRouterOS** / LibreMesh derivado de OpenWrt |

<div class="catalog-hardware-row__stack">
<p><img src="../../img/hardware/dut-librerouter-case.png" alt="Libre Router (unidad en rack)" /></p>
<p><img src="../../img/hardware/dut-librerouter.jpg" alt="Libre Router (placa)" /></p>
</div>

</div>

*Aporte **AlterMundi** (proyecto LibreRouter).*

### Belkin RT3200 / Linksys E8450

Mismo hardware con marcas **Belkin** (RT3200) y **Linksys** (E8450). OpenWrt usa layout **UBI**.

<div class="catalog-hardware-row catalog-hardware-row--double-img" markdown="block">

| Característica | Detalle |
|----------------|---------|
| Fabricante comercial | **Belkin** (RT3200) / **Linksys** (E8450) |
| SoC | MediaTek **MT7622BV** (dual Cortex-A53) + **MT7915E** (Wi-Fi 6) |
| Arquitectura | ARM64 |
| RAM | 512 MB DDR3 |
| Flash | 128 MB SPI-NAND (layout **UBI** en OpenWrt) |
| Ethernet | 5× **1 GbE** (1 WAN + 4 LAN) |
| Wi-Fi | Doble banda **AX3200** (según especificación del fabricante) |
| PoE | No |
| USB | 1× USB 2.0 en el chasis |
| OpenWrt | Instalación y migración **UBI**: [TOH E8450 / RT3200](https://openwrt.org/toh/linksys/e8450) |

<div class="catalog-hardware-row__stack">
<p><img src="../../img/hardware/dut-belkinrt3200.png" alt="Belkin RT3200" /></p>
<p><img src="../../img/hardware/dut-linksyse8450.png" alt="Linksys E8450 (mismo hardware)" /></p>
</div>

</div>

*Aporte **INTI** (Instituto Nacional de Tecnología Industrial).*
