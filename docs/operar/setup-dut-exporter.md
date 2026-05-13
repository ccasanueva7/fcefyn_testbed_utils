# DUT exporter setup (`setup_dut_exporter.py`)

Installs and configures [prometheus-node-exporter-lua](https://github.com/openwrt/packages/tree/master/utils/prometheus-node-exporter-lua) on OpenWrt DUTs via **SSH**. After running, Prometheus (on the lab host) scrapes metrics through the existing autossh tunnels and Grafana dashboards recover automatically.

---

## What it installs

| Package | Purpose |
|---------|---------|
| `prometheus-node-exporter-lua` | Core exporter (port 9100) |
| `prometheus-node-exporter-lua-openwrt` | OpenWrt-specific collectors (`node_openwrt_info`) |
| `prometheus-node-exporter-lua-hwmon` | Hardware temperature sensors |
| `prometheus-node-exporter-lua-wifi` | Wi-Fi station/network metrics |
| `luci-lib-nixio` | Dependency for filesystem collector |

Additionally deploys `filesystem.lua` custom collector (disk usage metrics not yet upstream).

UCI: binds exporter to **loopback only** (`listen_interface='loopback'`).

---

## Usage

```bash
# All DUTs (parallel SSH)
python scripts/setup_dut_exporter.py --all

# Single DUT
python scripts/setup_dut_exporter.py --device belkin-rt3200-1

# Preview without executing
python scripts/setup_dut_exporter.py --all --dry-run
```

**Prerequisite:** DUT must have internet access. Run [`provision_dut.py`](provision-dut.md) first.

---

## When to run

- After **reflashing** a DUT and running `provision_dut.py`.
- After **recovering** a bricked device.
- After **replacing** a DUT with a new unit.
- Safe to re-run (idempotent): `opkg install` skips already-installed packages, UCI overwrites, Lua file is replaced.

---

## Post-reflash sequence

```mermaid
flowchart LR
    Flash["Flash firmware"] --> Provision["provision_dut.py --serial"]
    Provision --> Exporter["setup_dut_exporter.py --SSH"]
    Exporter --> Grafana["Metrics in Grafana"]
```

1. `provision_dut.py` (serial) - mesh IPs, gateway, DNS, firewall, NTP
2. `setup_dut_exporter.py` (SSH) - exporter packages + config
3. Grafana recovers automatically via existing autossh tunnels

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| SSH timeout | DUT unreachable or no internet | Run `provision_dut.py` first, verify `ssh dut-belkin-1` works |
| opkg install fails | No internet or wrong date | Check gateway (`ip route`), DNS (`nslookup`), date (`date`) |
| `VERIFY_FAIL` | Service not started or port conflict | SSH in, check `/etc/init.d/prometheus-node-exporter-lua status` |
| Grafana shows no data | Tunnel not running on host | `systemctl status dut-metrics-tunnel-<name>` |

---

## See also

- [DUT provisioning](provision-dut.md) - prerequisite serial setup
- [Observability stack](../configuracion/observabilidad.md) - full architecture, Ansible host-side automation, dashboard details
- [Adding a DUT](dut-onboarding.md) - complete onboarding checklist
