# Ansible roles reference

`ansible/playbook_testbed.yml` installs components that complement the
upstream `playbook_labgrid.yml`. Each role maps to a tag so it can be run
independently.

---

## Quick reference

| Role | Tag | Function | Pre-requisite | Post-check |
|------|-----|----------|--------------|------------|
| `virtual_mesh` | `virtual_mesh` | Builds vwifi from source, installs QEMU, loads `mac80211_hwsim` | CMake, git, kernel headers | `which vwifi-server`, `lsmod | grep mac80211_hwsim` |
| `arduino_relay` | `arduino` | Deploys arduino daemon, udev rule for `/dev/arduino-relay`, systemd service | Arduino Nano connected | `systemctl status arduino-relay-daemon` |
| `poe_switch` | `poe_switch` | Installs `labgrid-switch-abstraction` via pipx, deploys `poe_switch_control.py` | Switch reachable via SSH | `poe_switch_control.py status 1` |
| `wireguard` | `wireguard` | Configures WireGuard tunnel to openwrt-tests global-coordinator | Public key shared with coordinator maintainer | `wg show` |
| `zerotier` | `zerotier` (via `testbed`) | Installs ZeroTier and joins network `93afae5963ea9881` | Node authorized at my.zerotier.com | `zerotier-cli info` |
| `wol` | `wol` | Enables Wake-on-LAN on the host NIC at boot via systemd | Correct interface in `wol_interface` | `ethtool enp0s25 | grep Wake` |
| `tftp_cleanup` | `tftp_cleanup` | Systemd timer that prunes broken TFTP symlinks and orphan labgrid cache dirs | TFTP dir at `/srv/tftp` | `systemctl status tftp-cleanup.timer` |
| `observability` | `observability` | Prometheus node-exporter, autossh tunnels per DUT, Grafana dashboards | DUTs reachable, Oracle VPS configured | `curl localhost:9100/metrics` |

---

## Running the playbook

```bash
# Full testbed provisioning
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml -K

# Single role by tag
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbook_testbed.yml \
    --tags virtual_mesh -K
```

`-K` / `--ask-become-pass` is required because most roles install system packages
and manage systemd units.

---

## Role details

### `virtual_mesh`

Installs the QEMU + vwifi stack required for virtual mesh tests:

- Clones and builds [vwifi](https://github.com/Raizo62/vwifi) with CMake
- Installs `qemu-system-x86`, `qemu-system-arm`
- Loads `mac80211_hwsim` at boot (via `/etc/modules-load.d/`)

Key variable: none (no defaults file; package names are hardcoded for Ubuntu).

### `arduino_relay`

- Deploys `scripts/arduino/arduino_daemon.py` to `/usr/local/bin/`
- Installs `configs/templates/arduino-relay-daemon.service` to systemd
- Writes a udev rule that creates `/dev/arduino-relay` symlink for the
  Arduino Nano's USB-serial adapter (matched by USB vendor/product ID)
- Enables and starts the daemon

See [Arduino relay](arduino-relay.md) for the channel map and CLI reference.

### `poe_switch`

- Installs `labgrid-switch-abstraction` via `pipx`
- Copies `scripts/switch/poe_switch_control.py` to `/usr/local/bin/`
- Creates `~/.config/switch.conf` from the `switch_password` variable
  (set in `ansible/inventory/group_vars/all.yml` or passed via `--extra-vars`)

See [PoE switch control](poe-switch-control.md) for usage and troubleshooting.

### `wireguard`

- Generates a WireGuard key pair on the host if one does not exist
- Renders `/etc/wireguard/wg0.conf` from a template with coordinator peer settings
- Enables `wg-quick@wg0` at boot

The lab's public key must be shared with the coordinator maintainer (Aparcar)
to be authorized in the coordinator's `wg0.conf`. See
[openwrt-tests onboarding](openwrt-tests-onboarding.md).

### `zerotier`

- Runs the official ZeroTier install script
- Joins network `93afae5963ea9881` (admin-only remote access)
- Node must be authorized manually at [my.zerotier.com](https://my.zerotier.com)

See [ZeroTier remote access](../operar/zerotier-remote-access.md).

### `wol`

- Sets `WakeOnLan=magic` on `wol_interface` (default: `enp0s25`) via
  a systemd network drop-in
- Verifies with `ethtool` that the NIC actually supports magic-packet WoL

The interface must match the host hardware. For the FCEFyN Lenovo T430
the interface is `enp0s25`.

See [Wake-on-LAN setup](../operar/wake-on-lan-setup.md).

### `tftp_cleanup`

Systemd timer that runs daily and removes:

- **Broken symlinks** under `tftp_cleanup_tftp_dir` (`/srv/tftp`)
- **Orphan labgrid cache dirs** under `tftp_cleanup_cache_dir`
  (`/var/cache/labgrid`) — directories with no referencing symlink and
  older than `tftp_cleanup_retention_days` days (default 30)

Key defaults (`ansible/roles/tftp_cleanup/defaults/main.yml`):

```yaml
tftp_cleanup_tftp_dir: /srv/tftp
tftp_cleanup_cache_dir: /var/cache/labgrid
tftp_cleanup_retention_days: 30
tftp_cleanup_schedule: "daily"
tftp_cleanup_dry_run: false
```

Set `tftp_cleanup_dry_run: true` to validate on a fresh host before
enabling real deletions.

### `observability`

- Installs and starts `prometheus-node-exporter` on the orchestration host
- Creates `autossh` systemd units that maintain reverse SSH tunnels from
  each DUT to a local port (19100–19105) for metrics scraping
- Deploys Grafana dashboard provisioning files

See [Observability](observabilidad.md) for the full monitoring stack.

---

## See also

- [Ansible / Labgrid](ansible-labgrid.md) — upstream `playbook_labgrid.yml`
  (exporter, places, SSH keys)
- `ansible/playbook_testbed.yml` — playbook source with per-role tag comments
