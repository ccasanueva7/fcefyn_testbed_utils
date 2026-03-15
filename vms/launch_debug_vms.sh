#!/bin/bash
# Launch virtual mesh VMs for debugging (vwifi, user-mode networking)
# Usage: VIRTUAL_MESH_IMAGE=/path/to/image.img ./vms/launch_debug_vms.sh
# Example from repo root: VIRTUAL_MESH_IMAGE=firmwares/qemu/libremesh/lime-*.img ./vms/launch_debug_vms.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE="${VIRTUAL_MESH_IMAGE:-}"
if [ -z "$IMAGE" ]; then
    echo "ERROR: Set VIRTUAL_MESH_IMAGE environment variable"
    echo "Example: VIRTUAL_MESH_IMAGE=firmwares/qemu/libremesh/lime-viwifi-x86-64-ext4-combined.img $SCRIPT_DIR/launch_debug_vms.sh"
    exit 1
fi

# Resolve relative paths from repo root
if [[ "$IMAGE" != /* ]]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
    IMAGE="$REPO_ROOT/$IMAGE"
fi

NODES="${VIRTUAL_MESH_NODES:-2}"
BOOT_TIMEOUT="${VIRTUAL_MESH_BOOT_TIMEOUT:-120}"
CONVERGENCE_WAIT="${VIRTUAL_MESH_CONVERGENCE_WAIT:-60}"
SSH_BASE_PORT=2222
VWIFI_SERVER_IP="10.99.0.2"

echo "=== Cleaning up old processes ==="
sudo pkill -9 vwifi-server 2>/dev/null || true
sudo pkill -9 qemu-system 2>/dev/null || true
sleep 2

echo "=== Starting vwifi-server ==="
vwifi-server -u &
VWIFI_PID=$!
sleep 2

if ! kill -0 $VWIFI_PID 2>/dev/null; then
    echo "ERROR: vwifi-server failed to start"
    exit 1
fi
echo "vwifi-server running (PID $VWIFI_PID)"

echo "=== Launching $NODES VMs ==="
QEMU_PIDS=()

for i in $(seq 1 $NODES); do
    PORT=$((SSH_BASE_PORT + i - 1))
    MAC=$(printf "52:54:00:00:00:%02x" $i)
    MAC_VWIFI=$(printf "52:54:99:00:00:%02x" $i)
    HOSTFWD="tcp::${PORT}-10.13.0.1:22"
    
    echo "Starting VM $i (SSH port $PORT)..."
    
    qemu-system-x86_64 \
        -enable-kvm \
        -cpu host \
        -M q35 \
        -m 512 \
        -smp 2 \
        -nographic \
        -snapshot \
        -drive "file=${IMAGE},if=virtio,format=raw,file.locking=off" \
        -device "virtio-net-pci,mac=${MAC},netdev=mesh0" \
        -netdev "user,id=mesh0,net=10.13.0.0/16,hostfwd=${HOSTFWD}" \
        -device "virtio-net-pci,netdev=wan0" \
        -netdev "user,id=wan0" \
        -device "virtio-net-pci,mac=${MAC_VWIFI},netdev=vwifi0" \
        -netdev "user,id=vwifi0,net=10.99.0.0/24" \
        -device "virtio-rng-pci" \
        > /tmp/qemu-vm${i}.log 2>&1 &
    
    QEMU_PIDS+=($!)
done

echo "=== Waiting for VMs to boot (timeout: ${BOOT_TIMEOUT}s) ==="
for i in $(seq 1 $NODES); do
    PORT=$((SSH_BASE_PORT + i - 1))
    echo -n "Waiting for VM $i (port $PORT)..."
    
    for attempt in $(seq 1 $BOOT_TIMEOUT); do
        if ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
               -o ConnectTimeout=2 -o BatchMode=no -o PubkeyAuthentication=no \
               -p $PORT root@127.0.0.1 "echo ok" 2>/dev/null | grep -q ok; then
            echo " ready!"
            break
        fi
        sleep 1
        echo -n "."
    done
done

echo ""
echo "============================================================"
echo "VMs are running! SSH access:"
for i in $(seq 1 $NODES); do
    PORT=$((SSH_BASE_PORT + i - 1))
    echo "  ssh -p $PORT root@127.0.0.1  # VM $i"
done
echo "============================================================"
echo ""

if [ "${VIRTUAL_MESH_SKIP_VWIFI:-0}" != "1" ]; then
    echo "=== Configuring vwifi-client on each VM ==="
    for i in $(seq 1 $NODES); do
        PORT=$((SSH_BASE_PORT + i - 1))
        MAC_HEX=$(printf "%02x" $i)
        ETH2_IP="10.99.0.$((10 + i))"
        
        echo "Configuring VM $i..."
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
            -o LogLevel=ERROR -p $PORT root@127.0.0.1 "
            set -eu
            # Configure eth2 for vwifi connectivity
            ip link set eth2 nomaster 2>/dev/null || true
            ip addr flush dev eth2 2>/dev/null || true
            ip addr add ${ETH2_IP}/24 dev eth2
            ip link set eth2 up

            # Configure and start vwifi-client
            service vwifi-client stop 2>/dev/null || true
            uci set vwifi.config.server_ip='${VWIFI_SERVER_IP}'
            uci set vwifi.config.mac_prefix='02:00:00:00:00:${MAC_HEX}'
            uci set vwifi.config.enabled='1'
            uci commit vwifi
            service vwifi-client start
            sleep 5

            # Run lime-config then override to 2.4GHz channel 1.
            # Root cause: hostapd fails "Could not determine operating frequency"
            # on 5GHz with mac80211_hwsim; phy stays unchanneled, mesh NO-CARRIER.
            lime-config
            uci set wireless.radio0.channel='1'
            uci set wireless.radio0.band='2g'
            uci set wireless.radio0.htmode='HT20'
            uci commit wireless

            # Restart wireless
            wifi down
            sleep 1
            wifi up
            sleep 2

            echo \"VM${i}: configured\"
        " && echo "  VM $i: configured" || echo "  VM $i: FAILED"
    done
    
    echo ""
    echo "=== Waiting ${CONVERGENCE_WAIT}s for mesh convergence ==="
    sleep $CONVERGENCE_WAIT
fi

echo ""
echo "============================================================"
echo "Debug session ready! SSH access:"
for i in $(seq 1 $NODES); do
    PORT=$((SSH_BASE_PORT + i - 1))
    echo "  ssh -p $PORT root@127.0.0.1  # VM $i"
done
echo ""
echo "Press Ctrl+C to stop all VMs"
echo "============================================================"

cleanup() {
    echo ""
    echo "Shutting down..."
    for pid in "${QEMU_PIDS[@]}"; do
        kill $pid 2>/dev/null || true
    done
    kill $VWIFI_PID 2>/dev/null || true
    echo "Done."
}

trap cleanup EXIT INT TERM

# Wait forever
while true; do
    sleep 10
done
