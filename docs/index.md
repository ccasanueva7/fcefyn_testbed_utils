# FCEFyN testbed documentation

**Hardware-in-the-loop** testing for [OpenWrt](https://openwrt.org/) and [LibreMesh](https://libremesh.org/) at [FCEFyN](https://fcefyn.unc.edu.ar/), [Universidad Nacional de Córdoba](https://www.unc.edu.ar/). Source and tooling live in [fcefyn_testbed_utils](https://github.com/ccasanueva7/fcefyn_testbed_utils). Tests align with [openwrt-tests](https://github.com/aparcar/openwrt-tests) and [libremesh-tests](https://github.com/francoriba/libremesh-tests).

---

## Before you start

**Testbed goal** and scope, in brief:

- **Validate firmware** for *OpenWrt* and *LibreMesh*-based routers in an **automated, repeatable** way using the [Labgrid](https://labgrid.readthedocs.io/en/latest/) + [pytest](https://docs.pytest.org/en/stable/) ecosystem, following *openwrt-tests* and *libremesh-tests*.
- **Cover physical and emulated targets**: tests on **physical devices** in a rack over physical links and on [QEMU](https://www.qemu.org/) instances with WiFi simulated via [vwifi](https://github.com/sysprog21/vwifi).
- **Operate a shared lab**: one DUT inventory for both projects ([Lab architecture](diseno/lab-architecture.md)) and remote access for administrators.

### Testbed overview

Relationship between orchestration host, switch, gateway, DUTs, power, and serial access:

![High-level diagram of the testbed and main components](img/diagrams/general-design-overview.png)

The design builds on the **remote lab** model from [openwrt-tests](https://github.com/aparcar/openwrt-tests), but scope is not limited to **adding devices** to that network. It also **reuses and extends** the approach with **local infrastructure**, along the same axes (orchestration, network, power, serial) with a focus on **LibreMesh** testing.
<!-- test comment mié 01 abr 2026 17:27:50 -03 -->
