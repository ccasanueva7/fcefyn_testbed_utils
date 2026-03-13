# fcefyn-testbed-utils

Infraestructura complementaria del banco de pruebas HIL (Hardware-in-the-Loop) de FCEFyN: configs, scripts y firmwares que no forman parte de los repositorios contribuidos libremsh-tests y openwrt-tests

---

## Estructura

```
fcefyn-testbed-utils/
├── configs/              # Configs del lab
│   ├── pool-config.yaml
│   └── templates/        # Archivos a copiar al host (systemd, udev, ssh, etc.)
│   │   ├── arduino-relay-daemon.service
│   │   ├── labgrid-exporter-*.service
│   │   ├── 99-serial-devices.rules
│   │   ├── ssh_config_fcefyn
│   │   └── poe_switch_control.conf.example
├── docs/                 # Documentación (índice: docs/README.md)
├── scripts/              # Utilidades Python/shell
│   ├── switch/           # Switch SSH, VLANs, PoE, pool-manager
│   ├── arduino/          # arduino_relay_control, arduino_daemon, start_daemon
│   ├── testbed-mode.sh
│   ├── generate_places_yaml.py
│   ├── provision_mesh_ip.py
│   └── resolve_target.py
├── firmwares/            # Imágenes por dispositivo (qemu, Belkin, etc.)
├── arduino/              # Firmware del controlador de relés
├── rack_design/          # Diseño del rack
└── vms/                  # VMs de prueba (libremesh_node.sh)
```

---

## Setup (Ansible)

El setup productivo y local se hace con **Ansible** desde libremesh-tests (o openwrt-tests):

```bash
cd openwrt-tests   # o libremesh-tests
ansible-playbook -i inventory.ini playbook_labgrid.yml -l labgrid-fcefyn -K
```

El playbook despliega exporter, PDUDaemon, dnsmasq, netplan, places.yaml, etc. Ver [docs/ref/ansible-labgrid.md](docs/ref/ansible-labgrid.md).

---

## Scripts

| Script | Uso |
|--------|-----|
| `scripts/switch/poe_switch_control.py` | Puertos PoE del switch TP-Link (OpenWRT One, Librerouter). |
| `scripts/switch/switch_vlan_preset.py` | Cambia VLANs del switch (isolated vs mesh). |
| `scripts/switch/pool-manager.py` | Modo híbrido: exporters por pool, switch differential apply. |
| `scripts/arduino/arduino_relay_control.py` | Control de relés Arduino (power on/off). Usado por PDUDaemon. |
| `scripts/arduino/arduino_daemon.py` | Daemon de conexión persistente al Arduino. Servicio `arduino-relay-daemon`. |
| `scripts/arduino/start_daemon.sh` | Arranque manual del daemon Arduino. |
| `scripts/generate_places_yaml.py` | Genera `places.yaml` desde labnet.yaml. |
| `scripts/provision_mesh_ip.py` | Provisiona 10.13.200.x + ruta 10.13.0.0/16 por serial para SSH en mesh. Ver host-config §3.6. |
| `scripts/resolve_target.py` | Resuelve target file desde device name. |

Los scripts de control deben estar en `/usr/local/bin/` o en el PATH; el playbook puede copiarlos.

---

## Prerrequisitos

- **git-lfs** — `apt install git-lfs` antes de clonar (firmwares).
- Python 3, `pyserial`, `pipx`, dnsmasq, ser2net — el playbook Ansible instala la mayoría.
