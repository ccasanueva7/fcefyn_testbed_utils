# System operation manual: FCEFyN testbed

Short manual for operators of the HIL testbed (vision, links, connectivity, typical incidents). **Step-by-step procedures and commands:** [Lab procedures](lab-procedures.md).

**Firmware images** for the lab (OpenWrt / LibreMesh, `LG_IMAGE`, TFTP): [Manual firmware build](../tests/build-firmware-manual.md) (site nav: **Testing and firmware**).

---

## Mission summary

The testbed validates **OpenWrt** and **LibreMesh** firmware automatically with **Labgrid** and **pytest**, on physical rack DUTs and, when applicable, emulated targets. It integrates [openwrt-tests](https://github.com/aparcar/openwrt-tests) and the [libremesh-tests](https://github.com/francoriba/libremesh-tests) fork. Availability depends on the academic calendar and shared lab use; it is not a 24x7 service unless explicitly agreed.

---

## Technical summary

An **orchestration host** runs the Labgrid exporter, TFTP, switch scripts, and test suites. A **global coordinator** (datacenter VM, via WireGuard) manages locks and reservations. The **rack** holds the managed switch, power (PoE / relays), USB serial, and cables to DUTs. [Unified pool architecture](../diseno/unified-pool-proposal.md). Overview diagram: [on the home page](../index.md#testbed-overview).

---

## Ownership and support {: #ownership-and-support }

| Role | Responsibility |
|------|----------------|
| **Service owner (FCEFyN lab)** | Prioritizes rack use, physical network changes, DUT onboarding. |
| **Day-to-day operation** | Exporter, VLANs, DUT checks. |
| **Major changes** | New DUT: [adding-dut-guide](adding-dut-guide.md). Infra: [ansible-labgrid](../configuracion/ansible-labgrid.md), [host-config](../configuracion/host-config.md). |

Current support contacts:

* [Riba, Franco](mailto:franco.riba@mi.unc.edu.ar)
* [Casanueva, María Constanza](mailto:ccasanueva@mi.unc.edu.ar)
* [Ing. Jorge, Javier Alejandro](mailto:javier.jorge@unc.edu.ar)

---

## Stakeholders and consumers

| Actor | Usage |
|-------|--------|
| **Global coordinator (Aparcar)** | Manages locks for all DUTs; lab exporter registers via WireGuard. |
| **CI runners (openwrt-tests)** | Jobs that reserve places and run pytest with `LG_PLACE` / `LG_IMAGE`. |
| **CI runners (libremesh-tests)** | Jobs that reserve places, change VLAN dynamically, and run pytest. |
| **FCEFyN lab maintainers** | Manual test runs and debugging via serial or SSH. |

---

## Related documentation

| Document | Contents |
|----------|----------|
| [lab-procedures.md](lab-procedures.md) | Unified pool, Ansible, SSH/serial, dynamic VLAN, TFTP, pytest. |
| [rack-cheatsheets.md](rack-cheatsheets.md) | DUT table, ports, one-line serial/SSH, switch. |
| [testbed-status.md](testbed-status.md) | Lab status TUI. |
| [adding-dut-guide.md](adding-dut-guide.md) | DUT onboarding or replacement. |
| [duts-config.md](../configuracion/duts-config.md) | DUTs, Internet, VLANs. |
| [ansible-labgrid.md](../configuracion/ansible-labgrid.md) | Playbooks, inventory, tags. |
| [tftp-server.md](../configuracion/tftp-server.md) | TFTP, symlinks, permissions. |
| [observabilidad.md](../configuracion/observabilidad.md) | Prometheus, Grafana on the host. |
| [grafana-public-access.md](../configuracion/grafana-public-access.md) | Grafana over HTTPS (VPS + tunnel). |
| [build-firmware-manual.md](../tests/build-firmware-manual.md) | Manual OpenWrt / LibreMesh / per-DUT builds. |

---

## Architecture (high level)

High-level topology: [testbed overview on the home page](../index.md#testbed-overview) and diagram asset `docs/img/diagrams/general-design-overview.png`.

---

## Network connectivity

Summary of flows relevant to operations and incidents. Host firewall detail: [host-config](../configuracion/host-config.md). DUT Internet egress: [duts-config - Internet access](../configuracion/duts-config.md#internet-access-opkg).

| Direction | Scope | Source / destination | Protocol | Port | Notes |
|-----------|-------|----------------------|----------|------|-------|
| INPUT | Inside | Admin → host | SSH | 22 | Orchestrator management (LAN/VPN per policy). |
| INPUT | Inside | Host → DUT | SSH | 22 | Via `labgrid-dut-proxy` / bound-connect; depends on VLAN mode. |
| INPUT | Inside | DUT → host | TFTP | 69/udp | Initramfs load from host (udp). |
| INPUT | Inside | Host → switch | SSH | 22 | VLAN management (e.g. `switch-fcefyn`). |
| OUTPUT | Cross | Exporter → global coordinator | WebSocket | 20408 | To coordinator on datacenter VM via WireGuard. |
| INPUT | Public | Internet → Oracle VPS | HTTPS | 443 | Public Grafana (TLS on Nginx). |
| INPUT | Public | Internet → VPS | SSH | 22 | VPS admin; Grafana reverse tunnel goes **from** the lab. |
| OUTPUT | Cross / Public | DUT → Internet | HTTP/S | 80, 443, … | Per lab gateway NAT; see duts-config. |

---

## Automation

- **Ansible:** `ansible/playbook_labgrid.yml` (exporter, places, users). See [ansible-labgrid](../configuracion/ansible-labgrid.md).
- **Dynamic VLAN:** `labgrid-switch-abstraction` (used by libremesh-tests in CI); manual ops: `switch-vlan`. Details in [unified pool architecture](../diseno/unified-pool-proposal.md).

---

## Observability

- Stack: [observabilidad.md](../configuracion/observabilidad.md).
- Internet-facing Grafana: [grafana-public-access.md](../configuracion/grafana-public-access.md) (start of doc: public URL and **access request**).

| Symptom | Quick action |
|---------|--------------|
| Exporter down | `systemctl status labgrid-exporter`; restart unit. See [Lab procedures 6.6](lab-procedures.md#66-verify-host-services). |
| DUT on wrong VLAN | Check with `ssh switch-fcefyn` → `show vlan all`. Restore manually: `switch-vlan <dut> --restore` or `switch-vlan --restore-all`. |
| Host disk full | `df -h`; clear cache or logs; Prometheus TSDB if applicable. |

---

## Security

* Public Grafana terminates TLS on the VPS; the lab uses an outbound SSH tunnel (does not expose Grafana on the host public IP), predefined users with secure access and permission levels.
* SSH keys and host/switch accounts follow best practices (secrets are not documented or published in the repo).
