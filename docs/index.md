# Documentación – Lab FCEFyN

Banco de pruebas HIL (Hardware-in-the-Loop) para OpenWrt y LibreMesh.

---

## Guía por rol

| Rol | Empezar por | Luego |
|-----|-------------|-------|
| **Administrador del lab** | [Manual de operación](operar/SOM.md) | [Rack cheatsheets](operar/rack-cheatsheets.md), [Agregar un DUT](operar/adding-dut-guide.md) |
| **Revisor (tesis/propuesta)** | [Propuesta lab híbrido](diseno/hybrid-lab-proposal.md) | [Tracking](diseno/hybrid-lab-tracking.md), [CI](diseno/ci-use-cases-proposal.md) |
| **Desarrollador (tests)** | [Enfoque de testing](tests/libremesh-testing-approach.md) | [Manual de operación](operar/SOM.md) para ejecutar |

---

## Secciones

- **[Operar el lab](operar/SOM.md)** -- Procedimientos diarios, cambio de modos, power cycle, troubleshooting.
- **[Configuración](configuracion/host-config.md)** -- Detalle de cada componente: host, switch, gateway, DUTs, TFTP, Arduino, Ansible.
- **[Tests y desarrollo](tests/libremesh-testing-approach.md)** -- Enfoque de testing, proxy SSH, catálogo de firmware CI, troubleshooting Labgrid.
- **[Diseño y propuestas](diseno/hybrid-lab-proposal.md)** -- Propuestas técnicas, tracking de fases, CI, virtual mesh.

---

## Arquitectura

```mermaid
flowchart TB
    subgraph uplink [" "]
        MT["MikroTik (uplink opcional)"]
    end

    subgraph gateway [" "]
        OW["OpenWrt (gateway del testbed)\n.254 por VLAN"]
    end

    subgraph switch [" "]
        SW["TP-Link SG2016P"]
    end

    subgraph host [" "]
        H["Lenovo T430\nLabgrid · dnsmasq · PDUDaemon"]
    end

    subgraph duts ["DUTs (1 por puerto)"]
        D1["Belkin #1 — VLAN 100"]
        D2["OpenWrt One — VLAN 104"]
        DN["..."]
    end

    MT -->|WAN| OW
    OW -->|trunk 802.1Q| SW
    H -->|trunk| SW
    SW -->|access| D1
    SW -->|access| D2
    SW -->|access| DN
```

**Host:** orquesta tests, alimentación, SSH a DUTs. dnsmasq DHCP+TFTP en cada VLAN.
**Switch:** VLAN por DUT (100--108) o compartida (200 mesh).
**Gateway:** OpenWrt trunk al switch; enruta VLANs e internet. DHCP lo provee el host. Detalle: [gateway](configuracion/gateway.md).
