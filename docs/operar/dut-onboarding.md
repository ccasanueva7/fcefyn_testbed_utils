# Guide: add or replace a DUT on the testbed

Onboard a new DUT or replace hardware on an existing switch port.

---

## Summary: files to change

Repos involved: **fcefyn-testbed-utils** (lab config) and **libremesh-tests** (labnet, ansible, targets).

| Step | Repo | File / action |
|------|------|----------------|
| 1. Hardware | - | USB serial to hub, cable to switch, power (relay or PoE) |
| 2. udev | fcefyn-testbed-utils | `configs/templates/99-serial-devices.rules` → `/etc/udev/rules.d/` |
| 3. dut-config | fcefyn-testbed-utils | `configs/dut-config.yaml` (`duts` section) |
| 4. labnet | libremesh-tests | `labnet.yaml` (devices, device_instances) |
| 5. Exporter / dnsmasq | libremesh-tests | `ansible/files/exporter/labgrid-fcefyn/exporter.yaml`, `dnsmasq.conf` |
| 6. PDUDaemon | libremesh-tests | `ansible/files/exporter/labgrid-fcefyn/pdudaemon.conf` (if power changes) |
| 7. Targets | libremesh-tests | `targets/<device>.yaml` (only if new device type) |
| 8. Netplan | libremesh-tests | `ansible/files/exporter/labgrid-fcefyn/netplan.yaml` (if new VLAN) |
| 9. TFTP | Host | `mkdir /srv/tftp/<place>/`, firmware, symlink |
| 10. Observability | fcefyn-testbed-utils | Install exporter on DUT + add `observability_duts` entry (see [observabilidad](../configuracion/observabilidad.md)) |
| 11. Deploy | - | Ansible (`playbook_labgrid.yml`) |
| 12. Verify | - | `labgrid-client places`, serial, SSH |

---

## New DUT (connecting to a free port on switch)

### 1. Hardware

