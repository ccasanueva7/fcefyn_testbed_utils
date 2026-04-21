# ZeroTier - admin remote access

!!! warning "Admin-only"
    ZeroTier is for **lab administrators** who need `sudo` on the host (Ansible, service management, switch/MikroTik consoles). Developers do **not** need ZeroTier: they reach the lab via the upstream coordinator as `ProxyJump` - see [developer-remote-access](developer-remote-access.md).

How to install ZeroTier on admin machines and reach the lab host as an unprivileged / personal user over VPN.

**Lab network:** `b103a835d2ead2b6` - [Join](https://joinzt.com/addnetwork?nwid=b103a835d2ead2b6&v=1).

See [host-config](../configuracion/host-config.md#8-ansible-integration) for the Ansible role on the orchestration host, and [gateway](../configuracion/gateway.md#57-zerotier-remote-access) for gateway router install.

---

## 1. Linux (Debian, Ubuntu, Fedora, etc.)

```bash
curl -fsSL https://install.zerotier.com | sudo bash

sudo systemctl start zerotier-one
sudo systemctl enable zerotier-one

sudo zerotier-cli join b103a835d2ead2b6

zerotier-cli listnetworks   # ACCESS_DENIED until authorized
```

If `zerotier-cli` shows "missing port and zerotier-one.port not found": the daemon is not running.

- **With systemd** (Debian, Ubuntu, Fedora): `sudo systemctl start zerotier-one`
- **Without systemd** (OpenWrt, etc.): `/etc/init.d/zerotier start`

Wait a few seconds before retrying `zerotier-cli`.

---

## 2. OpenWrt

```bash
opkg install zerotier
uci set zerotier.global.enabled='1'
uci commit zerotier
/etc/init.d/zerotier enable
/etc/init.d/zerotier start
```

**Network persistence** (after `reboot`, node rejoins lab NWID): on OpenWrt, `/etc/init.d/zerotier` only applies UCI sections of type **`network`** with **`option id '<16 hex>'`**. `zerotier-cli join` alone or sections with `list join` / `openwrt_network` are not enough if the init script does not read them. Full config, firewall, troubleshooting: **[gateway 5.7 - ZeroTier](../configuracion/gateway.md#57-zerotier-remote-access)** (TL-WDR3500 / lab gateway).

On OpenWrt 24.x with `apk`, the same UCI concepts apply; startup is still `/etc/init.d/zerotier`.

---

## 3. Authorization

A lab admin must authorize the node in [my.zerotier.com](https://my.zerotier.com) → network `b103a835d2ead2b6` → Members → check **Auth** for the new device. The device then gets a ZeroTier IP.

---

## 4. Connect to the host

Once authorized, SSH to the host using its ZeroTier IP (visible in ZeroTier Central or `zerotier-cli listnetworks` on the host):

```bash
ssh user@<HOST_ZEROTIER_IP>
```
