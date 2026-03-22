# Configuración del Switch

En el laboratorio el switch es un **TP-Link SG2016P** (16× Gigabit, 8× PoE). La **configuración de VLAN** se **aplica mediante scripts**, no como rutina manual en el CLI del equipo. Un switch distinto con **802.1Q** puede reutilizar el mismo esquema con otro driver en `scripts/switch/switch_drivers/`.

---

## 1. Contexto

El switch interconecta tres roles:

1. **Gateway** (OpenWrt; antes MikroTik): capa 3, rutas entre VLANs e internet. [gateway.md](./gateway.md).
2. **Host** (Lenovo T430): Labgrid, dnsmasq/TFTP, SSH a los DUTs.
3. **DUTs**: un router OpenWrt o LibreMesh por VLAN.

Gateway y host usan puertos **trunk** (802.1Q, tráfico etiquetado). Cada DUT va en **access** (tráfico untagged en su VLAN).

| Tipo   | Función | Tráfico |
|--------|---------|---------|
| **Access** | Un DUT por puerto | Untagged |
| **Trunk**  | Multi-VLAN | Tagged (802.1Q) |

En los trunk circulan varias VLAN; cada DUT tiene un puerto access dedicado.

---

## 2. Requisitos del Switch

- **802.1Q:** IDs numéricos (p. ej. 100+); cada puerto en modo access (untagged) o trunk (tagged).
- **PVID:** VLAN por defecto si el frame llega sin etiqueta (access = VLAN del DUT; trunk = 1).
- **Ingress checking** activo; **acceptable frame types:** Admit All.

---

## 3. Mapeo Puerto-Dispositivo (FCEFyN)

### 3.1 Tabla de asignación

| Puerto SG2016P | Dispositivo       | VLAN | Tipo   |
|----------------|-------------------|------|--------|
| 1              | OpenWrt One       | 104  | Access |
| 2              | LibreRouter #1    | 105  | Access (PoE + splitter 48V→12V) |
| 3              | LibreRouter #2    | 106  | Access |
| 4              | LibreRouter #3    | 107  | Access |
| 9              | Lenovo T430 (Server) | Trunk | Trunk |
| 10             | Router OpenWrt (Gateway) | Trunk | Trunk |
| 11             | Belkin RT3200 #1  | 100  | Access |
| 12             | Belkin RT3200 #2  | 101  | Access |
| 13             | Belkin RT3200 #3  | 102  | Access |
| 14             | Banana Pi R4      | 103  | Access |
| 15             | (disponible)      | -    | -      |
| 16             | OpenWrt One (LAN) | 104  | Access |

