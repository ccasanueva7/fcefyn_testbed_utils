# Documentación del Banco de pruebas HIL de la FCEFyN

Esta documentación describe el repositorio [fcefyn_testbed_utils](https://github.com/ccasanueva7/fcefyn_testbed_utils), donde están centralizados los componentes del **banco de pruebas hardware-in-the-loop** para [OpenWrt](https://openwrt.org/) y [LibreMesh](https://libremesh.org/) de la [Facultad de Ciencias Exactas, Físicas y Naturales](https://fcefyn.unc.edu.ar/) de la [Universidad Nacional de Córdoba](https://www.unc.edu.ar/).

La documentación cubre:

* Operación del laboratorio
* Diseño e infraestructura
* Componentes de hardware y software junto con sus configuraciones 
* Topología de red
* Integraciones con las suites de tests e infraestructura de pruebas de [openwrt-tests](https://github.com/aparcar/openwrt-tests) y su fork [libremesh-tests](https://github.com/francoriba/libremesh-tests)

---

## Antes de empezar

**Objetivo del banco** y alcance, en síntesis:

- **Validar firmware** de routers basados en *OpenWrt* y *LibreMesh* de forma **automatizada y repetible**, usando el ecosistema [Labgrid](https://labgrid.readthedocs.io/en/latest/) + [pytest](https://docs.pytest.org/en/stable/), en la línea de *openwrt-tests* y *libremesh-tests*.
- **Cubrir targets físicos y emulados**: permitir pruebas sobre **dispositivos físicos** dispuestos en un rack mediante enlaces físicos y sobre instancias [QEMU](https://www.qemu.org/) aprovisionadas con enlances WiFi simulados mediante [vwifi](https://github.com/sysprog21/vwifi).
- **Operar un laboratorio compartido**: bajo distintos modos de trabajo, y brindando acceso remoto para los administradores.

### Vista general del Banco de Pruebas

Relación entre host de orquestación, switch, gateway, DUTs, alimentación y acceso serial:

![Diagrama general del banco de pruebas y componentes principales](img/diagrams/general-design-overview.png)

El diseño parte del modelo de **laboratorios remotos** de [openwrt-tests](https://github.com/aparcar/openwrt-tests), pero el alcance no se reduce a **añadir dispositivos** a esa red. También se **reutiliza y amplía** el enfoque en **infraestructura propia**, con los mismos ejes (orquestación, red, alimentación, serial) y foco en pruebas de **LibreMesh**.

El diagrama anterior resume la topología: host, switch, gateway y rack.

---

## Cómo seguir

| Perfil | Empezar por | Luego |
|--------|-------------|-------|
| **Administrador del lab** | [Manual de operación](operar/SOM.md) | [Dashboard testbed-status](operar/testbed-status.md), [Rack cheatsheets](operar/rack-cheatsheets.md), [Agregar un DUT](operar/adding-dut-guide.md) |
| **Revisor o colaborador** | [Propuesta lab híbrido](diseno/hybrid-lab-proposal.md) | [Tracking](diseno/hybrid-lab-tracking.md), [CI](diseno/ci-use-cases-proposal.md) |
| **Desarrollador (tests)** | [Enfoque de testing](tests/libremesh-testing-approach.md) | [Manual de operación](operar/SOM.md) para ejecución en el lab |

