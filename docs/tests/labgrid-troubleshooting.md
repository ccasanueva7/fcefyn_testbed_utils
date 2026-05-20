# Labgrid Troubleshooting

Common issues encountered when running tests with Labgrid on the FCEFyN testbed and how to fix them.

---

## 1. Place not available / resource locked

**Symptom**: `labgrid-client lock` fails or pytest hangs waiting to acquire a place.

**Causes and fixes**:

| Cause | Fix |
|-------|-----|
| Previous test run crashed without releasing | `labgrid-client -p <place> unlock` |
| Another process holds the lock | `labgrid-client who` to see who holds it |
| Exporter not running | `systemctl status labgrid-exporter-*` and restart if needed |
| Coordinator unreachable | Check `LG_CROSSBAR` env var and network connectivity to coordinator |

---

## 2. SSH connection refused or timeout

**Symptom**: pytest fails at the SSH step with `Connection refused` or `timeout`.

**Checks**:

1. Is the DUT powered on? Check PDUDaemon / relay status with `testbed-status`.
2. Did the DUT boot correctly? Check serial console output.
3. Is the DUT on the correct VLAN?
   ```bash
   # Verify switch mode
   testbed-status
   ```
4. For LibreMesh: was the fixed IP provisioned?
   ```bash
   python3 scripts/provision_mesh_ip.py <place_name>
   ```
5. For virtual: is the VM running and has it finished booting?
   ```bash
   # Check if port is open
   nc -zv 127.0.0.1 2222
   ```

---

## 3. LibreMesh DUT not reachable at 10.13.200.x

**Symptom**: SSH to `10.13.200.x` times out even though the DUT is powered and booted.

**Checks**:

1. Verify the host has the `10.13.0.0/16` route on `vlan200`:
   ```bash
   ip route show | grep 10.13
   ```
   If missing:
   ```bash
   ip route add 10.13.0.0/16 dev vlan200
   ```

2. Verify the fixed IP was actually assigned to the DUT:
   ```bash
   # Connect via serial
   screen /dev/ttyUSB0 115200
   # On the DUT:
   ip addr show br-lan
   ```

3. Check that the switch is in mesh mode (VLAN 200), not isolated mode:
   ```bash
   testbed-status
   # or
   python3 scripts/switch/switch_vlan_preset.py status
   ```

---

## 4. TFTP boot fails

**Symptom**: DUT gets stuck in U-Boot, `TFTP error: 'File not found'` or no DHCP response.

**Checks**:

1. Is dnsmasq running and serving on the correct VLAN interface?
   ```bash
   systemctl status dnsmasq
   ```

2. Is the firmware image in the TFTP root directory?
   ```bash
   ls /srv/tftp/
   ```

3. Is the DUT on the correct VLAN for TFTP? In OpenWrt mode each DUT is on its own VLAN; in LibreMesh mode all DUTs share VLAN 200. Make sure `testbed-mode` was run before flashing.

4. Check dnsmasq logs:
   ```bash
   journalctl -u dnsmasq -f
   ```

---

## 5. Exporter not registering with coordinator

**Symptom**: `labgrid-client resources` does not show the FCEFyN lab's places.

**Checks**:

1. Check exporter service:
   ```bash
   systemctl status labgrid-exporter-openwrt
   systemctl status labgrid-exporter-libremesh
   ```

2. Check environment variables in the service unit:
   ```bash
   systemctl cat labgrid-exporter-openwrt
   # Look for LG_CROSSBAR and LG_PROXY
   ```

3. Verify coordinator is reachable:
   ```bash
   curl -v ws://<coordinator-host>:20408/ws
   ```

4. Check `places.yaml` exists and is valid:
   ```bash
   cat /etc/labgrid/places.yaml
   python3 -c "import yaml; yaml.safe_load(open('/etc/labgrid/places.yaml'))"
   ```

---

## 6. vwifi mesh not forming (virtual mode)

**Symptom**: VMs boot and SSH works, but `batctl n` shows no neighbors or `wlan0-mesh` is NO-CARRIER.

**Checks**:

1. Is `wpad-basic-mbedtls` installed in the image?
   ```bash
   ssh -p 2222 root@127.0.0.1 "opkg list-installed | grep wpad"
   ```
   If missing, it must be baked into the image — see [ci-firmware-catalog](ci-firmware-catalog.md).

2. Is vwifi-server running on the host?
   ```bash
   pgrep -a vwifi-server
   ```

3. Did vwifi-client connect inside the VM?
   ```bash
   ssh -p 2222 root@127.0.0.1 "logread | grep vwifi"
   ```

4. Is `kmod-mac80211-hwsim` loaded in the VM?
   ```bash
   ssh -p 2222 root@127.0.0.1 "lsmod | grep mac80211_hwsim"
   ```
   If not:
   ```bash
   ssh -p 2222 root@127.0.0.1 "modprobe mac80211_hwsim radios=0"
   ```

---

## 7. Serial console not available

**Symptom**: `screen /dev/ttyUSBx` shows nothing or permission denied.

**Checks**:

1. Is the user in the `dialout` group?
   ```bash
   groups $USER
   # If not: sudo usermod -aG dialout $USER  (re-login required)
   ```

2. Is ser2net running?
   ```bash
   systemctl status ser2net
   ```

3. Is the correct USB device assigned to this DUT? Check `exporter.yaml` for the serial device mapping.

4. Is another process (minicom, screen) already holding the port?
   ```bash
   fuser /dev/ttyUSB0
   ```
