# Laboratorio Virtual de LibreMesh con QEMU

Este directorio contiene scripts para levantar y administrar redes mesh virtuales con QEMU.

| Script | Modo | Uso |
|--------|------|-----|
| `libremesh_node.sh` | TAP + bridge | Mesh por cable (eth), requiere `sudo` |
| `launch_debug_vms.sh` | vwifi + user-mode | Mesh por WiFi simulada (vwifi), sin `sudo` |

El objetivo es proporcionar un entorno de pruebas liviano que permita experimentar con el comportamiento de una red mesh y validar la convergencia de rutas antes de ejecutar pruebas sobre hardware real.

## Descripción general

### libremesh_node.sh (TAP mode)

El script `libremesh_node.sh` crea una red mesh virtual compuesta por múltiples nodos ejecutando LibreMesh/OpenWrt dentro de máquinas virtuales de QEMU.

Cada nodo se conecta mediante interfaces TAP a un bridge de red en el host Linux, permitiendo que todos los nodos se comuniquen como si estuvieran en la misma red de capa 2.

El enrutamiento de la red mesh es manejado internamente por BATMAN Advanced.

Este laboratorio virtual permite:

* Crear redes mesh virtuales rápidamente
* Simular la adición y eliminación de nodos
* Verificar la convergencia de la red
* Probar comportamiento de routing antes de usar hardware real

---

# Funcionalidades del script

El script permite administrar el laboratorio mesh mediante distintos comandos.

### Iniciar la red mesh

Levanta **N nodos LibreMesh** en máquinas virtuales QEMU.

```bash
./libremesh_node.sh start <N>
```

Ejemplo:

```bash
./libremesh_node.sh start 3
```

---

### Agregar nodos dinámicamente

Permite agregar nuevos nodos a la red mesh que ya está en ejecución.

```bash
./libremesh_node.sh add <N>
```

Ejemplo:

```bash
./libremesh_node.sh add 2
```

---

### Simular caída de un nodo

Permite finalizar un nodo específico para observar la reconvergencia de la red.

```bash
./libremesh_node.sh kill <ID>
```

Ejemplo:

```bash
./libremesh_node.sh kill 3
```

---

### Verificar estado de la red mesh

Ejecuta un chequeo de salud del laboratorio.

```bash
./libremesh_node.sh status
```

---

# Chequeos de salud de la red

El script valida automáticamente el estado de la red mesh utilizando diferentes métricas:

**Detección de nodos activos**

Se analiza la tabla FDB del bridge del host para contar las direcciones MAC de los nodos virtuales.

**Vecinos BATMAN**

Se consulta `batctl n` para verificar que los nodos descubrieron vecinos en la red mesh.

**Tabla de rutas BATMAN**

Se consulta `batctl o` para verificar que la red generó rutas válidas entre nodos.

Esto permite detectar rápidamente si:

* los nodos están activos
* el mesh se formó correctamente
* el routing está funcionando

---

# Configuración del host para hacer ping a las VMs

Para que el host pueda comunicarse con las máquinas virtuales (VMs) levantadas con QEMU y verlas mediante `ping`, es necesario preparar la red en el host.

## 1. Crear un bridge en el host

```bash
sudo ip link add name br0 type bridge
sudo ip link set br0 up
```

## 2. Asignar una IP al host

```bash
sudo ip addr add 10.13.0.10/16 dev br0
```

Esta interfaz permitirá que el host se comunique con los nodos virtuales del laboratorio.

---

# launch_debug_vms.sh (vwifi, user-mode)

Levanta VMs con mesh WiFi simulada via [vwifi](https://github.com/Raizo62/vwifi). No requiere `sudo` ni bridge. Útil para debuggear tests el comportamiento observado en tests automatizados.

### Uso

```bash
# Desde la raíz del repo
VIRTUAL_MESH_IMAGE=firmwares/qemu/libremesh/lime-viwifi-x86-64-ext4-combined.img ./vms/launch_debug_vms.sh
```

Variables de entorno: `VIRTUAL_MESH_IMAGE` (requerido), `VIRTUAL_MESH_NODES` (default 2), `VIRTUAL_MESH_BOOT_TIMEOUT`, `VIRTUAL_MESH_CONVERGENCE_WAIT`, `VIRTUAL_MESH_SKIP_VWIFI`.

### SSH

```bash
ssh -p 2222 root@127.0.0.1  # VM 1
ssh -p 2223 root@127.0.0.1  # VM 2
```

Ctrl+C detiene las VMs y vwifi-server.

---


