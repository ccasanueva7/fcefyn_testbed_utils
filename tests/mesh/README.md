# Virtual Mesh Tests

Tests automatizados para el lab virtual de LibreMesh con QEMU + vwifi.

---

## Verificar la imagen antes de lanzar

Antes de correr las VMs conviene confirmar que la imagen es la correcta
(la del último build, no una vieja de los nodos `nodeN.img`).

### 1. Ver fecha y tamaño

```bash
ls -lh firmwares/qemu/libremesh/*.img vms/*.img
```

Ejemplo de salida esperada:

```
-rw-rw-r-- 1 constanza constanza 121M Apr  1 15:03 firmwares/qemu/libremesh/lime-24.10.5-viwifi-x86-64-generic-ext4-combined.img
-rw-rw-r-- 1 constanza constanza 121M Mar  9 01:37 vms/libremesh-vwifi-x86-64-ext4-combined.img   ← vieja
```

La imagen fresca está en `firmwares/qemu/libremesh/`. Los `vms/nodeN.img`
son copias que QEMU crea al arrancar y **no son el build fuente**.

### 2. Confirmar que es un disco x86 válido

```bash
file firmwares/qemu/libremesh/lime-*.img
```

Debe decir `DOS/MBR boot sector` — si dice otra cosa la imagen está corrupta.

### 3. Ver la versión de LibreMesh dentro de la imagen

```bash
strings firmwares/qemu/libremesh/lime-*.img | grep -E 'DISTRIB_RELEASE|lime_release|24\.'
```

Busca líneas como `DISTRIB_RELEASE="24.10.5"` o la referencia a `lime_release`.

### 4. Checksum rápido (opcional)

```bash
md5sum firmwares/qemu/libremesh/lime-*.img
```

Guardá el hash en la wiki/notion del equipo cada vez que buildeen una imagen
nueva para poder comparar después.

---

## Lanzar las VMs

```bash
# Desde la raíz del repo
VIRTUAL_MESH_IMAGE=firmwares/qemu/libremesh/lime-*.img ./vms/launch_debug_vms.sh
```

Variables de entorno disponibles:

| Variable | Default | Descripción |
|---|---|---|
| `VIRTUAL_MESH_IMAGE` | — | Path a la imagen (obligatorio) |
| `VIRTUAL_MESH_NODES` | `2` | Cantidad de VMs |
| `VIRTUAL_MESH_BOOT_TIMEOUT` | `120` | Segundos a esperar por boot |
| `VIRTUAL_MESH_CONVERGENCE_WAIT` | `60` | Segundos a esperar convergencia mesh |
| `VIRTUAL_MESH_SKIP_VWIFI` | `0` | Saltear config vwifi (para debug rápido) |

---

## Correr los tests

Desde la raíz del repo, con las VMs ya corriendo:

```bash
# Todos los tests del mesh lab
pytest tests/mesh/ -v

# Solo salud por nodo
pytest tests/mesh/test_mesh_node_basic.py -v

# Solo conectividad de red
pytest tests/mesh/test_mesh_basic.py -v

# Solo batman-adv
pytest tests/mesh/test_mesh_batman.py -v
```

Con más de 2 nodos:

```bash
VIRTUAL_MESH_NODES=3 VIRTUAL_MESH_IMAGE=firmwares/qemu/libremesh/lime-*.img \
  ./vms/launch_debug_vms.sh &

# Esperar convergencia, luego:
VIRTUAL_MESH_NODES=3 pytest tests/mesh/ -v
```

---

## Archivos

| Archivo | Qué hace |
|---|---|
| `conftest.py` | Fixtures SSH compartidos, fixture `node` parametrizado |
| `test_mesh_node_basic.py` | Salud por nodo: interfaces, servicios, UCI, kernel |
| `test_mesh_basic.py` | Conectividad de red: ping bat0, IPs únicas, visibilidad |
| `test_mesh_batman.py` | batman-adv: TQ, originadores, simetría, estadísticas |

---

## Acceso SSH manual

```bash
ssh -o StrictHostKeyChecking=no -p 2222 root@127.0.0.1  # VM 1
ssh -o StrictHostKeyChecking=no -p 2223 root@127.0.0.1  # VM 2
```

Comandos útiles dentro del nodo:

```bash
batctl n          # vecinos directos
batctl o          # tabla de originadores (todas las rutas)
batctl if         # interfaces esclavas
batctl s          # estadísticas
ip addr show bat0 # IP del nodo en la mesh
logread | grep lime-config  # ver si lime-config corrió
```
