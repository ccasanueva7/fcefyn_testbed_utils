#!/bin/bash
###############################################################################
# libremesh_nodes.sh
# Levanta N nodos QEMU LibreMesh/OpenWrt en terminal (nographic)
###############################################################################

NODES=${1:-2}   # Cantidad de nodos, por defecto 2
BASE_IMG="libremesh-vwifi-x86-64-ext4-combined.img"
BRIDGE="br0"

# Crear bridge si no existe
if ! ip link show $BRIDGE &>/dev/null; then
    echo "🔹 Creando bridge $BRIDGE..."
    sudo ip link add name $BRIDGE type bridge
    sudo ip addr add 10.13.0.1/16 dev $BRIDGE
    sudo ip link set dev $BRIDGE up
fi

# Crear TAPs e imágenes
for i in $(seq 1 $NODES); do
    TAP="tap$i"
    NODE_IMG="node$i.img"
    MAC=$(printf "52:54:00:00:00:%02x" $i)

    if ! ip link show $TAP &>/dev/null; then
        echo "🔹 Creando $TAP..."
        sudo ip tuntap add dev $TAP mode tap user $USER
        sudo ip link set dev $TAP master $BRIDGE
        sudo ip link set dev $TAP up
    fi

    if [ ! -f "$NODE_IMG" ]; then
        echo "🔹 Creando imagen $NODE_IMG..."
        cp "$BASE_IMG" "$NODE_IMG"
    fi

    echo "🚀 Lanzando Nodo $i con MAC $MAC..."
    gnome-terminal --title="Nodo$i" -- bash -c "
qemu-system-x86_64 -enable-kvm -M q35 -cpu host -smp 2 -m 512M -nographic \
  -drive file=$NODE_IMG,if=virtio,format=raw \
  -device virtio-net-pci,netdev=net$i,mac=$MAC \
  -netdev tap,id=net$i,ifname=$TAP,script=no,downscript=no
"
done
