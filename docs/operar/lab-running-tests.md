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
# OpenWrt vanilla
LG_PLACE=labgrid-fcefyn-belkin_rt3200_1 \
LG_IMAGE=/srv/tftp/firmwares/belkin_rt3200/openwrt/openwrt-23.05.5-vanilla-mediatek-mt7622-linksys_e8450-ubi-initramfs-recovery.itb \
uv run pytest tests/test_base.py tests/test_lan.py -v

# LibreMesh (fixture moves DUT VLAN to 200 automatically)
LG_PLACE=labgrid-fcefyn-belkin_rt3200_1 \
LG_IMAGE=/srv/tftp/firmwares/belkin_rt3200/libremesh/lime-24.10.5-mediatek-mt7622-linksys_e8450-initramfs-kernel.bin \
uv run pytest tests/test_libremesh.py tests/test_lan.py -v
```

---

## Multi-node LibreMesh test

The libremesh-tests fixture moves DUT VLANs to 200 automatically via `switch-vlan` invoked from `conftest_vlan.py` (SSH to the lab host if `LG_PROXY` is set).

```bash
LG_MESH_PLACES="labgrid-fcefyn-openwrt_one,labgrid-fcefyn-bananapi_bpi-r4,labgrid-fcefyn-librerouter_1,labgrid-fcefyn-belkin_rt3200_2" \
LG_IMAGE_MAP="labgrid-fcefyn-openwrt_one=/srv/tftp/firmwares/openwrt_one/libremesh/lime-24.10.5-mediatek-filogic-openwrt_one-initramfs.itb,labgrid-fcefyn-bananapi_bpi-r4=/srv/tftp/firmwares/bananapi_bpi-r4/libremesh/lime-24.10.5-mediatek-filogic-bananapi_bpi-r4-initramfs-recovery.itb,labgrid-fcefyn-librerouter_1=/srv/tftp/firmwares/librerouter_librerouter-v1/libremesh/lime-24.10.5-ath79-generic-librerouter_librerouter-v1-initramfs-kernel.bin,labgrid-fcefyn-belkin_rt3200_2=/srv/tftp/firmwares/belkin_rt3200/libremesh/lime-24.10.5-mediatek-mt7622-linksys_e8450-initramfs-kernel.bin" \
LG_MESH_KEEP_POWERED=1 \
uv run pytest tests/test_mesh.py -v
```

`LG_MESH_KEEP_POWERED=1` leaves DUTs powered after the test (VLANs are still restored to isolated). On the host, manual SSH to a node still on VLAN 200: `sudo labgrid-bound-connect vlan200 <mesh_ssh_ip> 22`. From a developer machine, the local `Host dut-*` aliases do **not** work for VLAN 200; use the nested `ProxyCommand` from [SSH access to DUTs - Remote developer](dut-ssh-access.md#remote-developer-lg_proxy).

---

## Running from a developer machine

A developer can run tests from their own machine using `LG_PROXY` to reach the lab. `LG_IMAGE` points to a **local file on the machine**; Labgrid uploads it to the lab server automatically (see [TFTP staging](../configuracion/tftp-server.md#42-remote-image-staging)). Full guide: [Developer quickstart](developer-remote-access.md).

```bash
# On the developer machine (not the lab host)
cd ~/pi/libremesh-tests
export LG_PLACE=labgrid-fcefyn-bananapi_bpi-r4
export LG_PROXY=labgrid-fcefyn
export LG_IMAGE=$HOME/builds/lime-24.10.5-mediatek-filogic-bananapi_bpi-r4-initramfs-recovery.itb
export LG_ENV=targets/bananapi_bpi-r4.yaml
uv run pytest tests/test_base.py -v --log-cli-level=INFO
```

The image is uploaded via SCP to `/var/cache/labgrid/<user>/<sha256>/` on the lab host, and a symlink is created in the DUT's TFTP directory. Subsequent runs with the same image skip the upload (hash match).

**Requirements:** the developer's SSH key must be in `labnet.yaml` (see [openwrt-tests onboarding](../diseno/openwrt-tests-onboarding.md#52-generate-ssh-key-for-new-developer)), and the lab host must be reachable via `LG_PROXY`.

The test suite locates `labnet.yaml` via `LABNET_PATH`, `OPENWRT_TESTS_DIR/labnet.yaml`, or `../openwrt-tests/labnet.yaml` (sibling of `libremesh-tests`). See [libremesh-tests CONTRIBUTING_LAB](https://github.com/fcefyn-testbed/libremesh-tests/blob/main/docs/CONTRIBUTING_LAB.md).

---

## Remote coordinator access (openwrt-tests)

```bash
# Aparcar coordinator is in the cloud; exporter does the work
# LG_COORDINATOR is set in CI runner env (HOST:PORT, gRPC - Labgrid 25.0+)
export LG_COORDINATOR=coordinator.aparcar.org:20408

# List available places
labgrid-client places

# Reserve a specific FCEFYN place
labgrid-client -p labgrid-fcefyn-openwrt_one reserve --wait --token mytoken
```
