# Orchestration host configuration - FCEFyN lab

Configuration of the host (Lenovo T430, Ubuntu) as the HIL orchestration server.

**Related:** [switch-config](switch-config.md) · [duts-config](duts-config.md) · [gateway](gateway.md) · [arduino-relay](arduino-relay.md) · [ci-runner](ci-runner.md)

---

## Summary

| Component | File | Role |
|-----------|------|------|
| **Netplan** | `/etc/netplan/labnet.yaml` | VLANs 100-108 (OpenWrt) + vlan200 (LibreMesh). `link:` = physical interface (`ip link show`). |
| **dnsmasq** | `/etc/dnsmasq.conf` | DHCP and TFTP per VLAN. Without it, DUTs do not get IP or network flash. |
| **PDUDaemon** | `/etc/pdudaemon/pdudaemon.conf` | Power cycle via Arduino relay or PoE. PoE needs override with switch password (5.2.1). |
| **Labgrid** | `/etc/labgrid/exporter.yaml` | Single exporter; global coordinator (datacenter VM, via WireGuard) manages reservations. |
| **SSH to DUTs** | `labgrid-bound-connect vlanNNN 192.168.1.1 22` | Connects to DUT on its isolated VLAN. See [SSH access to DUTs](../operar/dut-ssh-access.md). |
| **udev** | `/etc/udev/rules.d/99-serial-devices.rules` | Per-DUT serial symlinks (`/dev/belkin-rt3200-1`, etc.). |
| **TFTP** | `/srv/tftp/<place>/` | Firmware per place. See [tftp-server](tftp-server.md). |
| **TFTP cleanup** | Ansible role `tftp_cleanup` + `tftp-cleanup.timer` | Daily prune of broken TFTP symlinks and orphan `/var/cache/labgrid/` entries older than 30 days. See [tftp-server §7.1](tftp-server.md#71-automated-cleanup-tftp-cleanuptimer). |
| **ZeroTier** | Ansible role `zerotier` | Admin-only remote access to host via VPN. See [8.3](#83-remote-access-zerotier-for-admins-proxyjump-for-developers). |
| **WireGuard** | Ansible role `wireguard` | Tunnel to openwrt-tests global coordinator (upstream SSH jump host for developers and CI). See [8.3.1](#831-wireguard-global-coordinator). |
| **Wake-on-LAN** | BIOS + ethtool + `wol.service` | Power on the host from off over LAN. See [wake-on-lan-setup](../operar/wake-on-lan-setup.md). |
| **CI Runner** | `~/actions-runner/` | GitHub Actions self-hosted runner. See [ci-runner](ci-runner.md). |

**Key commands:** `netplan apply` · `systemctl restart dnsmasq labgrid-exporter` · `labgrid-client places`

**Ops:** [SOM](../operar/system-operation-manual.md) · [Routine operations](../operar/lab-routine-operations.md)

---

## 1. Context {: #1-context }

The host (Lenovo T430) centralizes tests and hardware access using:

- **Labgrid Exporter** - Publishes all DUTs to the global coordinator (datacenter VM, via WireGuard). See [Lab architecture](../diseno/lab-architecture.md).
- **dnsmasq** - DHCP and TFTP server on each VLAN. Used to load images on DUTs during boot (recovery) and for WAN to obtain IP.
- **PDUDaemon** - Power cycle: Arduino relays (barrel jack) or `poe_switch_control.py` (PoE).
- **SSH to DUTs** - `labgrid-bound-connect` connects to 192.168.1.1 on the correct VLAN.

Each DUT lives isolated on a VLAN. The host needs **one interface per VLAN** so Labgrid can SSH during tests. In openwrt-tests, `ansible/files/exporter/labgrid-fcefyn/exporter.yaml`:

```yaml
NetworkService:
  address: "192.168.1.1%vlan104"
  username: "root"
```

The `%vlan104` suffix means traffic must leave via that interface. Without it, DUTs cannot be distinguished because they all use 192.168.1.1 by default. VLAN context: [gateway §1](gateway.md#1-context). How Labgrid fits with the router (no Labgrid on OpenWrt): [gateway §4](gateway.md#4-labgrid-and-host).

---

## 2. Network configuration: Netplan with NetworkManager {: #2-network-configuration-netplan-with-networkmanager }

### 2.1 Netplan

**netplan** is used instead of imperative `nmcli` because:

- **Ansible compatibility:** openwrt-tests playbook deploys netplan via `template`. See [playbook_labgrid.yml](https://github.com/aparcar/openwrt-tests/blob/main/ansible/playbook_labgrid.yml).
- **Declarative config:** One YAML file defines desired state; idempotent and versionable.
- **Repo integration:** `ansible/files/exporter/labgrid-fcefyn/netplan.yaml` can hold this to reproduce the lab.

### 2.2 Renderer: NetworkManager

On desktop Ubuntu, **NetworkManager** usually owns the stack. Netplan should use `renderer: NetworkManager` so VLANs apply correctly. With `renderer: networkd` you may see `Unit dbus-org.freedesktop.network1.service not found` if networkd is not active.

### 2.3 Applied configuration (FCEFyN lab)

File: `/etc/netplan/labnet.yaml`. Source in repo: `ansible/files/exporter/labgrid-fcefyn/netplan.yaml`.

Structure (two VLANs shown; full file defines vlan100-vlan108):

```yaml
network:
  version: 2
  renderer: NetworkManager
  ethernets:
    enp0s25:
      dhcp4: true
  vlans:
    vlan100:
      id: 100
      link: enp0s25
      addresses:
        - 192.168.100.1/24
        - 192.168.1.100/24
    vlan101:
      id: 101
      link: enp0s25
      addresses:
        - 192.168.101.1/24
        - 192.168.1.101/24
    # ... vlan102 through vlan108 follow the same pattern
```

!!! note "Physical interface name"
    `enp0s25` is the host Ethernet interface name (`ip link show`).

### 2.3.1 Directory `/etc/netplan/`

Netplan reads all `.yaml` under `/etc/netplan/`. On the lab host you typically see:

| File | Source | Edit? |
|------|--------|-------|
| `labnet.yaml` | openwrt-tests Ansible (`ansible/files/exporter/.../netplan.yaml` deployed as this filename) | Yes; playbook deploys it |
| `90-NM-*.yaml` | NetworkManager | No; generated by NM when applying config |

`90-NM-*.yaml` match connections shown in Ubuntu GUI. NetworkManager generates them; do not edit by hand. To change networking: update the netplan source under **openwrt-tests** `ansible/files/exporter/labgrid-fcefyn/` and rerun the playbook, or edit `/etc/netplan/labnet.yaml` and run `netplan apply`.

### 2.4 Addressing: two IPs per VLAN {: #24-addressing-two-ips-per-vlan }

Each VLAN interface has **two addresses** because the host participates in two subnets with different roles: provisioning (boot) and SSH access (after OpenWrt is up).

| Host IP | Subnet | Use |
|---------|--------|-----|
| `192.168.X.1/24` | 192.168.X.0/24 | Host as **DHCP** and **TFTP** for that VLAN. DUT gets an IP here (e.g. 192.168.100.150) during boot. |
| `192.168.1.X/24` | 192.168.1.0/24 | Host on same subnet as DUT. Enables **SSH** to DUT at **192.168.1.1** (default OpenWrt LAN IP). |

**Flow:**

1. **Provisioning (boot):** DUT boots, requests DHCP. Host (192.168.X.1) answers with dnsmasq and serves TFTP if needed. DUT gets 192.168.X.x (e.g. 192.168.100.150).
2. **SSH (DUT running):** OpenWrt has 192.168.1.1 on LAN. Host must be on 192.168.1.0/24 to reach the DUT; hence 192.168.1.X (e.g. 192.168.1.100 on vlan100).

**Isolation:** Each DUT is on its own VLAN (separate broadcast domain), so all can use 192.168.1.1 without conflict. The two host IPs allow both phases on the same VLAN interface.

---

## 3. SSH to DUTs {: #3-ssh-to-duts }

### 3.1 Components

| Component | Role |
|-----------|------|
| **labgrid-bound-connect** | TCP (SSH) connections *bound* to a VLAN interface. Uses `socat` with `so-bindtodevice`. |

Each DUT SSH alias uses a static `ProxyCommand` bound to the DUT's isolated VLAN (e.g. `labgrid-bound-connect vlan100 192.168.1.1 22`). Tests that need mesh VLAN 200 use their own SSH path internally; `conftest_vlan.py` always restores ports to isolated after teardown. For manual mesh access on the host: `sudo labgrid-bound-connect vlan200 <mesh_ssh_ip> 22`. From a developer machine the bound-connect must run on the host via nested `ProxyCommand`; see [SSH access to DUTs - Remote developer](../operar/dut-ssh-access.md#remote-developer-lg_proxy).

### 3.2 Dynamic VLAN per test (labgrid-switch-abstraction / switch-vlan)

There is no global testbed "mode". All DUTs start on their **isolated VLAN** (100-108) by default, which matches openwrt-tests without changes. When a libremesh-tests test needs VLAN 200 (mesh), it changes at setup and restores at teardown via the `switch-vlan` CLI from [labgrid-switch-abstraction](https://github.com/fcefyn-testbed/labgrid-switch-abstraction); when `LG_PROXY` is set the test runs the command on the lab host via SSH (no local switch credentials needed). Manual debugging on the host:

```bash
switch-vlan belkin_rt3200_1 200       # move to mesh
switch-vlan belkin_rt3200_1 --restore  # restore isolated
```

Labgrid locking ensures mutual exclusion per DUT. See [Lab architecture](../diseno/lab-architecture.md).

### 3.3 Installation

`labgrid-bound-connect` is installed by `playbook_labgrid.yml` ([aparcar/openwrt-tests](https://github.com/aparcar/openwrt-tests)).

Manual install (without Ansible):

```bash
HELPERS=$(python3 -c "import labgrid; print(labgrid.__path__[0])")/../../share/labgrid/helpers
sudo cp $HELPERS/labgrid-bound-connect /usr/local/sbin/
sudo chmod +x /usr/local/sbin/labgrid-bound-connect
```

### 3.4 Sudoers

```bash
echo "$USER ALL=(ALL) NOPASSWD: /usr/local/sbin/labgrid-bound-connect" | sudo tee -a /etc/sudoers.d/labgrid
sudo chmod 440 /etc/sudoers.d/labgrid
```

### 3.5 SSH config for manual access (~/.ssh/config) {: #36-ssh-config-for-manual-access-sshconfig }

Each DUT alias uses a static `ProxyCommand` bound to the DUT's isolated VLAN via `labgrid-bound-connect`.

!!! warning "SSH config: do not set HostName to DUT IP"
    Do not set `HostName`; if you use `HostName 192.168.1.1`, SSH stores the key under that IP and all DUTs share one entry, causing "Host key verification failed" when switching VLANs.

Template file: `fcefyn-testbed-utils/configs/templates/ssh_config_fcefyn` (copy to `~/.ssh/config`).

```
Host dut-belkin-1
    User root
    ProxyCommand sudo labgrid-bound-connect vlan100 192.168.1.1 22

Host dut-belkin-2
    User root
    ProxyCommand sudo labgrid-bound-connect vlan101 192.168.1.1 22

# ... (see ssh_config_fcefyn for full list)

Host dut-librerouter-1
    User root
    ProxyCommand sudo labgrid-bound-connect vlan105 192.168.1.1 22

# Switch TP-Link SG2016P
Host switch-fcefyn
    HostName 192.168.0.1
    User admin
    PreferredAuthentications password
    PubkeyAuthentication no
```

Usage:

```bash
ssh dut-bananapi
ssh dut-librerouter-1
ssh switch-fcefyn   # needs management password
```

**Mesh SSH/control IP:** For mesh VLAN debugging and multi-node orchestration, each DUT keeps a stable secondary IP in `10.13.200.x` on `br-lan`. Once per DUT after flash: `provision_mesh_ip.py --device /dev/<symlink>` or `--all` (via serial). This IP is for unique host-side SSH/control access on VLAN 200; the real LibreMesh address used inside the mesh is still the node's dynamic `10.13.x.x` address. The script also adds a route to `10.13.0.0/16`. See [SSH access to DUTs](../operar/dut-ssh-access.md) for the per-DUT table and manual access.

**First connection:** If a previous 192.168.1.1 entry exists in `known_hosts`, remove it once:

```bash
ssh-keygen -f ~/.ssh/known_hosts -R 192.168.1.1
```

### 3.6 Lab identity key (fcefyn-lab)

Since [commit 2f1aed1](https://github.com/aparcar/openwrt-tests/commit/2f1aed1) upstream `labnet.yaml` no longer stores SSH keys inline. Instead, each lab entry has `maintainers:` (for healthcheck notifications) and `access:` (for SSH access), both listing GitHub usernames. The Ansible playbook fetches public keys from `https://github.com/<username>.keys` at deploy time and adds them to `~labgrid-dev/.ssh/authorized_keys`.

**Where it is set:**

- **labnet.yaml** (openwrt-tests): `labs.labgrid-fcefyn.access` lists `francoriba` and `aparcar`. Ansible fetches their GitHub SSH keys and deploys them to `/home/labgrid-dev/.ssh/authorized_keys`.
- **Lenovo (host):** The developer uses the SSH key registered on their GitHub account. No separate machine key is needed.

**Requirement:** Each user listed in `access:` must have at least one SSH public key on their GitHub profile (**Settings > SSH and GPG keys**). Key rotation on GitHub takes effect on the next Ansible run.

**Local testing:** TFTP dirs belong to `labgrid-dev`. For Labgrid to create symlinks when running tests, connect to the host as `labgrid-dev` (see [Running tests locally - labgrid-dev and TFTP](../operar/lab-running-tests.md#labgrid-dev-and-tftp)).

### 3.7 LuCI (web) access via SSH tunnel

DUTs share `192.168.1.1` on different VLANs. The browser cannot pick an interface, so direct LuCI access may fail if the kernel routes via another VLAN. Use an **SSH tunnel** forwarding local HTTP to the DUT using the correct SSH path (`~/.ssh/config` applies ProxyCommand and VLAN):

```bash
ssh -L 8888:localhost:80 dut-belkin-1 -N
```

**What it does:** `-L 8888:localhost:80` tunnels connections to local `localhost:8888` to port 80 on the DUT. Remote `localhost` is the router (LuCI). `-N` keeps the session open without a remote command, only the tunnel.

**Use:** With the command running, open **http://localhost:8888** in the browser. Stop tunnel: Ctrl+C.

**Per DUT:** Change alias (`dut-bananapi`, `dut-openwrt-one`, etc.). Use another local port for multiple tunnels: `-L 8889:localhost:80 dut-belkin-2 -N` for a second Belkin.

---

## 4. Verification

### 4.1 VLAN interfaces

```bash
ip link show | grep vlan
```

Should list vlan100 through vlan108.

### 4.2 Testbed gateway (OpenWrt) connectivity

Each VLAN has its gateway at `.254` on the OpenWrt router on the trunk to the switch (not the personal uplink MikroTik). Check reachability:

```bash
ping -I vlan100 -c2 192.168.100.254
ping -I vlan104 -c2 192.168.104.254
```

### 4.3 DUT connectivity

```bash
nmap -e vlan104 -sn 192.168.1.0/24

# SSH (after 192.168.1.1 responds)
ssh -o ProxyCommand="sudo labgrid-bound-connect vlan104 192.168.1.1 22" root@192.168.1.1
```

---

## 5. Power control and mapping

### 5.1 Power cycle

| Type | DUTs | Command |
|------|------|---------|
| **Arduino relays** | Belkin, Banana Pi, Librerouter 1-3, GL.iNet | `arduino_relay_control.py on/off N` (N = channel 0-10, 0-based) |
| **PoE (switch)** | OpenWRT One | `poe_switch_control.py on/off 1` |

**Arduino:** 11 channels (0-7 DUTs; 8-10 infra: unloaded channel, cooler, PSU). The **network switch** is not powered from Arduino. Detail: [arduino-relay](arduino-relay.md). Photos / specs: [hardware catalog](catalogo-hardware.md).

**PoE:** [switch-config section 5.1](switch-config.md#51-ssh-and-cli-access). Config: `~/.config/switch.conf`.

### 5.2 PDUDaemon (`/etc/pdudaemon/pdudaemon.conf`)

**PDU** (Power Distribution Unit) = power distribution. This lab does not use physical PDUs; PDUDaemon drives scripts (Arduino, PoE switch) that act as software PDUs to power DUTs remotely.

PDUDaemon exposes an HTTP API so Labgrid controls DUT power. The file defines PDUs and commands.

**Source:** Ansible (openwrt-tests) deploys from `ansible/files/exporter/labgrid-fcefyn/pdudaemon.conf`. If the lab is Ansible-managed, edit in repo and rerun the playbook.

**Minimum FCEFyN config:**

| PDU | Driver | Use |
|-----|--------|-----|
| `fcefyn-arduino` | localcmdline | Arduino relays (Belkin, Banana Pi, Librerouter 1-3) |
| `fcefyn-poe` | localcmdline | PoE via TP-Link: Labgrid passes **index** `1` (OpenWRT One). (`poe_switch_control.py on/off <index>`) |

`localcmdline` runs `cmd_on`/`cmd_off` substituting `%s` with the index from Labgrid. **Arduino relays:** 0-based channels (Belkin 1→0, Belkin 2→1, Belkin 3→2, Banana Pi→3, Librerouter 1→4). **PoE:** a single PDU entry routes PoE power cycles through `poe_switch_control.py`; **index** selects the switch port (currently only OpenWRT One on index 1). See [switch-config 5.1](switch-config.md#51-ssh-and-cli-access) and [Lab architecture](../diseno/lab-architecture.md). Switch password comes from `~/.config/switch.conf` or `/etc/switch.conf`. If PDUDaemon runs with `DynamicUser=yes` (Ansible default), use `SWITCH_PASSWORD` in a systemd override.

**Full example:** `ansible/files/exporter/labgrid-fcefyn/pdudaemon.conf` in [aparcar/openwrt-tests](https://github.com/aparcar/openwrt-tests).

#### 5.2.1 PoE PDU: password with DynamicUser {: #521-poe-pdu-password-with-dynamicuser }

`poe_switch_control.py` reads password from `~/.config/switch.conf` when run manually. Labgrid does not run it; PDUDaemon does. If PDUDaemon uses `DynamicUser=yes` (Ansible), it runs as a dynamic user with `ProtectHome=true` and cannot read `~/.config/`. Fix: pass password via environment in a systemd override:

```bash
sudo mkdir -p /etc/systemd/system/pdudaemon.service.d
sudo tee /etc/systemd/system/pdudaemon.service.d/switch-password.conf << 'EOF'
[Service]
Environment=SWITCH_PASSWORD=real_switch_password
Environment=SWITCH_HOST=192.168.0.1
Environment=SWITCH_USER=admin
EOF

sudo systemctl daemon-reload
sudo systemctl restart pdudaemon
```

**Alternative (PDUDaemon with User=host user):** If PDUDaemon runs as a normal host user (not DynamicUser), `~/.config/switch.conf` is enough; no override.

### 5.3 Port ↔ DUT mapping

See [switch-config.md](./switch-config.md) for full mapping. The DUT must be on the correct switch port (per VLAN). Per-DUT state: [duts-config.md](./duts-config.md).

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `labgrid-client power cycle` fails with 500 (OpenWRT One) | PDUDaemon missing `fcefyn-poe` | Ensure `/etc/pdudaemon/pdudaemon.conf` includes PDU; copy from `openwrt-tests/ansible/files/exporter/labgrid-fcefyn/pdudaemon.conf` |
| `Password required` in pdudaemon journal on PoE power cycle | PDUDaemon (DynamicUser) cannot read `~/.config/` | systemd override with `Environment=SWITCH_PASSWORD=...`; see [section 5.2.1](#521-poe-pdu-password-with-dynamicuser) |
| `No route to host` on SSH | DUT on wrong switch port | Check mapping in switch-config.md; cable to correct port |
| `No route to host` (OpenWRT One) | Cable on PoE (WAN) port | Swap eth0/eth1: see [duts-config OpenWRT One](./duts-config.md#openwrt-one) |
| `Host key verification failed` | DUT reflashed or IP reused | `ssh-keygen -f ~/.ssh/known_hosts -R 192.168.1.1` |
| VLANs not created with netplan | Wrong renderer | Use `renderer: NetworkManager` |
| `systemd-networkd` errors with netplan | networkd not active on Desktop | Switch to `renderer: NetworkManager` |
| nmap only finds host | DUT on other port/VLAN | Check cable and switch port |
| Loss of switch access (192.168.0.1) after VLAN change | Trunk without VLAN 1 untagged | Ensure `tplink_jetstream.py` includes `switchport general allowed vlan 1 untagged` and `switchport pvid 1` on trunks (ports 9, 10) |
| Switch reachable but drops periodically (~45s) | `dhcp4: true` on netplan with no DHCP on VLAN 1 | `dhcp4: false` on trunk interface in netplan |
| Switch unreachable after host reboot | NM "Wired connection N" fights netplan | `nmcli connection delete "Wired connection 1"` |

---

## 7. Udev rules for serial adapters {: #7-udev-rules-for-serial-adapters }

USB-serial adapters connect the host console to each DUT. Udev rules create stable name symlinks (`/dev/belkin-rt3200-1`, etc.) for Labgrid and scripts.

**Symlinks:** [rack-cheatsheets.md](../operar/rack-cheatsheets.md). Example: `screen /dev/belkin-rt3200-1 115200`.

Rules file: `fcefyn-testbed-utils/configs/templates/99-serial-devices.rules`. Install on host:

```bash
sudo cp configs/templates/99-serial-devices.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### 7.1 Adapter models

| Chip   | Vendor:Product | Vendor               | Unique serial |
|--------|----------------|----------------------|---------------|
| **FTDI** | 0403:6001     | Future Technology Devices | Yes           |
| **CP210x** | 10c4:ea60   | Silicon Labs              | Sometimes not   |
| **CH340** | 1a86:7523    | QinHeng Electronics       | No           |

In FCEFyN lab:

- **FTDI:** Unique serial adapters. Match `ATTRS{serial}`; any hub port.
- **CP210x:** Belkin and Librerouter use `"0001"` (generic). Several share it; use physical USB port (`KERNELS`).
- **CH340:** No serial. Physical port only.

### 7.2 USB hub

**Current model:** Nisuta NSUH113Q (10 ports). *(Previously TP-Link UH700.)*

This hub **cannot** power ports on/off in software; DUT power cycle is via PDUDaemon (Arduino relay or PoE on switch).

### 7.3 USB hub layout

Adapters map to hub ports as follows:

| Hub port | Device       | Chip   | Symlink         | Strategy   |
|----------|--------------|--------|-----------------|--------------|
| 1          | Arduino Nano      | FTDI   | arduino-relay   | Serial       |
| 2          | Belkin RT3200 #1  | FTDI   | belkin-rt3200-1 | Serial       |
| 3          | Belkin RT3200 #2  | FTDI   | belkin-rt3200-2 | Serial       |
| 4          | Belkin RT3200 #3  | FTDI   | belkin-rt3200-3 | Serial       |
| 5          | Banana Pi R4      | FTDI   | bpi-r4          | Serial       |
| 6          | Librerouter 1     | CP210x | librerouter-1   | Port       |
| 7          | (reserved)       | -      | -               | -            |
| 8          | (reserved)       | -      | -               | -            |
| 9          | OpenWRT One       | FTDI   | openwrt-one     | Serial       |

### 7.4 Rule types

**By serial:** Devices with unique serial. Adapter can use any hub port.

```udev
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="A5069RR4", \
  SYMLINK+="arduino-relay", MODE="0666", GROUP="dialout"
```

**By USB port (fixed):** Devices without unique serial. Keep adapter on the same hub port. Use `KERNELS` wildcards (`*-1.1`, `*-1.2`, …) so rules work if USB bus numbers change across reboots. *(All three Belkin RT3200 units in the lab currently use FTDI with unique serials; this pattern applies if you add a CH340/CP210x without serial again.)*

```udev
SUBSYSTEM=="tty", KERNELS=="*-1.3.4", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", \
  SYMLINK+="example-no-serial-device", MODE="0666", GROUP="dialout"
```

### 7.5 Identifying new devices

To add a new adapter (e.g. Librerouter 2 or 3):

1. **See mapping on plug:** run `sudo dmesg -W` and plug the adapter. Kernel shows assigned tty (e.g. `ttyUSB0`, `ttyACM0`).

2. **Inspect attributes for udev:**

   ```bash
   udevadm info -a -n /dev/ttyUSB0
   ```

   In output (often device `parent` block):

   - `ATTRS{idVendor}`, `ATTRS{idProduct}` - always required.
   - `ATTRS{serial}` - if present and unique (FTDI), use for rule; adapter can use any port.
   - `KERNELS` - if no unique serial (CH340, generic CP210x), use hub path (e.g. `*-1.3.5`) to pin physical port.

3. Trim output:

   ```bash
   udevadm info -a -n /dev/ttyUSB0 | grep -E "ATTRS\{serial\}|ATTRS\{idVendor\}|ATTRS\{idProduct\}|KERNELS==" | head -8
   ```

4. If `ATTRS{serial}` is new vs existing, use serial rule. Else use `KERNELS` port rule.

### 7.6 Verification

```bash
ls -la /dev/arduino-relay /dev/belkin-rt3200-* /dev/bpi-r4 /dev/openwrt-one /dev/librerouter-*
```

*(bpi-r4 only when device connected)*

Each symlink should exist when the corresponding device is plugged.

---

## 8. Ansible integration {: #8-ansible-integration }

### 8.1 Internal playbook (fcefyn_testbed_utils)

`ansible/playbook_testbed.yml` installs FCEFyN-specific pieces **not** in the labgrid playbook (openwrt-tests):

- **virtual_mesh:** vwifi-server, QEMU, mac80211_hwsim (QEMU + vwifi virtual tests)
- **arduino:** arduino-relay-daemon, udev rules for serial devices
- **poe_switch:** poe_switch_control.py, switch_client, switch_drivers (PoE control)

- **zerotier:** ZeroTier for admin remote access (see [8.3](#83-remote-access-zerotier-for-admins-proxyjump-for-developers))
- **wireguard:** WireGuard tunnel to openwrt-tests global coordinator (see [8.3.1](#831-wireguard-global-coordinator))
- **wol:** persistent Wake-on-LAN (see [8.4](#84-wake-on-lan-persistence))

Run from fcefyn_testbed_utils repo root:

```bash
# Full install (needs -K for sudo)
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml -K

# virtual mesh only (vwifi, qemu, mac80211_hwsim)
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags virtual_mesh -K

# arduino daemon and udev only
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags arduino -K

# PoE switch control only
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags poe_switch -K

# ZeroTier only (remote access)
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags zerotier -K

# WireGuard only (global coordinator tunnel)
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags wireguard -K

# Wake-on-LAN only (persist after reboot)
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags wol -K


```

Recommended order: run `playbook_testbed.yml` before or after `playbook_labgrid.yml` (openwrt-tests); they are independent.

### 8.2 Labgrid playbook (openwrt-tests)

To automate host config with the openwrt-tests playbook:

1. Create `ansible/files/exporter/labgrid-fcefyn/netplan.yaml` with section 2.3 content.
2. Adjust `vlan_interface` if inventory uses variables, or put full config in host-specific file.
3. Run playbook against host `labgrid-fcefyn`.

Playbook prefers host-specific file over default template.

### 8.3 Remote access (ZeroTier for admins, ProxyJump for developers)

#### Two remote access levels

| Level | Who | How | Host user | Can do |
|-------|-----|-----|-------------|--------|
| **Developer** | Contributors listed in `labnet.yaml` | SSH `ProxyJump` via upstream `labgrid-coordinator:51818` (plus LAN when on site). No VPN. | `labgrid-dev` | Run tests, `labgrid-client` (lock, power, ssh, console), SSH to DUTs, TFTP symlinks. No general `sudo` (except `labgrid-bound-connect` and `switch-vlan` over SSH). |
| **Administrator** | Lab maintainers | Direct SSH via ZeroTier (or LAN) | Personal user with `sudo` | All above plus: Ansible, service management, switch config, package install, `switch-vlan` locally, etc. |

Developer access is the upstream openwrt-tests pattern and does not require ZeroTier. Setup on the developer machine: [Developer quickstart](../operar/developer-remote-access.md#2-configure-ssh).

#### Developer access (Labgrid + `labgrid-dev`)

No VPN. Two SSH hops:

1. Developer GitHub username in `labnet.yaml` `access:` list → Ansible fetches SSH keys from GitHub and copies to `~labgrid-dev/.ssh/authorized_keys` on both the lab host and the coordinator (the `coordinator.yml` playbook also fetches from GitHub).
2. Set `LG_PROXY=labgrid-fcefyn` on the developer machine; SSH chain resolves via `~/.ssh/config` (ProxyJump through `labgrid-coordinator`).
3. `labgrid-client` tunnels traffic (coordinator gRPC, exporter, SSH to DUTs) over SSH to host as `labgrid-dev`.
4. DUT SSH runs on host via `labgrid-bound-connect`; `switch-vlan` runs on host via the same SSH session (credentials in `/etc/switch.conf` stay on host).

Developer runs as `labgrid-dev` on host, no general `sudo`, cannot change system config.

#### Administrator access (ZeroTier + personal user)

ZeroTier is installed on the **host** only, not DUTs. Host reachable from the Internet without public IP or port forwarding. Admins SSH as personal user (with `sudo`) via ZeroTier IP for: Ansible, `systemctl`, SSH to DUTs, switch/MikroTik consoles.

**DUTs do not need ZeroTier.** Both developers and admins reach DUTs through the host (network gateway).

#### Install (Ansible role)

`ansible/roles/zerotier` installs ZeroTier on the orchestration host and joins lab VPN (`<ZT_NETWORK_ID>`, same as `defaults/main.yml` and [gateway 5.7](./gateway.md#57-zerotier-remote-access)).

**Location:** `ansible/roles/zerotier/` - tasks in `tasks/main.yml`, `zerotier_network_id` in `defaults/main.yml`.

**Role steps:**

1. Install `curl` if missing.
2. Get default-route interface (e.g. `wlp3s0`).
3. Temporary DNS (`resolvectl dns <iface> 8.8.8.8 8.8.4.4`) - needed if lab router does not resolve `install.zerotier.com`.
4. Install ZeroTier via official script (`curl -fsSL https://install.zerotier.com | bash`).
5. Start and enable `zerotier-one`.
6. Run `zerotier-cli join <ZT_NETWORK_ID>`.

```bash
cd fcefyn_testbed_utils
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags zerotier -K
```

After first run: authorize node in [my.zerotier.com](https://my.zerotier.com) → network `<ZT_NETWORK_ID>` → Members → **Auth** for labgrid-fcefyn.

```bash
zerotier-cli listnetworks   # verify
```

!!! note "ZeroTier role compatibility"
    Role targets Debian/Ubuntu (`ansible_os_family == "Debian"`).

**External devices (machines):** see [zerotier-remote-access](../operar/zerotier-remote-access.md).

### 8.3.1 WireGuard (global-coordinator) {: #831-wireguard-global-coordinator }

WireGuard tunnel between lab host and openwrt-tests **global-coordinator**. Lets the coordinator (datacenter VM with public IP) reach the host over SSH for DUT proxy, and CI runners run tests on lab devices.

**vs ZeroTier:** ZeroTier is for FCEFyN admin access. WireGuard is for upstream openwrt-tests integration. Both coexist.

#### Current status

Tunnel active. Lab host IP: `10.0.0.10/24`. Coordinator endpoint: `195.37.88.188:51820`. Values in `ansible/roles/wireguard/defaults/main.yml`.

#### Prerequisite: key exchange with maintainer

Before first run, coordinate with openwrt-tests maintainer (Paul):

1. Generate keypair on host (the Ansible role does this automatically if missing):

```bash
sudo apt install wireguard-tools
wg genkey | sudo tee /etc/wireguard/private.key | wg pubkey | sudo tee /etc/wireguard/public.key
sudo chmod 600 /etc/wireguard/private.key
```

2. Send public key (`cat /etc/wireguard/public.key`) to maintainer via Matrix.
3. Receive: assigned IP, coordinator endpoint, server public key.
4. Update `ansible/roles/wireguard/defaults/main.yml` with received values.

#### Install (Ansible role)

`ansible/roles/wireguard` installs `wireguard-tools`, generates keypair if missing, deploys `/etc/wireguard/wg0.conf` from template, enables `wg-quick@wg0.service`.

**Location:** `ansible/roles/wireguard/` - tasks `tasks/main.yml`, vars `defaults/main.yml`, template `templates/wg0.conf.j2`.

```bash
cd fcefyn_testbed_utils
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags wireguard -K
```

Role prints public key in debug output for sending to maintainer.

#### Verification

```bash
sudo wg show wg0              # interface state and last handshake
ping 10.0.0.1                 # reach coordinator (server-side WG IP)
```

!!! warning "Private key"
    Never commit `/etc/wireguard/private.key`. Role reads it from host at runtime.

!!! note "Compatibility"
    Role targets Debian/Ubuntu (`ansible_os_family == "Debian"`).

### 8.4 Wake-on-LAN (persistence)

`ansible/roles/wol` creates a systemd service running `ethtool -s enp0s25 wol g` at boot. Without it, WoL disables after each reboot. Full detail: [wake-on-lan-setup](../operar/wake-on-lan-setup.md).

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags wol -K
```

**Variable:** `wol_interface` (default: `enp0s25`). Prerequisite: BIOS Wake on LAN = AC Only.

### 8.5 TFTP and labgrid cache cleanup

`ansible/roles/tftp_cleanup` installs `/usr/local/sbin/tftp-cleanup` and a systemd timer (`tftp-cleanup.timer`, `OnCalendar=daily`). The script prunes broken symlinks under `/srv/tftp/` and removes orphan `/var/cache/labgrid/<user>/<sha>/` directories older than `tftp_cleanup_retention_days` (default 30). `/srv/tftp/firmwares/` is never touched. Full detail and tunables: [tftp-server §7](tftp-server.md#7-retention-and-cleanup).

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags tftp_cleanup -K
```

Inspection: `systemctl list-timers tftp-cleanup.timer` · `journalctl -u tftp-cleanup.service --since '7 days ago'`.

---
