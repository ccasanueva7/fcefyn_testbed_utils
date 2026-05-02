# Belkin RT3200 layout 1.0 DTB patch

When the lab CI moved to OpenWrt 24.10 firmware, every Belkin RT3200
that ran a CI test boot KO'd on its next power cycle. This page is the
diagnosis and the rationale for the
[`patch_dtb_partitions.py`][patcher] CI patcher, gated by the
`dtb_force_legacy_partitions: true` flag in `.github/ci/targets.yml`
for the `linksys_e8450` target.

[patcher]: https://github.com/fcefyn-testbed/lime-packages/blob/master/tools/ci/patch_dtb_partitions.py

## Symptom

After `mtk_uartboot` recovery + U-Boot menu options 8 (write BL2) +
7 (write FIP), the unit boots once, passes its `test-firmware` job,
and is dead by the next power cycle. BL2 then prints on serial:

    ERROR: BL2: Failed to load image id 3 (-2)

(image id 3 = BL31; -2 = -ENOENT). 23.05.x firmware did not cause this;
the regression appeared on the move to 24.10.

## Root cause

OpenWrt rebuilt the SPI-NAND partitioning of `linksys_e8450` /
`Belkin RT3200` between 23.05 and 24.10, bumping
`DEVICE_COMPAT_VERSION` from 1.0 to 2.0:

| Layout | MTD partitions                                                        |
|--------|-----------------------------------------------------------------------|
| 1.0 (23.05) | `bl2 @0x000000`, `fip @0x080000`, `factory @0x1c0000`, `ubi @0x300000` |
| 2.0 (24.10) | `bl2 @0x000000`, `ubi @0x080000` (covers everything else; `fip`, `factory`, `ubootenv`, `fit` are UBI static volumes inside it) |

A device that has migrated to layout 2.0 (via `owrt-ubi-installer
v1.1.3+`) has a UBI created over `0x080000-0x8000000` with `fip` and
`factory` materialised as UBI static volumes - the 24.10 DTS describes
that on-flash topology and everything works.

A device still on layout 1.0 (the lab Belkins, recovered with
`mtk_uartboot` + 23.05.5 FIPs) has BL31 + U-Boot at SPI-NAND bytes
`0x080000-0x1c0000` and WiFi/MAC calibration at
`0x1c0000-0x2c0000`, with `ubi` only covering `0x300000+`. When the
24.10 kernel attaches UBI starting at `0x080000`, the kernel-side UBI
driver scans every PEB-sized block in that range. The bytes that hold
BL31+u-boot and factory carry no valid UBI EC header, so the scan
classifies them as candidate empty PEBs. Over the run, UBI's
wear-levelling allocator writes its volume table and one or more new
EBs over BL31/FIP and factory.

Next power cycle:

1. BootROM loads BL2 from offset `0x0` (still intact - read-only MTD).
2. BL2 loads FIP from offset `0x80000` (now a UBI EC header).
3. FIP signature check fails -> `Failed to load image id 3 (-2)`.

`hexdump /dev/mtd2` (factory) on a freshly-recovered Belkin shows
`UBI#` magic where calibration data should sit, confirming the
overwrite happened on a previous run.

## Why patch the FIT instead of migrating

The "proper" fix is to migrate to layout 2.0 with
`owrt-ubi-installer v1.1.4`. We tried this on the lab Belkins; the
installer aborts with:

    INSTALLER: cannot find Wi-Fi EEPROM data
    sysrq: Trigger a crash
    Kernel panic - not syncing: sysrq triggered crash

