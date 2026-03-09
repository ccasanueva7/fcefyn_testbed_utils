# pi-hil-testing-utils

Infraestructura complementaria del banco de pruebas HIL (Hardware-in-the-Loop) de FCEFyN: configs, scripts y firmwares que no están en libremesh-tests.

---

## Estructura

```
pi-hil-testing-utils/
├── configs/              # Documentación y configs del lab
│   ├── README.md         # Índice, orden de lectura
│   ├── templates/        # Archivos a copiar al host (systemd, udev, ssh, etc.)
│   │   ├── arduino-relay-daemon.service
│   │   ├── labgrid-exporter-*.service
│   │   ├── 99-serial-devices.rules
│   │   ├── ssh_config_fcefyn
│   │   └── poe_switch_control.conf.example
│   └── *.md              # Documentación (host-config, switch-config, etc.)
├── scripts/              # Utilidades Python/shell
│   ├── switch/           # Switch SSH, VLANs, PoE, pool-manager
│   ├── arduino/          # arduino_relay_control, arduino_daemon, start_daemon
│   ├── testbed-mode.sh
│   ├── generate_places_yaml.py
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

El playbook despliega exporter, PDUDaemon, dnsmasq, netplan, places.yaml, etc. Ver [configs/ansible-labgrid.md](configs/ansible-labgrid.md).

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
| `scripts/resolve_target.py` | Resuelve target file desde device name. |

Los scripts de control deben estar en `/usr/local/bin/` o en el PATH; el playbook puede copiarlos.

---

## Prerrequisitos

- **git-lfs** — `apt install git-lfs` antes de clonar (firmwares).
- Python 3, `pyserial`, `pipx`, dnsmasq, ser2net — el playbook Ansible instala la mayoría.
