# Running tests locally

Pytest and Labgrid on the lab host. Deploy and services: [Routine operations](lab-routine-operations.md).

---

## First time: validate the lab {: #first-time-validate-the-lab }

**Concepts:** Place = reservable DUT (serial, power, TFTP, SSH). Exporter = publishes places. Coordinator = reservations. `labgrid-client` / pytest acquire and run.

**Steps:** (1) Deploy configs via Ansible (see [Routine operations - Ansible](lab-routine-operations.md#ansible)). (2) `sudo systemctl start labgrid-coordinator labgrid-exporter` if not running. (3) `labgrid-client places`. (4) Firmware on TFTP: [TFTP / dnsmasq](../configuracion/tftp-server.md). (5) Reserve before pytest: `labgrid-client lock` (with `LG_PLACE`), run tests, `labgrid-client unlock`.

### labgrid-dev and TFTP symlinks {: #labgrid-dev-and-tftp }

TFTP dirs belong to **`labgrid-dev`**. For Labgrid to create symlinks when running tests, connect to the host as **`labgrid-dev`**. Paths and ownership: [host-config](../configuracion/host-config.md), [TFTP / dnsmasq](../configuracion/tftp-server.md).

---

## Single-node test (one DUT)

```bash
# OpenWrt
LG_PLACE=labgrid-fcefyn-belkin_rt3200_1 \
LG_IMAGE=/srv/tftp/belkin_rt3200_1/linksys_e8450-initramfs-kernel.bin \
uv run pytest tests/test_base.py tests/test_lan.py -v

# LibreMesh (fixture moves DUT VLAN to 200 automatically)
LG_PLACE=labgrid-fcefyn-belkin_rt3200_1 \
LG_IMAGE=/srv/tftp/belkin_rt3200_1/lime-linksys_e8450-initramfs-kernel.bin \
uv run pytest tests/test_libremesh.py tests/test_lan.py -v
```

---

## Multi-node LibreMesh test

The libremesh-tests fixture moves DUT VLANs to 200 automatically (via `labgrid-switch-abstraction`).

```bash
LG_MESH_PLACES="labgrid-fcefyn-openwrt_one,labgrid-fcefyn-bananapi_bpi-r4,labgrid-fcefyn-librerouter_1,labgrid-fcefyn-belkin_rt3200_2" \
LG_IMAGE_MAP="openwrt_one=/srv/tftp/.../openwrt-one-initramfs.itb,..." \
LG_MESH_KEEP_POWERED=1 \
uv run pytest tests/test_mesh.py -v
```

`LG_MESH_KEEP_POWERED=1` leaves DUTs powered after the test (VLANs are still restored to isolated). SSH via alias: `ssh dut-belkin-rt3200-2`.

### Robustness mechanisms

Multi-node tests include several layers of automatic recovery:

| Mechanism | Scope | Description |
|-----------|-------|-------------|
| Boot retries | Per node | Up to 3 attempts per node. Failures in U-Boot activation, TFTP download, and post-shell stages are retriable. |
| U-Boot proactive interrupt | Per node | Single-byte interrupt chars (`\x1b` ESC or `\x03` Ctrl-C) are sent proactively during boot to ensure U-Boot is captured before autoboot. |
| IP watchdog | Per node | Background script on the DUT re-applies the fixed SSH IP on `br-lan` every 3s for 300s, surviving network restarts. |
| SSH transport retry | Per node | `SSHProxy` retries up to 3 times on SSH exit code 255 (transport errors during mesh convergence). |
| Network settle | Global | After all nodes boot, a convergence window (60s base + 20s per extra node beyond 3) waits for batman-adv/babeld routing to stabilize. |

---

## Remote coordinator access (openwrt-tests)

```bash
# Aparcar coordinator is in the cloud; exporter does the work
# LG_COORDINATOR is set in CI runner env
export LG_COORDINATOR=ws://coordinator.aparcar.org:20408

# List available places
labgrid-client places

# Reserve a specific FCEFYN place
labgrid-client -p labgrid-fcefyn-openwrt_one reserve --wait --token mytoken
```
