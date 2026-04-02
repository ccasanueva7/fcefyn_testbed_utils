# Switch configuration

The lab uses a **TP-Link SG2016P** (16× Gigabit, 8× PoE). **VLAN configuration** is **applied by scripts**, not as a manual CLI routine. Another **802.1Q** switch can reuse the same scheme with another driver under `scripts/switch/switch_drivers/`.

---

## 1. Context

The switch connects three roles:

1. **Gateway** (OpenWrt; formerly MikroTik): layer 3, routes between VLANs and Internet. [gateway.md](./gateway.md).
2. **Host** (Lenovo T430): Labgrid, dnsmasq/TFTP, SSH to DUTs.
3. **DUTs:** one OpenWrt or LibreMesh router per VLAN.

Gateway and host use **trunk** ports (802.1Q, tagged traffic). Each DUT is **access** (untagged traffic on its VLAN).

| Type   | Role | Traffic |
|--------|------|---------|
| **Access** | One DUT per port | Untagged |
| **Trunk**  | Multi-VLAN | Tagged (802.1Q) |

Trunks carry several VLANs; each DUT has a dedicated access port.

---

## 2. Switch requirements

- **802.1Q:** numeric IDs (e.g. 100+); each port access (untagged) or trunk (tagged).
- **PVID:** default VLAN if the frame arrives untagged (access = DUT VLAN; trunk = 1).
- **Ingress checking** on; **acceptable frame types:** Admit All.

---

## 3. Port-to-device mapping (FCEFyN)

### 3.1 Assignment table

| SG2016P port | Device       | VLAN | Type   |
|--------------|--------------|------|--------|
| 1              | OpenWrt One       | 104  | Access |
| 2              | LibreRouter #1    | 105  | Access (PoE + 48V→12V splitter) |
| 3              | LibreRouter #2    | 106  | Access |
| 4              | LibreRouter #3    | 107  | Access |
| 9              | Lenovo T430 (server) | Trunk | Trunk |
| 10             | OpenWrt router (gateway) | Trunk | Trunk |
| 11             | Belkin RT3200 #1  | 100  | Access |
| 12             | Belkin RT3200 #2  | 101  | Access |
| 13             | Belkin RT3200 #3  | 102  | Access |
| 14             | Banana Pi R4      | 103  | Access |
| 15             | (available)      | -    | -      |
| 16             | OpenWrt One (LAN) | 104  | Access |

