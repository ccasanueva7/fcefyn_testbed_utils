# Adding a device to the lime-packages CI

Step-by-step guide to onboard a new board into the
[`build-firmware.yml`][wf] pipeline. The end result is per-release
firmware built for the board (and, if you want lab coverage, automated
tests on the self-hosted runner).

Companion pages:

- [CI: firmware build pipeline](lime-packages-ci-flow.md)
- [CI: hardware test stage](lime-packages-test-flow.md)
- [DUT onboarding](../operar/dut-onboarding.md)

[wf]: https://github.com/fcefyn-testbed/lime-packages/blob/master/.github/workflows/build-firmware.yml

---

## 1. Prerequisites

Before adding a device to the matrix:

1. **OpenWrt support**: the board has an upstream OpenWrt profile and
   ImageBuilder ships images for the relevant releases. Look up the
   board on [OpenWrt ToH][toh] - if there is no entry, this guide does
   not apply yet.
2. **FIT-capable U-Boot** (recommended): RAM-bootable initramfs FITs
   are how `test-firmware` gets a clean, predictable rootfs onto the
   DUT without flashing. ath79 boards on legacy U-Boot can use
   `multi-uimage` instead. x86_64 uses the `x86-combined` disk image.
3. **Lab onboarding done** (only if you want physical tests): the
   board is provisioned in the labgrid coordinator as
   `labgrid-fcefyn-<place>` with TFTP, serial console, network and
   power control. Follow [DUT onboarding][dut].
