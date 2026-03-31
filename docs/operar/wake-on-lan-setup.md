# Wake-on-LAN - Lenovo ThinkPad T430 (orchestration host)

Wake-on-LAN setup to power on the Lenovo T430 orchestration host remotely when it is off. WoL lets testbed admins power the lab from outside without physical access.

**Context:** A powered-off host does not receive ZeroTier traffic. The WoL packet must be sent from an always-on device on the same LAN (the OpenWrt gateway router, which runs ZeroTier). See [gateway 5.8](../configuracion/gateway.md#58-wake-on-lan-remote-host-power-on) for the full remote flow.

---

## 1. Prerequisites

- Active Ethernet interface (on the T430 host: `enp0s25`).
- Ethernet cable to switch/gateway (same VLAN/LAN as the Lenovo).

---

## 2. BIOS - Enable Wake-on-LAN

BIOS must allow WoL. On ThinkPad T430:

### 2.1 Enter BIOS

1. Reboot the laptop.
2. When the ThinkPad logo appears, press **F1**.
3. **BIOS Setup Utility** opens.

### 2.2 Enable Wake-on-LAN

Navigate to: `Config > Network > Wake On Lan`

Set `Wake on LAN = AC Only` (AC power only).

Save and exit.

---

## 3. Linux - ethtool (after boot)

After Ubuntu boots, enable WoL on the Ethernet interface.

### 3.1 Check interface and state

```bash
ip link show
# Identify Ethernet (on T430: enp0s25)

sudo ethtool enp0s25
```

In the output, find `Wake-on:`. If it shows `d` (disabled), enable it.

### 3.2 Enable WoL

```bash
sudo ethtool -s enp0s25 wol g
```

`g` = magic packet (standard WoL). After this, `ethtool enp0s25` should show `Wake-on: g`.

### 3.3 Behavior after reboot

!!! warning "WoL persistence"
    Without extra configuration, the setting is lost on reboot. Use the systemd persistence service (section 4) or the Ansible role (section 5).

---

## 4. Persistence - systemd service (manual)

To keep WoL enabled after each boot, use a systemd unit that runs `ethtool` at startup.

### 4.1 Create the service

```bash
sudo nano /etc/systemd/system/wol.service
```

Content (adjust `enp0s25` if the Ethernet name differs):

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

!!! note "Order vs NetworkManager"
    The service must run **after** NetworkManager. With `After=network.target`, NM may reset `Wake-on` to `d` after the service sets `g`. `ExecStartPre=sleep 5` gives NM time to finish.

### 4.2 Enable the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable wol
sudo systemctl start wol
```

On each reboot, the service enables WoL automatically.

### 4.3 Verification

```bash
sudo systemctl status wol
sudo ethtool enp0s25
# Should show Wake-on: g
```

---

## 5. Automation with Ansible

The Ansible `wol` role creates and enables the systemd service idempotently. See [host-config 8.4](../configuracion/host-config.md#84-wake-on-lan-persistence).

Run:

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags wol -K
```

---

## 6. Get the host MAC

To send the magic packet from the gateway (or another LAN host), you need the Lenovo MAC.

```bash
ip link show enp0s25
# Find "link/ether XX:XX:XX:XX:XX:XX"
```

Or:

```bash
cat /sys/class/net/enp0s25/address
```

Store that MAC (e.g. as `LABGRID_HOST_MAC` in gateway docs) for `wakeonlan` or equivalents.

---

## 7. Send WoL (from gateway or LAN)

The magic packet must come from a device on the same subnet as the Lenovo (or broadcast). The gateway router (always on) is the natural sender when accessing remotely via ZeroTier.

### 7.1 OpenWrt (current setup: TL-WDR3500)

Testbed gateway is OpenWrt with `etherwake` installed and ZeroTier for remote access. Send WoL on a testbed VLAN:

```bash
ssh root@<ZeroTier-IP-of-router> 'etherwake -i eth0.100 00:21:cc:c4:25:3b'
```

See [gateway 5.8](../configuracion/gateway.md#58-wake-on-lan-remote-host-power-on) for full router configuration.

### 7.2 MikroTik (deprecated - previous setup)

If a MikroTik were used again as testbed gateway:

```routeros
/tool wol mac=00:21:CC:C4:25:3B interface=LAB-TRUNK
```

### 7.3 Via ZeroTier (full flow)

1. SSH to OpenWrt router via ZeroTier: `ssh root@10.246.3.95`
2. Send WoL: `etherwake -i eth0.100 00:21:cc:c4:25:3b`
3. Wait ~2 min for the Lenovo to boot.
4. SSH to host via ZeroTier: `ssh laryc@10.246.3.118`
