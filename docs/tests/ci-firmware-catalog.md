# CI Firmware Catalog

Reference for LibreMesh and OpenWrt firmware images used in the FCEFyN testbed CI pipelines.

---

## 1. Image Types

| Type | Use | Location |
|------|-----|----------|
| **LibreMesh physical** | Flash to real DUTs via TFTP | `firmwares/<device>/` |
| **LibreMesh QEMU** | Virtual mesh tests (vwifi) | `firmwares/qemu/libremesh/` |
| **OpenWrt vanilla** | openwrt-tests CI | Downloaded from `mirror-03.infra.openwrt.org` |

---

## 2. QEMU LibreMesh Image

The QEMU image is the primary image for virtual mesh CI. It runs on x86_64 and includes vwifi-client for simulated WiFi mesh.

### 2.1 Build configuration

| Parameter | Value |
|-----------|-------|
| **Base** | OpenWrt v23.05.5 |
| **Target** | x86 / x86_64 |
| **Profile** | generic |
| **Filesystem** | ext4 |
| **LibreMesh version** | v2024.1 |

### 2.2 Required packages

| Package | Purpose |
|---------|---------|
| `lime-proto-batadv` | batman-adv mesh |
| `lime-proto-babeld` | babeld routing |
| `lime-proto-anygw` | anycast gateway |
| `lime-app` | web UI |
| `lime-hwd-openwrt-wan` | WAN detection |
| `shared-state` | distributed node state |
| `kmod-mac80211-hwsim` | virtual WiFi radios (radios=0 at load) |
| `vwifi-client` | connects hwsim radios to vwifi-server |
| `libstdcpp6` | vwifi-client dependency |
| `wpad-basic-mbedtls` | **mandatory** — without it, mesh interfaces stay NO-CARRIER |

> **Note on wpad-basic-mbedtls**: This package is required for hostapd to bring up mesh interfaces on mac80211_hwsim. Without it, `wlan0-mesh` remains NO-CARRIER and batman-adv cannot see any active interfaces. It must be baked into the image — installing it via opkg after boot is not reliable for CI.

### 2.3 Deselected packages

The following must be deselected in `make menuconfig` to avoid conflicts:

- `dnsmasq` (Base system)
- `odhcpd-ipv6only` (Network)
- Enable feed libremesh (Image configuration → Separate feed repositories)
- Enable feed profiles (Image configuration → Separate feed repositories)

### 2.4 Build steps summary

See [build-firmware-manual](build-firmware-manual.md) for the full step-by-step build process including feed setup and menuconfig selections.

### 2.5 Output file

After a successful build, the image is located at:

```
openwrt/bin/targets/x86/64/openwrt-x86-64-generic-ext4-combined.img.gz
```

Decompress before use:
```bash
gunzip openwrt-x86-64-generic-ext4-combined.img.gz
```

### 2.6 Running with QEMU

Minimal command to boot the image and expose SSH on port 2222:

```bash
qemu-system-x86_64 \
  -m 256 \
  -drive file=openwrt-x86-64-generic-ext4-combined.img,format=raw \
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:2222-:22 \
  -device virtio-net-pci,netdev=net0 \
  -nographic
```

Connect after boot:
```bash
ssh -o StrictHostKeyChecking=no -p 2222 root@127.0.0.1
```

---

## 3. Physical DUT Images

Images for physical DUTs are built with the same LibreMesh feed but with device-specific targets.

| DUT | Target | Subtarget | Profile | Notes |
|-----|--------|-----------|---------|-------|
| Belkin RT3200 | mediatek | mt7622 | linksys_e8450-ubi | UBI layout required |
| Banana Pi R4 | mediatek | filogic | bananapi_bpi-r4 | |
| OpenWrt One | mediatek | filogic | openwrt_one | |
| LibreRouter v1 | ath79 | generic | librerouter_librerouter-v1 | |

Physical images are flashed via TFTP during the labgrid boot sequence. See [build-firmware-manual](build-firmware-manual.md) for build details.

---

## 4. Image Storage

| Location | Contents |
|----------|----------|
| `firmwares/qemu/libremesh/` | QEMU x86_64 LibreMesh images |
| `firmwares/<device-name>/` | Physical DUT images |

Images are tracked with **git-lfs**. Run `git lfs pull` after cloning to download them.

---

## 5. OpenWrt Vanilla Images

For openwrt-tests CI, vanilla OpenWrt images are not stored in this repo. They are downloaded automatically by the CI pipeline from:

```
https://mirror-03.infra.openwrt.org/
```

using a `.versions.json` index that maps each device to its snapshot/stable/oldstable image URL.