- Connect a *trustable* DUT USB-serial adapter to hub.
- Ethernet from DUT to free switch port (e.g. port 3 or 15).
- Power: Arduino relay (free channel) or PoE (free port). See [switch-config](../configuracion/switch-config.md) and [host-config 5](../configuracion/host-config.md#5-power-control-and-mapping).

### 2. Identify serial adapter

Follow [host-config 7.5](../configuracion/host-config.md#75-identifying-new-devices):

- Run `sudo dmesg -W` and plug the adapter to see `/dev/ttyUSB*` or `/dev/ttyACM*`.
- Inspect attributes with `udevadm info -a -n /dev/ttyUSB0` (adjust port).
- If **unique serial** (FTDI): rule by `ATTRS{serial}`.
- If **no serial** (CH340, generic CP210x): rule by `KERNELS` per hub port.

### 3. udev

Edit `fcefyn-testbed-utils/configs/templates/99-serial-devices.rules` and add the rule for the new adapter. Example by serial:

```
# Belkin RT3200 #4 - FTDI, serial BG01ABCD
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="BG01ABCD", \
  SYMLINK+="belkin-rt3200-4", MODE="0666", GROUP="dialout", ENV{ID_MM_DEVICE_IGNORE}="1"
```

On the host:

```bash
sudo cp configs/templates/99-serial-devices.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
ls -la /dev/belkin-rt3200-4   # must exist with DUT connected
```

### 4. dut-config.yaml

In `fcefyn-testbed-utils/configs/dut-config.yaml`, add under `duts`:

```yaml
  belkin_rt3200_4:
    location: fcefyn-testbed
    serial_port: "/dev/belkin-rt3200-4"
    serial_speed: 115200
    pdu_host: "localhost:16421"
    pdu_name: "fcefyn-arduino"
    pdu_index: 4                    # free relay channel
    switch_port: 3                  # physical switch port
    switch_vlan_isolated: 106       # free VLAN (100-108)
    tftp_path: "belkin_rt3200_4/"
    libremesh_fixed_ip: "10.13.200.XXX"   # Mesh SSH/control IP on VLAN 200 (avoid collisions)
```

For PoE DUTs: use PDU name `fcefyn-poe` and set `pdu_index` to the switch PoE port number (same index passed to `poe_switch_control.py`). See `openwrt_one` in `configs/dut-config.yaml` and `libremesh-tests` `ansible/files/exporter/labgrid-fcefyn/exporter.yaml`.

### 5. labnet.yaml

In `libremesh-tests/labnet.yaml`:

- If **device type already exists** and you add another instance (e.g. another Belkin): add under `device_instances`:

```yaml
    device_instances:
      linksys_e8450:
        - belkin_rt3200_1
        - belkin_rt3200_2
        - belkin_rt3200_3
        - belkin_rt3200_4    # new
```

- If it is a **new device type** (not in `devices`): add under `devices` and `labs.labgrid-fcefyn.devices`. For a single unit, `device_instances` may be optional (place `labgrid-fcefyn-<device>`).

### 6. Exporter and dnsmasq

In `libremesh-tests/ansible/files/exporter/labgrid-fcefyn/`:

**exporter.yaml** - add place with RawSerialPort, PDUDaemonPort, TFTPProvider, NetworkService:

```yaml
labgrid-fcefyn-belkin_rt3200_4:
  RawSerialPort:
    port: "/dev/belkin-rt3200-4"
    speed: 115200
  PDUDaemonPort:
    host: "localhost:16421"
    pdu: "fcefyn-arduino"
    port: 4
  TFTPProvider:
    internal: "/srv/tftp/belkin_rt3200_4/"
    external: "belkin_rt3200_4/"
    external_ip: "192.168.106.1"
  NetworkService:
    address: "192.168.1.1%vlan106"
    username: "root"
```

**dnsmasq.conf** - if VLAN is new, add:

```
interface=vlan106
dhcp-range=vlan106,192.168.106.100,192.168.106.200,24h
```

### 7. PDUDaemon

If you use a **new Arduino channel** or **new PoE port**: edit `pdudaemon.conf` to add PDU/port if missing. For multi-channel Arduino relay, same PDU works; for PoE you may need one PDU per port (see [host-config 5.2](../configuracion/host-config.md#52-pdudaemon-etcpdudaemonpdudaemonconf)).

### 8. Targets

Only for a **new device type** not supported yet: create `libremesh-tests/targets/<device>.yaml` (drivers, prompts, boot strategies). See `targets/linksys_e8450.yaml` as reference. If reusing an existing device, skip.

### 9. Netplan

If you added a **new VLAN** (100-108), edit exporter `netplan.yaml` and add the interface. Example:

```yaml
    vlan106:
      id: 106
      link: enp0s25
      addresses:
        - 192.168.106.1/24
        - 192.168.1.106/24
```

Then `netplan apply` and `systemctl restart dnsmasq` on the host.

### 10. TFTP

On the host:

```bash
sudo mkdir -p /srv/tftp/belkin_rt3200_4
# Copy firmware to device type firmwares dir
# Symlink with U-Boot expected name (see tftp-server.md)
ln -sf /srv/tftp/firmwares/linksys_e8450/openwrt-*.bin /srv/tftp/belkin_rt3200_4/linksys_e8450-initramfs-kernel.bin
```

See [tftp-server](../configuracion/tftp-server.md) for naming per device.

### 11. Gateway router

If VLAN is new, configure gateway to route `192.168.XXX.0/24`. See [gateway](../configuracion/gateway.md).

### 12. SSH config (optional)

For alias `ssh dut-belkin-4`: add block in `~/.ssh/config` per `configs/templates/ssh_config_fcefyn`, with `ProxyCommand sudo labgrid-bound-connect vlan106 192.168.1.1 22` (use the DUT's isolated VLAN).

### 13. Deploy and verify

```bash
cd fcefyn-testbed-utils
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_labgrid.yml -K
labgrid-client places        # should list labgrid-fcefyn-belkin_rt3200_4
# Test serial and SSH
screen /dev/belkin-rt3200-4 115200
ssh dut-belkin-4
```

---

## Case B: Replace DUT (using a port where another device was connected)

When replacing hardware on an existing port (e.g. broken device in port 1 for another device in that port):

1. **udev**: If serial adapter differs (other chip or USB port), update rule in `99-serial-devices.rules` and reload udev. Same adapter: skip.
2. **dut-config**: Update `serial_port`, `libremesh_fixed_ip` if changed; `pdu_*` if power changes; keep `switch_port` and `switch_vlan_isolated`.
3. **labnet**: If device type changes (e.g. Belkin to LibreRouter), move between `device_instances` or adjust `devices`. Same type: often only place name changes if desired.
4. **exporter.yaml**: Update `RawSerialPort.port`, `TFTPProvider` if path changes, `NetworkService.address` if IP (mesh) changes. VLAN usually unchanged.
5. **pdudaemon.conf**: Only if PDU or port changes.
6. **targets**: Only if new device type.
7. **TFTP**: New directory if place name changes; appropriate firmware.
8. **Netplan / dnsmasq**: Unchanged (same VLAN).
9. **Deploy**: Ansible (`playbook_labgrid.yml`).
10. **duts-config.md**: Update DUT state in [duts-config](../configuracion/duts-config.md) and [rack-cheatsheets](rack-cheatsheets.md).