El puerto 16 conecta el **LAN** del OpenWrt One cuando la alimentación **PoE** está en el puerto 1; detalle en [duts-config, OpenWrt One](duts-config.md#openwrt-one). Los puertos 5-8 quedan sin asignar (VLAN 1 por defecto).

### 3.2 Nombres de VLAN Utilizados

| VLAN ID | Nombre en Switch   | Subred           |
|---------|--------------------|------------------|
| 100     | belkin_rt3200_1    | 192.168.100.0/24 |
| 101     | belkin_rt3200_2    | 192.168.101.0/24 |
| 102     | belkin_rt3200_3    | 192.168.102.0/24 |
| 103     | banana-pi-r4       | 192.168.103.0/24 |
| 104     | openwrt-one        | 192.168.104.0/24 |
| 105     | libre_router_1     | 192.168.105.0/24 |
| 106     | libre_router_2     | 192.168.106.0/24 |
| 107     | libre_router_3     | 192.168.107.0/24 |
| **200** | **mesh**           | 192.168.200.0/24 |

!!! note "Gateway e internet en los DUTs al cambiar de modo"
    Además de **aplicar el preset de VLAN en el switch**, `switch_vlan_preset.py` abre **SSH en paralelo** a cada DUT y ajusta gateway, rutas e interfaces según el preset. Pasos y tablas: [duts-config, Acceso a Internet (opkg)](duts-config.md#acceso-a-internet-opkg).

    - **isolated:** gateway por VLAN `192.168.XXX.254`.
    - **mesh:** gateway `192.168.200.254`.

    En ambos casos el script configura una **IP secundaria** en la subred del gateway (`192.168.{vlan}.x` o `192.168.200.x`, según `libremesh_fixed_ip`). Sin esa dirección el gateway del testbed no enruta correctamente el retorno (NAT / salida a internet). En ese mismo flujo **detiene el firewall** en el DUT.

---

## 4. Configuración Automatizada

La configuración de VLAN del testbed **no se realiza manualmente** en el switch; la aplican estas herramientas:

| Herramienta | Uso |
|-------------|-----|
| **testbed-mode.sh** | CLI de modo: `openwrt` (VLANs 100-108 isolated), `libremesh` (VLAN 200 mesh), `hybrid` (pool). |
| **switch_vlan_preset.py** | Presets `isolated` o `mesh` al switch por SSH; guarda `~/.config/labgrid-vlan-mode`. |
| **pool-manager.py** | Modo híbrido: lee `configs/pool-config.yaml`, VLANs mixtas en el switch, exporters. |

Operación diaria: [SOM 2](../operar/SOM.md#2-cambio-de-modo) y [SOM 5](../operar/SOM.md#5-pool-manager-modo-hibrido).

!!! note "Configuración manual (referencia)"
    Para recuperación o depuración: una VLAN de prueba por puerto access (untagged); puertos trunk con todas las VLANs en tagged; PVID e ingress como en §2 (Admit All).

---

## 5. TP-Link SG2016P: SSH y PoE

### 5.1 Acceso SSH/CLI

El switch acepta SSH para gestión por CLI. IP por defecto: `192.168.0.1`. El switch **no acepta autenticación por clave pública**; la sesión debe usar **contraseña**.

Ver [host-config 3.6](host-config.md#36-configuracion-ssh-para-acceso-manual-sshconfig) o plantilla `configs/templates/ssh_config_fcefyn`. 

Conexión: 

```bash
ssh switch-fcefyn
```

El prompt es `SG2016P>`.

!!! note "Cliente SSH y autenticación"
    El cliente intenta primero claves públicas; el switch rechaza y corta la sesión. Incluir `PreferredAuthentications password` y `PubkeyAuthentication no` en la configuración (plantilla citada arriba).

El **OpenWrt One** está en el puerto 1 (PoE). Para power-cycle por software:

**Manual (accediendo por SSH desde el host):**
```text
enable
configure
interface gigabitEthernet 1/0/1
power inline supply disable    # Apaga el OpenWrt One
# Esperar 5-10 segundos
power inline supply enable     # Enciende el OpenWrt One
end
```

**Automático (script):** Instalar vía Ansible (recomendado) o manualmente. El script requiere `switch_client.py` y `switch_drivers/` en el mismo directorio.

**Instalación con Ansible:**
```bash
# Desde fcefyn_testbed_utils
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags poe_switch -K
```

**Instalación manual:** Copiar `scripts/switch/poe_switch_control.py`, `switch_client.py` y `scripts/switch/switch_drivers/` a `/usr/local/bin/`. La configuración del switch va en `~/.config/poe_switch_control.conf`.

!!! warning "Credenciales (fuera del repositorio)"
    Ese archivo contiene la contraseña del switch: usar permisos restrictivos (`chmod 600`) y no versionarlo en git.

```bash
# Una sola vez: copiar plantilla y editar con la contraseña del switch
cp configs/templates/poe_switch_control.conf.example ~/.config/poe_switch_control.conf
chmod 600 ~/.config/poe_switch_control.conf
# Editar y poner POE_SWITCH_PASSWORD=contraseña_real

# Uso (desde cualquier directorio)
poe_switch_control.py on 1    # Encender puerto 1 (OpenWrt One)
poe_switch_control.py off 1   # Apagar
poe_switch_control.py cycle 1 # Power cycle (off, 5s, on)
poe_switch_control.py on 2    # Puerto 2 (Librerouter 1)
```

!!! note "Ejecución con sudo"
    Tanto `poe_switch_control.py` como `switch_vlan_preset.py` (usado por `testbed-mode.sh`) leen la configuración desde el home del usuario que invocó sudo (`SUDO_USER`). Si se ejecuta `sudo ./testbed-mode.sh libremesh`, la contraseña se toma de `/home/<usuario>/.config/poe_switch_control.conf`, no de `/root/.config/`.

!!! note "PoE y sesiones SSH concurrentes"
    PDUDaemon puede invocar varios `poe_switch_control.py` en paralelo (p. ej. varios DUTs PoE). El firmware del TP-Link **no tolera de forma fiable** varias sesiones SSH simultáneas (timeouts). El script serializa el acceso con un lock (`/tmp/poe_switch.lock`, `fcntl.flock`); las llamadas en background se ejecutan en cola.

!!! note "Integración con PDUDaemon"
    Un PDU por puerto (`fcefyn-poe-port1`, `fcefyn-poe-port2`) permite ciclos paralelos desde el coordinator. Ver [host-config 5.2](host-config.md#52-pdudaemon-etcpdudaemonpdudaemonconf). Si PDUDaemon se instaló con Ansible (DynamicUser), hace falta un override de systemd con `POE_SWITCH_PASSWORD`; ver [host-config 5.2.1](host-config.md#521-pdu-poe-contrasena-con-dynamicuser).

### 5.2 OpenWrt One: dos cables (PoE + LAN para U-Boot TFTP)

!!! note "Timeout de PHY en WAN y segundo enlace (LAN)"
    Con PoE en el puerto 1, U-Boot en el WAN (EN8811H) puede incurrir en timeout de PHY. Se cablean **dos enlaces:** WAN (PoE) al puerto 1; LAN al puerto 16. El puerto 16 se configura en VLAN 104 (untagged, PVID 104) para que DHCP/TFTP alcancen el host. Más detalle en [duts-config, OpenWrt One](duts-config.md#openwrt-one).

!!! note "LibreRouter 1 (puerto 2) y PoE"
    Usa PoE vía splitter 48V→12V. El LibreRouter requiere PoE pasivo; el switch entrega PoE activo (802.3af/at). Un inyector/splitter genérico (ej. POE-48V-12W Gigabit) convierte 48V→12V. Hay que habilitar PoE en el puerto 2 del switch para alimentar el splitter.

---

## 6. Integración con Labgrid

### 6.1 Coherencia con exporter

El mapeo VLAN ↔ DUT debe coincidir con el archivo `exporter.yaml` de Labgrid:

```yaml
labgrid-fcefyn-belkin_rt3200_1:
  NetworkService:
    address: "192.168.1.1%vlan100"   # VLAN 100 = puerto 11
    username: "root"

labgrid-fcefyn-openwrt_one:
  NetworkService:
    address: "192.168.1.1%vlan104"   # VLAN 104 = puerto 1
    username: "root"
```

El `%vlanXXX` en `address` debe coincidir con el **VLAN ID** del puerto del DUT en el switch; el tráfico etiquetado llega a esa interfaz en el servidor.

### 6.2 Flujo de Tráfico

1. El servidor envía un paquete hacia `192.168.1.1` con origen en `192.168.1.100` (interfaz `vlan100`).
2. El frame sale etiquetado con VLAN 100 hacia el switch (puerto 9).
3. El switch reenvía el frame por el puerto 11 (access de VLAN 100) sin etiqueta hacia el Belkin.
4. El Belkin responde; el switch reetiqueta el tráfico y lo envía al puerto 9 (servidor) o 10 (gateway) según corresponda.

---

## 7. Soporte para Otros Switches

Mismo modelo lógico 802.1Q; hace falta un driver que emita los comandos del CLI del fabricante.

1. Crear `scripts/switch/switch_drivers/<nombre>.py` según [DRIVER_INTERFACE.md](../../scripts/switch/switch_drivers/DRIVER_INTERFACE.md).
2. En `~/.config/poe_switch_control.conf`: `POE_SWITCH_DRIVER=<nombre>` y `POE_SWITCH_DEVICE_TYPE=<netmiko_type>`.

Implementar `PRESETS`, `build_preset_commands()`, `build_poe_commands()`, `build_hybrid_commands()`. Referencia: `tplink_jetstream.py`.
