# ZeroTier - Instalación para acceso al lab

Instrucciones para instalar ZeroTier en dispositivos externos (laptops de administradores, profesores, etc.) y conectarse al host del lab vía VPN.

**Red del lab:** `b103a835d2ead2b6` - [Unirse](https://joinzt.com/addnetwork?nwid=b103a835d2ead2b6&v=1).

Ver [host-config](../configuracion/host-config.md#8-integracion-con-ansible) para el role Ansible que instala ZeroTier en el host orquestador, y [gateway](../configuracion/gateway.md#57-zerotier-acceso-remoto) para la instalación en el router gateway.

---

## 1. Linux (Debian, Ubuntu, Fedora, etc.)

```bash
curl -fsSL https://install.zerotier.com | sudo bash

sudo systemctl start zerotier-one
sudo systemctl enable zerotier-one

sudo zerotier-cli join b103a835d2ead2b6

zerotier-cli listnetworks   # ACCESS_DENIED hasta autorización
```

Si `zerotier-cli` da "missing port and zerotier-one.port not found": el daemon no está corriendo.

- **Con systemd** (Debian, Ubuntu, Fedora): `sudo systemctl start zerotier-one`
- **Sin systemd** (OpenWrt, etc.): `/etc/init.d/zerotier start`

Esperar unos segundos antes de reintentar `zerotier-cli`.

---

## 2. OpenWrt

```bash
opkg install zerotier
uci set zerotier.global.enabled='1'
uci commit zerotier
/etc/init.d/zerotier enable
/etc/init.d/zerotier start
```

**Persistencia de la red** (que tras un `reboot` el nodo vuelva a unirse al NWID del lab): en el paquete OpenWrt, `/etc/init.d/zerotier` solo aplica secciones UCI con tipo **`network`** y **`option id '<16 hex>'`**. No basta `zerotier-cli join` ni secciones con `list join` / `openwrt_network` si el init no las lee. Configuración completa, firewall y tabla de averías: **[gateway 5.7 - ZeroTier](../configuracion/gateway.md#57-zerotier-acceso-remoto)** (router TL-WDR3500 / gateway del lab).

En OpenWrt 24.x con `apk`, los mismos conceptos UCI aplican; el arranque sigue siendo `/etc/init.d/zerotier`.

---

## 3. Autorización

Un administrador del lab debe autorizar el nodo en [my.zerotier.com](https://my.zerotier.com) → red `b103a835d2ead2b6` → Members → marcar **Auth** para el dispositivo nuevo. Tras eso el dispositivo recibe una IP en la red ZeroTier.

---

## 4. Conectarse al host

Una vez autorizado, SSH al host usando la IP ZeroTier del host (visible en ZeroTier Central o con `zerotier-cli listnetworks` desde el host):

```bash
ssh usuario@<IP_ZEROTIER_DEL_HOST>
```
