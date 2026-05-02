# ImageBuilder limits for RAM-bootable LibreMesh

`tools/ci/build_image.sh` produces RAM-bootable LibreMesh images by
repacking three artifacts that come out of `make image PROFILE=...`:

1. The pre-built kernel binary `<profile>-kernel.bin`.
2. The pre-built device tree blob `image-<dts>.dtb` (FIT only).
3. A freshly-built rootfs CPIO of the LibreMesh root.

These are wrapped in a FIT (mediatek/filogic, mt7622) or in a legacy
`IH_TYPE_MULTI` uImage (ath79) that the testbed TFTP-boots from RAM.
The strategy works only when ImageBuilder ships a `KERNEL_INITRAMFS`
recipe for the profile - otherwise it cannot emit a kernel binary
that is RAM-bootable on its own.

This page documents two devices that fall outside that path and the
prototype work that was rejected.

## Devices not in the matrix

### `librerouter_librerouter-v1` (ath79/generic, MIPS)

Removed from `targets.yml` entirely. ath79/generic boots the legacy
uImage format and OpenWrt builds a single kernel image with the
initramfs CPIO **statically linked at compile time** via
`CONFIG_INITRAMFS_SOURCE`. The shipped `<profile>-kernel.bin` already
has the upstream OpenWrt rootfs hardcoded into the kernel, and
ImageBuilder cannot substitute our LibreMesh CPIO without recompiling
the kernel - which it cannot do, because it ships no kernel sources,
no compiler and no build infrastructure.

The labgrid YAML
`libremesh-tests/targets/librerouter_librerouter-v1.yaml` is preserved
for manual local/remote test runs against a pre-staged
`*-initramfs-kernel.bin`.

### `linksys_e8450` legacy (mediatek/mt7622, NAND non-UBI)

Replaced in `targets.yml` with `linksys_e8450-ubi`, which targets the
same Belkin RT3200 hardware via the UBI boot path. The legacy profile
in `target/linux/mediatek/image/mt7622.mk` does not define a
`KERNEL_INITRAMFS` recipe, so
`linksys_e8450-kernel.bin` is never produced under
`build_dir/.../linux-mediatek_mt7622/`. The `-ubi` profile defines
`KERNEL_INITRAMFS` and is the upstream-recommended boot path.

## Prototypes rejected for ath79

Three build paths for `librerouter_librerouter-v1` were tried before
removing the device from CI:

1. **`image_format: multi-uimage`** (legacy `IH_TYPE_MULTI` uImage with
   `[kernel.lzma, rootfs.cpio]`). The kernel boots, but the LibreRouter
   U-Boot 1.1.x fork ([LibreRouterOrg/u-boot][lr-uboot],
   `lib_mips/mips_linux.c`) does not propagate sub-image-1 to the MIPS
   kernel as `initrd_start` / `initrd_size`. The kernel cmdline ends up
   `console=ttyS0,115200n8 rootfstype=squashfs,jffs2`, the initramfs
   unpacker never runs, and the device falls through to the on-flash
   squashfs. CI symptom: `root@margarita:/#` instead of
   `root@LiMe-XXXXXX:/#`.

2. **OpenWrt SDK** (`ghcr.io/openwrt/sdk:ath79-generic-*`).
   `make image` inside the SDK fails immediately:

       make[1]: *** No rule to make target 'image'. Stop.

   The SDK ships only the `package/` subtree and the host toolchain;
   its `target/` and `include/image.mk` are deliberately stripped. By
   design the SDK compiles `.ipk` files against a pre-built kernel; it
   cannot rebuild the kernel.

3. **ImageBuilder with `CONFIG_TARGET_ROOTFS_INITRAMFS=y`**. Even with
   the kconfig flag forced, ImageBuilder only emits
   `*-squashfs-sysupgrade.bin`. `include/image.mk` skips the initramfs
   recipe entirely under `$(if $(IB),,...)`, again because there are
   no kernel sources to recompile.

[lr-uboot]: https://github.com/LibreRouterOrg/u-boot

## The only viable path: full source build

The only path that produces a real RAM-bootable LibreMesh image for
`librerouter_librerouter-v1` is a full OpenWrt source-tree build
(`make world`) with `CONFIG_INITRAMFS_SOURCE` pointing at the
LibreMesh CPIO. A prototype (`build_image_source.sh`, ~780 lines)
wired this up against `v24.10.6` with GHA caching: cold runs took
~50-60 min, warm runs ~10-20 min.

Discarded because:

- LibreMesh CI testing on ath79 is not a release-blocker.
- The full source build dominates wall-clock time for the entire
  workflow even when run in parallel with the other matrix entries.
- The maintenance surface (toolchain bumps, OpenWrt release tag
  drift, feed src-link plumbing, `libremesh.mk` symlink) is
  significant.

The prototype lives in the git history if it ever becomes worth
reviving.

## Resurrecting source build for ath79

If anyone resurrects the source-build path, the key inputs are:

1. Check out `openwrt/openwrt` at the matching tag (`v24.10.6`).
2. `make defconfig` with:

    ```text
    CONFIG_TARGET_ath79=y
    CONFIG_TARGET_ath79_generic=y
    CONFIG_TARGET_ath79_generic_DEVICE_librerouter_librerouter-v1=y
    CONFIG_TARGET_ROOTFS_INITRAMFS=y
    CONFIG_TARGET_INITRAMFS_COMPRESSION_LZMA=y
    ```

3. Wire `pi-lime-packages` as a `src-link` feed and make sure
   `libremesh.mk` is reachable from `package/feeds/lime_packages/`
   (otherwise the `include ../../libremesh.mk` lookups in
   `lime-proto-*` / `lime-hwd-*` silently drop those packages).
4. `make -j$(nproc) world` produces
   `bin/targets/ath79/generic/openwrt-*-librerouter_librerouter-v1-initramfs-kernel.bin`.

## Manual lab runs

For local lab runs against a manually-built artifact:

```bash
labgrid-client -p labgrid-fcefyn-librerouter_1 acquire
export LG_PLACE=labgrid-fcefyn-librerouter_1
export LG_ENV=targets/librerouter_librerouter-v1.yaml
export LG_IMAGE=/srv/tftp/firmwares/librerouter_librerouter-v1/libremesh/<artifact>.bin
uv run python -m pytest tests/test_libremesh.py tests/test_base.py tests/test_lan.py -v
labgrid-client -p labgrid-fcefyn-librerouter_1 release
```

## See also

- [CI: firmware build pipeline](../lime-packages-ci-flow.md) - the
  high-level pipeline that consumes `BUILD_INITRAMFS=1` artifacts.
- `tools/ci/build_image.sh` - the manual `mkimage` repack flow.
- `.github/ci/targets.yml` - `build_initramfs` / `test_firmware` keys.
