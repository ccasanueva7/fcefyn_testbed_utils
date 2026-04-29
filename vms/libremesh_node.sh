#!/bin/bash
###############################################################################
# libremesh_node.sh
# Virtual LibreMesh/OpenWrt mesh lab with QEMU
###############################################################################

set -e

# directorio donde está el script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# imagen de firmware (en ../firmwares)
BASE_IMG="$SCRIPT_DIR/../firmwares/qemu/libremesh/libremesh-vwifi-x86-64-ext4-combined.img"


BRIDGE="br0"
HOST_IP="10.13.0.10"
NODE_IP="10.13.255.254"

MODE=$1
ARG=$2

###############################################################################
# CLEANUP
###############################################################################

cleanup_taps() {
    echo " Limpiando TAPs..."
    ip -o link show | grep -o 'tap[0-9]*' | while read tap; do
        sudo ip link delete $tap 2>/dev/null || true
    done
}

cleanup_qemu() {
    echo " Cerrando QEMU..."
    pkill -f qemu-system-x86_64 || true
}

###############################################################################
# NETWORK
###############################################################################

ensure_bridge() {

    if ! ip link show $BRIDGE &>/dev/null; then
        echo " Creando bridge $BRIDGE"
        sudo ip link add name $BRIDGE type bridge
        sudo ip addr add $HOST_IP/16 dev $BRIDGE
        sudo ip link set $BRIDGE up
    else
        echo " Bridge $BRIDGE ya existe"
    fi
}

###############################################################################
# TESTS
###############################################################################

run_tests() {

    echo ""
    echo "======================================"
    echo " Mesh health check"
    echo "======================================"

    BRIDGE_NODES=$(bridge fdb show br $BRIDGE | grep 52:54 | wc -l)

    BAT_NEIGH=$(ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$NODE_IP \
    "batctl n 2>/dev/null | awk 'NR>2 {print \$2}' | wc -l" || echo 0)

    BAT_ROUTES=$(ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$NODE_IP \
    "batctl o 2>/dev/null | grep LiMe | wc -l" || echo 0)

    echo "Nodes detected: $BRIDGE_NODES"
    echo "Batman neighbors: $BAT_NEIGH"
    echo "Batman routes: $BAT_ROUTES"

    echo "--------------------------------------"

    if [ "$BAT_NEIGH" -gt 0 ]; then
        echo " Mesh neighbors discovered"
    else
        echo " Mesh neighbors missing"
    fi

    if [ "$BAT_ROUTES" -gt 0 ]; then
        echo " Mesh routing OK"
    else
        echo " Mesh routing missing"
    fi

    echo "======================================"
}

###############################################################################
# NODE MANAGEMENT
###############################################################################

next_node_id() {

    LAST=$(ip -o link show | grep -o 'tap[0-9]*' | sed 's/tap//' | sort -n | tail -1)

    if [ -z "$LAST" ]; then
        echo 1
    else
        echo $((LAST+1))
    fi
}

launch_node() {

    ID=$1
    TAP="tap$ID"
    IMG="node$ID.img"
    MAC=$(printf "52:54:00:00:00:%02x" $ID)

    echo " Creando $TAP"
    sudo ip tuntap add dev $TAP mode tap user $USER
    sudo ip link set $TAP master $BRIDGE
    sudo ip link set $TAP up

    if [ ! -f "$IMG" ]; then
        cp $BASE_IMG $IMG
    fi

    echo " Lanzando nodo $ID"

    gnome-terminal --title="Nodo$ID" -- bash -c "
echo 'Nodo $ID iniciado';
qemu-system-x86_64 \
-enable-kvm \
-M q35 \
-cpu host \
-smp 2 \
-m 512M \
-nographic \
-drive file=$IMG,if=virtio,format=raw \
-device virtio-net-pci,netdev=net$ID,mac=$MAC \
-netdev tap,id=net$ID,ifname=$TAP,script=no,downscript=no
exec bash
"
}

###############################################################################
# START LAB
###############################################################################

if [ "$MODE" == "start" ]; then

    NODES=$ARG

    if [ -z "$NODES" ]; then
        echo "Uso: ./libremesh_node.sh start <nodos>"
        exit 1
    fi

    echo "======================================"
    echo " LibreMesh QEMU Virtual Lab"
    echo "======================================"

    cleanup_qemu
    cleanup_taps
    ensure_bridge

    for i in $(seq 1 $NODES); do
        launch_node $i
    done

    echo " Esperando arranque..."
    sleep 40

    run_tests
    exit 0
fi

###############################################################################
# ADD NODES
###############################################################################

if [ "$MODE" == "add" ]; then

    ADD=$ARG

    if [ -z "$ADD" ]; then
        echo "Uso: ./libremesh_node.sh add <nodos>"
        exit 1
    fi

    START=$(next_node_id)

    echo " Agregando $ADD nodos"

    for i in $(seq 0 $((ADD-1))); do
        ID=$((START+i))
        launch_node $ID
    done

    echo " Esperando convergencia..."
    sleep 30

    run_tests
    exit 0
fi

###############################################################################
# KILL NODE
###############################################################################

if [ "$MODE" == "kill" ]; then

    shift
    NODES="$@"

    for N in $NODES; do

        echo " Matando nodo $N"

        PID=$(ps aux | grep "tap$N" | grep qemu | awk '{print $2}')

        if [ -n "$PID" ]; then
            kill $PID
        fi

        sudo ip link delete tap$N 2>/dev/null || true
    done

    echo " Esperando reconvergencia..."
    sleep 20

    run_tests
    exit 0
fi

###############################################################################
# STATUS
###############################################################################

if [ "$MODE" == "status" ]; then
    run_tests
    exit 0
fi

echo "Uso:"
echo "./libremesh_node.sh start <nodos>"
echo "./libremesh_node.sh add <nodos>"
echo "./libremesh_node.sh kill <id>"
echo "./libremesh_node.sh status"