because earlier 24.10 CI runs already wrote UBI metadata over the
on-flash `factory` MTD: there is no calibration data left to back up,
so the installer refuses to migrate (correctly - migrating with empty
factory bytes would lose the unit's OEM MAC and WiFi calibration).
Recovering it would require a backup taken before the corruption (the
lab does not have one) plus serial-console reflashing of a known-good
factory image.

Patching the FIT-shipped DTB avoids the migration:

- The CI test boot is RAM-only initramfs. The kernel never sysupgrades,
  never enforces `DEVICE_COMPAT_VERSION`, and never has to match the
  on-flash layout exactly.
- BL2 + FIP + recovery on the device stay at 23.05.5, so future KOD
  recoveries keep working with the existing `mtk_uartboot` procedure
  documented in [DUTs config][dut].
- The patched DTB tells the kernel the device is on layout 1.0; the
  kernel attaches UBI strictly to MTD offset `0x300000+`, and BL31/FIP
  bytes are no longer reachable from the UBI driver.

The cost: the kernel inside the CI initramfs cannot use the layout-2.0
features (UBI-resident `ubootenv`, `factory`, `fit` static volumes).
That has no impact on what we test.

[dut]: ../../configuracion/duts-config.md

## What the patch does

[`patch_dtb_partitions.py`][patcher] replaces the
`&snand { partitions { ... } }` block in the FIT-shipped DTB with the
layout 1.0 shape:

| Partition          | Offset    | Notes                                       |
|--------------------|-----------|---------------------------------------------|
| `bl2 @0`           | `0x000000`| Read-only.                                  |
| `fip @80000`       | `0x080000`| Read-only.                                  |
| `factory @1c0000`  | `0x1c0000`| Read-only. Parent of the `eeprom_factory_*` and `macaddr_factory_*` nvmem-cells children. |
| `ubi @300000`      | `0x300000`| Kernel UBI MTD; layout 2.0 starting offset. |

The patcher also re-publishes `eeprom@0`, `eeprom@5000`,
`macaddr@7fff4` and `macaddr@7fffa` as nvmem-cell children of the
`factory` MTD. To keep references from `wmac`/`wmac1`/`gmac0`/`wan`
resolving across the rewrite, it reads the `phandle = <0xNN>;` integer
of each cell from the original `ubi-volume-factory > nvmem-layout`
block and injects the same integer on the new MTD-backed cell.
Numeric references downstream then resolve without a `__symbols__`
table - which OpenWrt 24.10 does not emit for kernel DTBs.

The patcher is a textual rewrite over the DTS produced by `dtc -I dtb
-O dts`. It hard-fails if:

- the input DTS contains zero or more than one
  `partitions { ... compatible = "linux,ubi" ... }` blocks;
- any of the four expected factory cell nodes (`eeprom@0`,
  `eeprom@5000`, `macaddr@7fff4`, `macaddr@7fffa`) is missing.

A node that is present but has no `phandle` property is fine - the
patcher emits the new node without one and trusts dtc to assign one on
recompile.

## What the patch does not do

- Restore factory calibration bytes that previous CI runs already
  overwrote. The MAC / EEPROM `factory` partition will read zeros (or
  UBI metadata) on units whose `factory` MTD region got clobbered
  before the patch was in place. `dtb_patch_nvmem_mac: true` already
  handles the MAC side by injecting `local-mac-address` properties;
  WiFi PHYs (mt7615 / mt7915) fall back to driver defaults for
  missing eeprom data.
- Move the on-flash device to layout 2.0. Re-attempting the
  `owrt-ubi-installer` migration on a recovered unit would require
  restoring a known-good `factory` blob first.

## How to verify on a CI run

After the patch lands, a build job for `linksys_e8450` should print:

    === Patching DTB stage 1: local-mac-address (workaround openwrt#22858) ===
    [patch_dtb_local_mac] ...
    === Patching DTB stage 2: legacy 23.05 SPI-NAND partitioning ===
    [patch_dtb_partitions] rewrote partitions block at bytes ... -> ... bytes

On the device side, after a CI test boot, `cat /proc/mtd` should
report:

    mtd0: 00080000 ... "bl2"
    mtd1: 00140000 ... "fip"
    mtd2: 00100000 ... "factory"
    mtd3: 07d00000 ... "ubi"

`dmesg` should not show any UBI scan over offsets below `0x300000`.
Power-cycling the unit after a CI run should bring it back up cleanly
at the U-Boot prompt - no KOD.

## Future cleanup

When the lab can give up layout-1.0:

1. Reflash a known-good `factory` blob via U-Boot menu (TFTP write
   to MTD), per OpenWrt's installer doc.
2. Run `owrt-ubi-installer v1.1.4` to migrate to layout 2.0.
3. Drop `dtb_force_legacy_partitions: true` from `targets.yml`. The
   patcher then becomes dead code; keep it around behind the flag as
   a recovery tool for any new layout-1.0 unit added to the lab.

Until step 1 is feasible, the CI patch is the only fix that keeps the
lab Belkins booting 24.10 firmware reliably.
