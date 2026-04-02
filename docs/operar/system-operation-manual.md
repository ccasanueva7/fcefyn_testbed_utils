# System operation manual: FCEFyN testbed

Vision, ownership, connectivity, and typical incidents for operators. Testbed procedures and commands can be found in [Lab procedures](lab-procedures.md).

---

## Mission summary

A testbed that can be accessed/operates remotely by allowed users validates **OpenWrt** and **LibreMesh** firmware automatically with **Labgrid** and **pytest**, on physical rack DUTs and, when applicable, emulated targets (QEMU). It integrates [openwrt-tests](https://github.com/aparcar/openwrt-tests) and the [libremesh-tests](https://github.com/francoriba/libremesh-tests) fork. Availability depends on the academic calendar and shared lab use; it is not a 24x7 service unless explicitly agreed.

---

## Technical summary

An orchestration host, either manually operated or running a CI runner, coordinates the execution of tests and infrastructure components. It runs a [Labgrid exporter](https://labgrid.readthedocs.io/en/stable/man/exporter.html), a [TFTP server](../configuracion/tftp-server.md), switch control commands, and [Pytest](https://docs.pytest.org/en/stable/) test suites.

Device access and scheduling are handled by a [Labgrid coordinator](https://labgrid.readthedocs.io/en/latest/man/coordinator.html), referred to as the [**global coordinator**](../diseno/openwrt-tests-onboarding.md/#1-global-coordinator-architecture) and provided by openwrt-tests. This component manages locks and reservations over devices and their associated labgrid remote [resources and places](https://labgrid.readthedocs.io/en/stable/overview.html#remote-resources-and-places).

The physical infrastructure is organized in a [DIY rack](../diseno/diy-rack.md), which includes a managed switch, power control mechanisms such as PoE and relays, USB serial adapters, Ethernet connections to the Devices Under Test (DUTs) and a fan/cooler.

---

## Ownership and support {: #ownership-and-support }

| Role                                 | Responsibility                                                                                                                                 |
|--------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| **UNC / FCEFyN Educative Community** | Rack maintenance, network infrastructure changes, onboarding of new devices, assistance for new contributors of openwrt-tests/libremesh-tests. |

Current support contacts from FCEFyN:

* [Ing. Jorge, Javier Alejandro](mailto:javier.jorge@unc.edu.ar)
* [Riba, Franco](mailto:franco.riba@mi.unc.edu.ar)
* [Casanueva, María Constanza](mailto:ccasanueva@mi.unc.edu.ar)

Auxiliar support contacts from our friends from related projects: 

* [Paul Spooren](mail@aparcar.org) (openwrt-tests project owner)
* [Ilario Gelmetti](iochesonome@gmail.com) (LibreMesh main representative)
---

## Stakeholders and consumers

| Actor | Usage                                                                 |
|-------|-----------------------------------------------------------------------|
| **FCEFyN lab maintainers** | Development, manual test runs, toubleshooting, debugging.             |
| **Global coordinator (Aparcar)** | Manages locks for all DUTs; lab exporter registers via WireGuard.     |
| **CI runners (openwrt-tests)** | Jobs that reserve places and run pytest with `LG_PLACE` / `LG_IMAGE`. |
| **CI runners (libremesh-tests)** | Jobs that reserve places, change VLAN dynamically, and run pytest.    |

---

## Architecture (high level)

High-level topology: [testbed overview on the home page](../index.md#testbed-overview) and diagram asset `docs/img/diagrams/general-design-overview.png`.

---

## Network connectivity

Summary of flows relevant to operations and incidents. Host firewall detail: [host-config](../configuracion/host-config.md). DUT Internet egress: [duts-config - Internet access](../configuracion/duts-config.md#internet-access-opkg).

| Direction | Scope | Source / destination | Protocol | Port | Notes |
|-----------|-------|----------------------|----------|------|-------|
| INPUT | Inside | Admin → host | SSH | 22 | Orchestrator management (LAN/VPN per policy). |
| INPUT | Inside | Host → DUT | SSH | 22 | Via `labgrid-bound-connect` (static isolated VLAN per DUT). |
| INPUT | Inside | DUT → host | TFTP | 69/udp | Initramfs load from host (udp). |
| INPUT | Inside | Host → switch | SSH | 22 | VLAN management (e.g. `switch-fcefyn`). |
| OUTPUT | Cross | Exporter → global coordinator | WebSocket | 20408 | To coordinator on datacenter VM via WireGuard. |
| INPUT | Public | Internet → Oracle VPS | HTTPS | 443 | Public Grafana (TLS on Nginx). |
| INPUT | Public | Internet → VPS | SSH | 22 | VPS admin; Grafana reverse tunnel goes **from** the lab. |
| OUTPUT | Cross / Public | DUT → Internet | HTTP/S | 80, 443, … | Per lab gateway NAT; see duts-config. |

---

## Automation

Automation of necessary operations is achieved using: 

- **Ansible:** `ansible/playbook_labgrid.yml` (exporter, places, users). See [ansible-labgrid](../configuracion/ansible-labgrid.md).
- **Dynamic VLAN:** `labgrid-switch-abstraction` (used by libremesh-tests in CI); manual ops: `switch-vlan`. Details in [Lab architecture](../diseno/lab-architecture.md).

---

## Observability

The infrastructure includes support for a [public grafana setup](../configuracion/grafana-public-access.md) which is possible using this [observavility stack](../configuracion/observabilidad.md).
