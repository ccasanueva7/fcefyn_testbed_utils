# Routine operations

Deploy (Ansible), power, TFTP, VLANs, and health checks for the FCEFyN lab host. `labgrid-client` commands: [Labgrid commands](labgrid-useful-commands.md). Adding a DUT: [Adding a DUT](dut-onboarding.md).

---

## Ansible

Run from the repo `ansible/` directory. Requires `--ask-become-pass` (or `-K`) if the user does not have passwordless sudo.

| Action | Command |
|--------|---------|
| Full deploy | `ansible-playbook -i inventory.ini playbook_labgrid.yml -K` |
| Exporter only | `ansible-playbook -i inventory.ini playbook_labgrid.yml --tags export -K` |
| Users/keys only | `ansible-playbook -i inventory.ini playbook_labgrid.yml --tags users -K` |
| places.yaml only | `ansible-playbook -i inventory.ini playbook_labgrid.yml --tags places -K` |
| Dry-run | `ansible-playbook -i inventory.ini playbook_labgrid.yml --check -K` |

Detail: [ansible-labgrid](../configuracion/ansible-labgrid.md).

---

## DUTs and VLANs {: #duts-and-vlans }

### Labgrid inventory

All DUTs are exported through one global coordinator (datacenter VM, via WireGuard) and one exporter (`labgrid-exporter`).

| Component | Configuration |
|-----------|---------------|
| **Coordinator** | Global (Aparcar), reachable via WireGuard |
| **Exporter** | One `labgrid-exporter` service with all DUTs |
| **Default state** | Isolated VLANs (100-108) - compatible with openwrt-tests |
| **Dynamic VLAN** | `switch-vlan` CLI from [labgrid-switch-abstraction](https://github.com/fcefyn-testbed/labgrid-switch-abstraction); invoked by `conftest_vlan.py` and tunneled via SSH to the lab host when `LG_PROXY` is set |

### Dynamic VLAN and switch-vlan {: #dynamic-vlan-and-switch-vlan }

The default switch state is **isolated** (VLANs 100-108). **openwrt-tests** does not change VLANs. **libremesh-tests** invokes `switch-vlan` (CLI from `labgrid-switch-abstraction`) at test start and restores at teardown via `conftest_vlan.py`; when `LG_PROXY` is set the command runs on the lab host via SSH, so a remote developer never needs local switch credentials.

- **openwrt-tests:** DUTs stay on default isolated VLANs (100-108). No VLAN change.
- **libremesh-tests:** moves the DUT VLAN to 200 before each test and restores after.

```bash
# Restore all ports to isolated (base state)
switch-vlan --restore-all

# Move one DUT to mesh (VLAN 200) - manual debug only
switch-vlan belkin_rt3200_1 200

# Restore one DUT to its isolated VLAN
switch-vlan belkin_rt3200_1 --restore
```

In CI, VLAN changes run inside the libremesh-tests pytest fixture (no manual step). DUT/switch port database (`duts:` section): see [DUTs config](../configuracion/duts-config.md).

### Switch state tracking

Switch VLAN state is tracked in `~/.config/labgrid-switch-state.yaml`. Scripts: `switch_state.py`, `switch_vlan_preset.py`. Differential apply updates only ports that changed; if state and desired config diverge, a full apply corrects the switch. Use `--force` to force a full apply.

---

## Power cycle a DUT

```bash
# Arduino relay (Belkin RT3200 #1-3, BananaPi R4, LibreRouter #1)
sudo arduino_relay_control.py cycle 0    # Belkin #1
sudo arduino_relay_control.py cycle 1    # Belkin #2
sudo arduino_relay_control.py cycle 2    # Belkin #3
sudo arduino_relay_control.py cycle 3    # BananaPi R4
sudo arduino_relay_control.py cycle 4    # LibreRouter #1

# PoE switch (OpenWrt One)
sudo poe_switch_control.py cycle 1       # OpenWrt One

# Via Labgrid (requires reserved place)
labgrid-client -p labgrid-fcefyn-belkin_rt3200_1 power cycle
```

---

## Load firmware via TFTP

```bash
# 1. Copy firmware to firmwares directory
cp openwrt-*.bin /srv/tftp/firmwares/linksys_e8450/

# 2. Symlink with U-Boot expected name
ln -sf /srv/tftp/firmwares/linksys_e8450/openwrt-23.05-mediatek-mt7622-linksys_e8450-ubi-initramfs-kernel.bin \
       /srv/tftp/belkin_rt3200_1/linksys_e8450-initramfs-kernel.bin

# 3. Run test with LG_IMAGE pointing at symlink
LG_PLACE=labgrid-fcefyn-belkin_rt3200_1 \
LG_IMAGE=/srv/tftp/belkin_rt3200_1/linksys_e8450-initramfs-kernel.bin \
pytest tests/test_base.py -v
```

Layout and dnsmasq: [TFTP / dnsmasq](../configuracion/tftp-server.md).

---

## View switch state (current VLANs)

```bash
# Switch state via SSH (switch password required)
ssh switch-fcefyn
# On switch CLI:
show vlan all
show interfaces status
```

---

## Manual healthcheck

```bash
# SSH connectivity to all DUTs (isolated VLAN, default state)
for dut in dut-belkin-rt3200-1 dut-belkin-rt3200-2 dut-belkin-rt3200-3 \
           dut-bananapi-bpi-r4 dut-openwrt-one dut-librerouter-1; do
    echo -n "$dut: "
    ssh -o ConnectTimeout=5 -o BatchMode=yes "$dut" echo OK 2>&1 | tail -1
done
```

---

## Verify host services {: #verify-host-services }

```bash
systemctl status labgrid-exporter

# Common services
systemctl status pdudaemon
systemctl status dnsmasq
systemctl status arduino-relay-daemon

# Restart exporter
sudo systemctl restart labgrid-exporter
```