Port 16 connects **LAN** of OpenWrt One when **PoE** power is on port 1; see [duts-config OpenWrt One](duts-config.md#openwrt-one). Ports 5-8 unassigned (default VLAN 1).

### 3.2 VLAN names in use

| VLAN ID | Name on switch   | Subnet           |
|---------|------------------|------------------|
| 100     | belkin_rt3200_1    | 192.168.100.0/24 |
| 101     | belkin_rt3200_2    | 192.168.101.0/24 |
| 102     | belkin_rt3200_3    | 192.168.102.0/24 |
| 103     | banana-pi-r4       | 192.168.103.0/24 |
| 104     | openwrt-one        | 192.168.104.0/24 |
| 105     | libre_router_1     | 192.168.105.0/24 |
| 106     | libre_router_2     | 192.168.106.0/24 |
| 107     | libre_router_3     | 192.168.107.0/24 |
| **200** | **mesh**           | 192.168.200.0/24 |

!!! note "Gateway and Internet on DUTs when changing mode"
    Besides **applying the VLAN preset on the switch**, `switch-vlan` (labgrid-switch-abstraction) can open **parallel SSH** to each DUT and adjust gateway, routes, and interfaces per preset. Steps and tables: [duts-config Internet access (opkg)](duts-config.md#internet-access-opkg).

    - **isolated:** per-VLAN gateway `192.168.XXX.254`.
    - **mesh:** gateway `192.168.200.254`.

    In both cases the script sets a **secondary IP** on the gateway subnet (`192.168.{vlan}.x` or `192.168.200.x` per `libremesh_fixed_ip`). Without it the testbed gateway does not route return traffic correctly (NAT / Internet). The same flow **stops the firewall** on the DUT.

---

## 4. Automated configuration

Testbed VLAN configuration is **not done manually** on the switch; these tools apply it:

| Tool | Use |
|------|-----|
| **switch-vlan** | labgrid-switch-abstraction CLI: per-DUT VLAN change (`switch-vlan <dut> <vlan>`, `--restore`, `--restore-all`). Used by tests and manual ops. |
| **labgrid-bound-connect** | SSH ProxyCommand (`socat` + `SO_BINDTODEVICE`) binds each DUT alias to its isolated VLAN. See [SSH access to DUTs](../operar/dut-ssh-access.md). |

Day-to-day: [DUTs and VLAN](../operar/lab-duts-and-vlan.md#dynamic-vlan-and-switch-vlan) (`switch-vlan` / `labgrid-switch-abstraction`; design: [Lab architecture](../diseno/lab-architecture.md)).

!!! note "Manual configuration (reference)"
    For recovery or debug: one test VLAN per access port (untagged); trunk ports with all VLANs tagged; PVID and ingress as in §2 (Admit All).

---

## 5. TP-Link SG2016P: SSH and PoE

### 5.1 SSH and CLI access

The switch accepts SSH for CLI management. Default IP: `192.168.0.1`. The switch **does not accept public-key auth**; use **password**.

See [host-config 3.6](host-config.md#36-ssh-config-for-manual-access-sshconfig) or template `configs/templates/ssh_config_fcefyn`.

Connect:

```bash
ssh switch-fcefyn
```

Prompt is `SG2016P>`.

!!! note "SSH client and authentication"
    The client tries public keys first; the switch rejects and drops the session. Set `PreferredAuthentications password` and `PubkeyAuthentication no` (template above).

**OpenWrt One** is on port 1 (PoE). For software power-cycle:

**Manual (SSH from host):**
```text
enable
configure
interface gigabitEthernet 1/0/1
power inline supply disable    # Power off OpenWrt One
# Wait 5-10 seconds
power inline supply enable     # Power on OpenWrt One
end
```

**Automatic (script):** Install via Ansible (recommended) or manually. Script needs `switch_client.py` and `switch_drivers/` alongside.

**Ansible install:**
```bash
# From fcefyn_testbed_utils
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml --tags poe_switch -K
```

**Manual install:** Install `labgrid-switch-abstraction` (`pip install git+https://github.com/fcefyn-testbed/labgrid-switch-abstraction.git`). Copy `scripts/switch/poe_switch_control.py` to `/usr/local/bin/`. Switch config in `~/.config/switch.conf`.

!!! warning "Credentials (out of repo)"
    That file holds the switch password: restrictive perms (`chmod 600`) and do not commit to git.

```bash
# Once: copy template and set switch password
cp configs/templates/switch.conf.example ~/.config/switch.conf
chmod 600 ~/.config/switch.conf
# Edit and set SWITCH_PASSWORD=real_password

# Use (from any directory)
poe_switch_control.py on 1    # Power on port 1 (OpenWrt One)
poe_switch_control.py off 1   # Power off
poe_switch_control.py cycle 1 # Power cycle (off, 5s, on)
poe_switch_control.py on 2    # Port 2 (Librerouter 1)
```

!!! note "Running with sudo"
    Both `poe_switch_control.py` and `switch-vlan` read config from the home of the user who invoked sudo (`SUDO_USER`). If you run `sudo switch-vlan libremesh`, password comes from `/home/<user>/.config/switch.conf`, not `/root/.config/`.

!!! note "PoE and concurrent SSH sessions"
    PDUDaemon may invoke several `poe_switch_control.py` in parallel (multiple PoE DUTs). TP-Link firmware **does not reliably tolerate** concurrent SSH sessions (timeouts). The script serializes access with a lock (`/tmp/switch.lock`, `fcntl.flock`); background calls queue.

!!! note "PDUDaemon integration"
    PoE uses **one** PDUDaemon PDU (`fcefyn-poe`); Labgrid selects the switch port via **index** (same number as in `poe_switch_control.py`). Multiple PoE DUTs do not use separate PDU names. Concurrent power scripts queue on a **lockfile** (switch SSH is not safe in parallel). See [host-config 5.2](host-config.md#52-pdudaemon-etcpdudaemonpdudaemonconf). If PDUDaemon was installed with Ansible (DynamicUser), use systemd override with `SWITCH_PASSWORD`; see [host-config 5.2.1](host-config.md#521-poe-pdu-password-with-dynamicuser).

### 5.2 OpenWrt One: two cables (PoE + LAN for U-Boot TFTP)

!!! note "WAN PHY timeout and second link (LAN)"
    With PoE on port 1, U-Boot on WAN (EN8811H) can hit PHY timeout. **Two links:** WAN (PoE) to port 1; LAN to port 16. Port 16 is VLAN 104 (untagged, PVID 104) so DHCP/TFTP reach the host. More in [duts-config OpenWrt One](duts-config.md#openwrt-one).

!!! note "LibreRouter 1 (port 2) and PoE"
    Uses PoE via 48V→12V splitter. LibreRouter needs passive PoE; switch delivers active (802.3af/at). A generic injector/splitter (e.g. POE-48V-12W Gigabit) converts 48V→12V. Enable PoE on switch port 2 to feed the splitter.

---

## 6. Labgrid integration

### 6.1 Consistency with exporter

VLAN ↔ DUT mapping must match Labgrid `exporter.yaml`:

```yaml
labgrid-fcefyn-belkin_rt3200_1:
  NetworkService:
    address: "192.168.1.1%vlan100"   # VLAN 100 = port 11
    username: "root"

labgrid-fcefyn-openwrt_one:
  NetworkService:
    address: "192.168.1.1%vlan104"   # VLAN 104 = port 1
    username: "root"
```

The `%vlanXXX` in `address` must match the DUT port **VLAN ID** on the switch; tagged traffic hits that interface on the server.

### 6.2 Traffic flow

1. Server sends to `192.168.1.1` from `192.168.1.100` (`vlan100` interface).
2. Frame leaves tagged VLAN 100 toward switch (port 9).
3. Switch forwards on port 11 (VLAN 100 access) untagged to Belkin.
4. Belkin replies; switch retags and sends to port 9 (server) or 10 (gateway) as appropriate.

---

## 7. Other switches

Same 802.1Q logic; need a driver that emits the vendor CLI commands.

1. Add a driver in `labgrid-switch-abstraction` per [DRIVER_INTERFACE.md](https://github.com/fcefyn-testbed/labgrid-switch-abstraction/blob/main/src/switch_abstraction/drivers/DRIVER_INTERFACE.md).
2. In `~/.config/switch.conf`: `SWITCH_DRIVER=<name>` and `SWITCH_DEVICE_TYPE=<netmiko_type>`.

Implement `PRESETS`, `build_preset_commands()`, `build_poe_commands()`, `build_hybrid_commands()`. Reference: `tplink_jetstream.py`.