4. **A `targets/<device>.yaml` in libremesh-tests**: the labgrid
   environment file consumed by `pytest --lg-env`. This file lives in
   `fcefyn-testbed/libremesh-tests` (the test repo, separate from the
   `lime-packages` workflow repo). See the
   [libremesh-tests README][lr-readme] and the
   [two-repo model](lime-packages-test-flow.md#0-two-repo-model-workflow-vs-tests).

[toh]: https://openwrt.org/toh/start
[dut]: ../operar/dut-onboarding.md
[lr-readme]: https://github.com/fcefyn-testbed/libremesh-tests/blob/staging/README.md

---

## 2. `.github/ci/targets.yml` field reference

Each entry under `targets:` is a YAML map. Required fields are bold;
default behaviour is shown when a field is omitted.

| Field                          | Required? | Description                                         |
|--------------------------------|-----------|-----------------------------------------------------|
| **`device`**                   | yes       | Stable device key. Used as artifact name and TFTP path. |
| **`imagebuilder`**             | yes       | ImageBuilder image suffix (e.g. `mediatek-filogic`, `x86-64`). The full image is `ghcr.io/openwrt/imagebuilder:<suffix>-v<release>`. |
| **`profile`**                  | yes       | OpenWrt profile (`make image PROFILE=<this>`).      |
| **`arch`**                     | yes       | Package arch (`aarch64_cortex-a53`, `x86_64`, ...). Used to mount the right feed. |
| **`sdk_arch`**                 | yes       | SDK arch tag for `gh-action-sdk` (e.g. `aarch64_cortex-a53-openwrt-24.10`). |
| **`index_imagebuilder`**       | yes       | ImageBuilder image used to build the local feed index (`ipkg-make-index.sh` / `apk mkndx`). Same as `imagebuilder` for most boards. |
| `build_initramfs`              | no, default `false` | When true, repack the IB rootfs into a RAM-bootable artifact (FIT/uimage). When false, ship the squashfs-sysupgrade for IPK validation only. |
| `image_format`                 | no, default `fit` | One of `fit`, `multi-uimage`, `x86-combined`.    |
| `fit_arch`                     | required if `build_initramfs && image_format != x86-combined` | mkimage `-A` value (`arm64`, `mips`, ...). |
| `fit_kernel_loadaddr`          | same      | Kernel load + entry address as a hex string (e.g. `0x44000000`). |
| `fit_dts`                      | required if `image_format == fit` | DTS basename without extension (`mt7622-linksys-e8450-ubi`). The IB ships `image-<this>.dtb`. |
| `fit_config`                   | no, default `config-1` | FIT configuration node name. The labgrid YAML must `setenv bootconf` to match. |
| `fit_bootargs`                 | required if `image_format == fit` | Kernel bootargs injected into the FIT config. **Must not** contain `root=...` for FIT initramfs builds. |
| `uboot_interrupt_spam_sec`     | no        | Seconds the test fixture should send interrupt characters before U-Boot starts the autoboot countdown. Bump for boards with long pre-U-Boot init (BL2/BL31). |
| `dtb_patch_nvmem_mac`          | no        | True for boards whose OEM MAC lives in a UBI factory volume (workaround [openwrt#22858][nvmem]). |
| `dtb_force_legacy_partitions`  | no        | True for Belkin RT3200 layout-1.0 units (legacy SPI-NAND partitioning). |
| `packages`                     | no        | Per-target package list override. Use `{{ packages_default }}` to include the global default. Set explicitly on small-flash devices. |
| `extra_feeds`                  | no        | Extra src-git feeds piped into the SDK (`<type>\|<name>\|<url>^<sha>`). |
| `extra_packages`               | no        | Extra packages added to the build (the SDK still has to know how to build them - usually via `extra_feeds`). |
| `test_firmware`                | no, default `true` | When false, exclude this target from `test-firmware` (still built for IPK validation). |
| `test_qemu`                    | no, default `false` | When true, include this target in QEMU test jobs. |
| `test_places`                  | no, default `[<device>]` | Labgrid place names that run this artifact in `test-firmware`. Lets a single artifact (e.g. `linksys_e8450`) target multiple identical units (`belkin_rt3200_1`/`_2`/`_3`). |

[nvmem]: https://github.com/openwrt/openwrt/issues/22858

---

## 3. Add the matrix entry

For most boards, copy an existing similar entry and adjust. Examples:

### FIT-capable mediatek board

```yaml
- device: openwrt_one
  imagebuilder: mediatek-filogic
  profile: openwrt_one
  arch: aarch64_cortex-a53
  sdk_arch: aarch64_cortex-a53-openwrt-24.10
  index_imagebuilder: mediatek-filogic
  build_initramfs: true
  fit_arch: arm64
  fit_kernel_loadaddr: "0x44000000"
  fit_dts: mt7981b-openwrt-one
```

### Board with UBI-factory NVMEM (needs DTB patches)

```yaml
- device: linksys_e8450
  imagebuilder: mediatek-mt7622
  profile: linksys_e8450-ubi
  arch: aarch64_cortex-a53
  sdk_arch: aarch64_cortex-a53-openwrt-24.10
  index_imagebuilder: mediatek-filogic
  build_initramfs: true
  fit_arch: arm64
  fit_kernel_loadaddr: "0x44000000"
  fit_dts: mt7622-linksys-e8450-ubi
  test_firmware: true
  test_places:
    - belkin_rt3200_1
    - belkin_rt3200_2
    - belkin_rt3200_3
  uboot_interrupt_spam_sec: 25
  fit_bootargs: "console=ttyS0,115200n1 swiotlb=512 pci=pcie_bus_perf"
  dtb_patch_nvmem_mac: true
  dtb_force_legacy_partitions: true
```

### x86_64 QEMU virtual target

```yaml
- device: qemu_x86_64
  imagebuilder: x86-64
  profile: generic
  arch: x86_64
  sdk_arch: x86_64-openwrt-24.10
  index_imagebuilder: x86-64
  build_initramfs: false
  image_format: x86-combined
  packages: >-
    {{ packages_default }} kmod-mac80211-hwsim wpad-mesh-mbedtls vwifi
  extra_feeds:
    - "src-git|vwifi|https://github.com/fcefyn-testbed/vwifi_cli_package.git^<sha>"
  extra_packages:
    - "vwifi"
  test_firmware: false
  test_qemu: true
```

### Small-flash device

```yaml
- device: librerouter-v1
  imagebuilder: ath79-generic
  profile: librerouter_librerouter-v1
  arch: mips_24kc
  sdk_arch: mips_24kc-openwrt-24.10
  index_imagebuilder: ath79-generic
  build_initramfs: true
  image_format: multi-uimage
  fit_arch: mips
  fit_kernel_loadaddr: "0x80060000"
  fit_bootargs: "console=ttyS0,115200n8 root=/dev/ram0"
  packages: >-
    lime-system lime-proto-batadv lime-proto-anygw
    lime-hwd-openwrt-wan lime-hwd-ground-routing lime-app
    babeld-auto-gw-mode batctl-default
    -dnsmasq -odhcpd-ipv6only
```

---

## 4. Add the labgrid environment

The CI workflow (`lime-packages`) checks out
`fcefyn-testbed/libremesh-tests@staging` during each test job
(see [two-repo model][two-repo]). That repo owns all test definitions;
`lime-packages` owns the workflow and the matrix. If you want CI to
actually boot the new board:

1. Open a PR to `fcefyn-testbed/libremesh-tests` that adds
   `targets/<device>.yaml` with the labgrid driver chain for the new
   place (see the [libremesh-tests README][lr-readme]).
2. Make sure the place name registered in the coordinator matches
   `labgrid-fcefyn-<place>` in your `test_places:` list. The lock
   command is `labgrid-client -p labgrid-fcefyn-<place> lock`.
3. Confirm `aparcar/openwrt-tests` `labnet.yaml` lists the new device
   if any cross-test references it.
4. Merge the `libremesh-tests` PR to `staging` **before** enabling
   `test_firmware: true` on the `targets.yml` entry, otherwise the CI
   workflow will fail looking for `targets/<device>.yaml`.

[two-repo]: lime-packages-test-flow.md#0-two-repo-model-workflow-vs-tests

---

## 5. Validate end-to-end

Run the build path first (no lab access required):

```bash
gh workflow run build-firmware.yml \
  -f targets=<device> \
  -f openwrt_releases=24.10.6
```

Then opt into the lab path on the same branch (requires
`physical-lab` environment approval):

```bash
gh workflow run build-firmware.yml \
  -f targets=<device> \
  -f openwrt_releases=24.10.6 \
  -f physical_single=true
```

For multi-node mesh validation:

```bash
gh workflow run build-firmware.yml \
  -f targets=all \
  -f openwrt_releases=24.10.6 \
  -f physical_single=true \
  -f physical_mesh_count=3
```

---

## 6. Failure modes and where to look

| Symptom | First thing to check |
|---------|----------------------|
| `make image` errors with "package <name> not found" | `lime_packages` feed indexing - `feed_hash` cache may be stale; bump it or clear the cache. |
| Booted DUT prints `root@OpenWrt` instead of `root@LiMe-XXXXXX` | `build_image.sh` manifest validation should catch this; if you see it in tests, the image silently shipped without LibreMesh. Check the `build-image` log for the manifest contents. |
| Probe deferral, no LAN/WAN/wifi | OEM MAC lives in UBI factory volume. Set `dtb_patch_nvmem_mac: true` and check [DTB patcher source][lmpatch]. |
| Belkin RT3200 dies on first power cycle | Layout-1.0 unit. Set `dtb_force_legacy_partitions: true`. Background: [Belkin RT3200 DTB layout][belkin]. |
| `Initramfs unpacking failed` in kernel log | CPIO is compressed. `build_image.sh` already enforces newc magic; check the build log for the `cpio_magic` line. |
| Missing FIT artifact for ath79 | Use `image_format: multi-uimage`; FIT requires DTB to be a separate file. Background: [ImageBuilder limits][ib-limits]. |
| QEMU mesh tests fail to start `vwifi` | The `qemu_x86_64` package list must include `kmod-mac80211-hwsim`, `wpad-mesh-mbedtls` and `vwifi`. Background: [QEMU vwifi notes][qemu-doc]. |

[lmpatch]: https://github.com/fcefyn-testbed/lime-packages/blob/master/tools/ci/patch_dtb_local_mac.py
[belkin]: lime-packages/belkin-rt3200-dtb.md
[ib-limits]: lime-packages/imagebuilder-limits.md
[qemu-doc]: lime-packages/qemu-vwifi.md

---

## 7. Test locally before pushing

`prepare_matrix.sh` is self-contained and can be dry-run from a
checkout:

```bash
cd lime-packages
TARGETS_INPUT=<device> \
RELEASES_OVERRIDE=24.10.6 \
EVENT_NAME=workflow_dispatch \
GITHUB_OUTPUT=/dev/stdout \
bash tools/ci/prepare_matrix.sh
```

This prints the matrices that would be pushed to GitHub Actions. The
`feed_hash` line in the output is the cache key your build will use.
