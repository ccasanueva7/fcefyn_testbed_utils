# PoE switch control (`poe_switch_control.py`)

`scripts/switch/poe_switch_control.py` manages PoE power on individual ports
of the TP-Link SG2016P managed switch. It is the backend used by PDUDaemon
to power OpenWrt One (port 1) and LibreRouter 1 (port 2) — devices that
receive power over Ethernet rather than via the Arduino relay board.

---

## 1. PoE port map

Ports 1–8 on the SG2016P support PoE. Only ports in active use:

| Switch port | DUT | Power mode | Notes |
|-------------|-----|------------|-------|
| 1 | OpenWrt One | PoE (802.3at) | Native PoE — direct |
| 2 | LibreRouter 1 | PoE via 48 V→12 V splitter | Active-to-passive conversion; see [switch config](switch-config.md) |

---

## 2. Usage

```bash
# Turn PoE on/off for a single port
poe_switch_control.py on  1
poe_switch_control.py off 1

# Power-cycle (off → sleep → on, default delay 3 s)
poe_switch_control.py cycle 1
poe_switch_control.py cycle 1 --delay 5

# Multiple ports at once
poe_switch_control.py on 1 2
```

---

## 3. Authentication

The script uses `SwitchClient` from `labgrid-switch-abstraction` for SSH.
Credentials are loaded in order:

1. `SWITCH_PASSWORD` environment variable
2. `~/.config/switch.conf` (INI format):

```ini
[switch]
host     = 192.168.0.1
user     = admin
password = <your-password>
```

The switch does not accept SSH public keys; password auth is required.
See [switch config](switch-config.md#ssh-access) for the SSH alias setup.

---

## 4. Lock serialization

Multiple PDUDaemon workers or manual invocations can run concurrently.
The script uses `fcntl.flock` on `/tmp/switch.lock` to serialize SSH
sessions and prevent contention on the switch's SSH daemon
(which handles only one session at a time reliably).

---

## 5. PDUDaemon integration

The Ansible role configures PDUDaemon with a `localcmdline` driver:

```ini
[poe-switch]
driver  = localcmdline
cmd_on  = poe_switch_control.py on %s
cmd_off = poe_switch_control.py off %s
cmd_status = poe_switch_control.py status %s
```

Labgrid target files reference this PDUDaemon entry via the
`PDUDaemonPower` resource:

```yaml
resources:
  PDUDaemonPower:
    host: localhost
    pdu: poe-switch
    index: 1    # switch port number
```

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Authentication failed` | Wrong password | Check `SWITCH_PASSWORD` or `~/.config/switch.conf` |
| `Connection refused` | Switch SSH not enabled or wrong IP | Verify `ssh switch-fcefyn` works manually |
| `Invalid PoE port` | Port number > 8 or non-integer | Only ports 1–8 support PoE on SG2016P |
| PoE on command succeeds but DUT stays off | Splitter issue (port 2 / LibreRouter) | Check 48 V→12 V splitter connection |
| Lock timeout | Another process holding `/tmp/switch.lock` | `rm /tmp/switch.lock` if the process is gone |

---

## See also

- [Switch configuration](switch-config.md) — VLAN setup and physical port layout
- [Arduino relay](arduino-relay.md) — non-PoE DUT power control
- [Adding a DUT](dut-onboarding.md) — how to register a new PoE DUT
