# Wake-on-LAN - Lenovo ThinkPad T430 (Host de Orquestación)

Configuración de Wake-on-LAN para encender remotamente el host Lenovo T430 cuando está apagado. El WoL permite a los sysadmin de la testbed encender el lab desde fuera sin acceso físico.

**Contexto:** El host apagado no recibe tráfico ZeroTier. El paquete WoL debe enviarse desde un dispositivo siempre encendido en la misma LAN (el gateway router OpenWrt, que tiene ZeroTier). Ver [gateway 5.8](../configuracion/gateway.md#58-wake-on-lan-encendido-remoto-del-host) para el flujo remoto completo.

---

## 1. Requisitos previos

- Interfaz Ethernet activa (en el host T430: `enp0s25`).
- Cable Ethernet conectado al switch/gateway (misma VLAN/LAN que el Lenovo).

---

## 2. BIOS - Habilitar Wake-on-LAN

La BIOS debe permitir WoL. En ThinkPad T430:

### 2.1 Entrar a la BIOS

1. Reiniciar la laptop.
2. Cuando aparezca el logo ThinkPad, presionar **F1**.
3. Se abre el **BIOS Setup Utility**.

### 2.2 Activar Wake-on-LAN

Navegar a: `Config > Network > Wake On Lan`

Configurar `Wake on LAN = AC Only` (solo con alimentación conectada).

Guardar cambios y salir.

---

## 3. Linux - ethtool (una vez arrancado)

Tras arrancar Ubuntu, habilitar WoL en la interfaz Ethernet.

### 3.1 Verificar interfaz y estado actual

```bash
ip link show
# Identificar la interfaz Ethernet (en la T430: enp0s25)

sudo ethtool enp0s25
```

En la salida, buscar `Wake-on:`. Si aparece `d` (disabled), hay que habilitarlo.

### 3.2 Habilitar WoL

```bash
sudo ethtool -s enp0s25 wol g
```

`g` = magic packet (WoL estándar). Tras este comando, `ethtool enp0s25` debería mostrar `Wake-on: g`.

### 3.3 Comportamiento tras reinicio

**Importante:** Sin configuración adicional, el setting se pierde al reiniciar. Por eso se usa el servicio systemd de persistencia (sección 4) o el rol Ansible (sección 5).

---

## 4. Persistencia - Servicio systemd (manual)

Para que WoL siga habilitado tras cada reinicio, se usa un unit systemd que ejecuta `ethtool` al arrancar.

### 4.1 Crear el servicio

```bash
sudo nano /etc/systemd/system/wol.service
```

Contenido (adaptar `enp0s25` si la interfaz Ethernet tiene otro nombre):

```ini
[Unit]
Description=Enable Wake On LAN
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 5
ExecStart=/usr/sbin/ethtool -s enp0s25 wol g
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

> **Nota:** El servicio debe correr **después** de NetworkManager. Si se usa
> `After=network.target`, NM puede resetear `Wake-on` a `d` al configurar la
> interfaz después de que el servicio ya la puso en `g`. El `ExecStartPre=sleep 5`
> da margen para que NM termine.

### 4.2 Habilitar el servicio

```bash
sudo systemctl daemon-reload
sudo systemctl enable wol
sudo systemctl start wol
```

A partir de cada reinicio, el servicio habilitará WoL automáticamente.

### 4.3 Verificación

```bash
sudo systemctl status wol
sudo ethtool enp0s25
# Debe mostrar Wake-on: g
```

---

## 5. Automatización con Ansible

El rol Ansible `wol` crea y habilita el servicio systemd de forma idempotente. Ver [host-config 8.4](../configuracion/host-config.md#84-wake-on-lan-persistencia).

Ejecutar:

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags wol -K
```

---

## 6. Obtener la MAC del host

Para enviar el magic packet desde el gateway (o desde otro equipo en la LAN), se necesita la dirección MAC del Lenovo.

```bash
ip link show enp0s25
# Buscar "link/ether XX:XX:XX:XX:XX:XX"
```

Alternativamente:

```bash
cat /sys/class/net/enp0s25/address
```

Guardar esa MAC (p. ej. como `LABGRID_HOST_MAC` en la documentación del gateway) para que quien ejecute `wakeonlan` o equivalentes use la dirección correcta.

---

## 7. Enviar WoL (desde el gateway o la LAN)

El magic packet debe enviarse desde un dispositivo en la misma subred que el Lenovo (o en broadcast). El gateway router (siempre encendido) es el candidato natural para enviar WoL cuando se accede remotamente vía ZeroTier.

### 7.1 OpenWrt (setup actual: TL-WDR3500)

El gateway del testbed es un router OpenWrt con `etherwake` instalado
y ZeroTier para acceso remoto. Enviar WoL por una VLAN del testbed:

```bash
ssh root@<IP-ZeroTier-del-router> 'etherwake -i eth0.100 00:21:cc:c4:25:3b'
```

Ver [gateway 5.8](../configuracion/gateway.md#58-wake-on-lan-encendido-remoto-del-host)
para la configuración completa del router.

### 7.2 MikroTik (deprecado - setup anterior)

Si se volviera a usar un MikroTik como gateway del testbed:

```routeros
/tool wol mac=00:21:CC:C4:25:3B interface=LAB-TRUNK
```

### 7.3 Desde ZeroTier (flujo completo)

1. SSH al router OpenWrt vía ZeroTier: `ssh root@10.246.3.95`
2. Enviar WoL: `etherwake -i eth0.100 00:21:cc:c4:25:3b`
3. Esperar ~2min a que el Lenovo arranque.
4. SSH al host vía ZeroTier: `ssh laryc@10.246.3.118`
