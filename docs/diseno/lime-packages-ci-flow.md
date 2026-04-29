# lime-packages CI: firmware build pipeline

How the **fcefyn-testbed/lime-packages** fork builds per-device LibreMesh images in GitHub Actions: OpenWrt SDK for IPKs, ImageBuilder for images, local feed indexing, caching, and where to change the matrix.

Companion: [lime-packages CI: hardware tests](lime-packages-test-flow.md). Manual builds remain in [Build firmware (manual)](../operar/build-firmware-manual.md).

---

## 1. Why two stages?

| Stage | Tool | Output | Why |
|-------|------|--------|-----|
| **build-feed** | OpenWrt **SDK** (via `openwrt/gh-action-sdk`) | `.ipk` packages under `lime_packages/` | Compiles **lime-packages** from source. Upstream `feed.libremesh.org` for OpenWrt 24.10 ships almost no `lime-*` / `shared-state-*` IPKs, so CI must build them. |
| **build-image** | **ImageBuilder** (`ghcr.io/openwrt/imagebuilder:…`) | Initramfs / sysupgrade images per profile | Reuses OpenWrt’s prebuilt kernel and base packages; only resolves and installs your feed + `PACKAGES`. Much faster than full Buildroot. |

```mermaid
flowchart LR
  PM[prepare-matrix]
  BF[build-feed per arch]
  BI[build-image per device]
  PM --> BF
  BF --> BI
```

---

## 2. Components

### OpenWrt SDK

Docker image `ghcr.io/openwrt/sdk:<sdk_arch>` (e.g. `aarch64_cortex-a53-openwrt-24.10`). Contains the cross-toolchain and OpenWrt build rules to compile a single feed’s packages into `.ipk` files.

### `openwrt/gh-action-sdk` (pinned tag, e.g. `@v9`)

GitHub Action that runs the SDK container with your repo mounted as feed `lime_packages`. For each package name in `PACKAGES` it effectively runs `feeds install -p lime_packages -f $pkg` and `make package/$pkg/compile`. In this fork, `prepare-matrix` fills `PACKAGES` with **every** directory under `packages/` that has a `Makefile`, because an empty list would only build `defconfig` targets—and no `lime-*` recipe defaults to `y/m`, so the feed would be empty.

### OpenWrt ImageBuilder

Docker image `ghcr.io/openwrt/imagebuilder:<target>-v<release>` (e.g. `mediatek-filogic-v24.10.6`). Ships a ready-made rootfs builder: `make image PROFILE=… PACKAGES="…"` pulls IPKs from configured feeds (downloads.openwrt.org + your local feed) and assembles the final firmware files.

### `ipkg-make-index.sh`

Script inside the ImageBuilder image (`/builder/scripts/ipkg-make-index.sh`). CI copies all `lime_packages` `.ipk` files into one directory and runs this script (with `MKHASH` and host `PATH` set) so `Packages` / `Packages.gz` have correct **`Filename:`** basenames. Wrong paths (e.g. absolute `/work/...`) break `opkg` when the feed is mounted as `file:///feed/lime_packages`.

### opkg-lede (ImageBuilder host opkg)

Host `opkg` used during image generation reads `repositories.conf`. For an **unsigned** local feed, CI must **remove** any `option check_signature` line—not set it to `0`—because the boolean parser treats the presence of the option as “on” regardless of value. See the **FCEFyN CI** section in [lime-packages README](https://github.com/fcefyn-testbed/lime-packages/blob/master/README.md).

---

## 3. Data-driven matrix (`.github/ci/targets.yml`)

Each target entry defines at least:

- `device`, `profile`, `imagebuilder` (ImageBuilder image suffix), `arch`, `sdk_arch`, `index_imagebuilder`, optional per-target **`packages:`** (overrides the global default list).

**Small-flash devices:** e.g. LibreRouter v1 cannot fit the full default `PACKAGES` in the sysupgrade partition; a reduced `packages:` list is defined only for that target. That affects **image size**, not which IPKs the SDK compiles (the SDK still builds the full feed).

---

## 4. Cache strategy (`actions/cache`)

- **Path cached:** `feed-artifact/lime_packages/` (merged arch + `all` IPKs + `Packages` / `Packages.gz`).
- **Exact key:** `lime-feed-v2-<arch>-<openwrt_release>-<feed_hash>`.
- **`feed_hash`:** sha256 over **package sources** (`Makefile`, `files/`, `patches/`, `src/` under `packages/`) plus `tools/ci/build_feed.sh`. It **excludes** `targets.yml` and `build-firmware.yml` so workflow-only or per-target image package tweaks do not force a ~50+ minute SDK rebuild when sources are unchanged.
- **`restore-keys`:** prefix `lime-feed-v2-<arch>-<openwrt_release>-` so a new hash can still restore the newest previous feed for that arch (partial reuse).

If you change the SDK action major version or the feed merge/index procedure incompatibly, bump the **`lime-feed-vN-`** prefix in `.github/workflows/build-firmware.yml` to avoid restoring stale binary caches.

---

## 5. Adding a new device

1. Add a row under `targets` in `.github/ci/targets.yml` with correct `imagebuilder` / `profile` / `arch` / `sdk_arch` / `index_imagebuilder` (see existing rows and [OpenWrt Table of Hardware](https://openwrt.org/toh/start)).
2. Ensure **libremesh-tests** has `targets/<device>.yaml` and **openwrt-tests** `labnet.yaml` lists the device if you want CI tests to run on it.
3. If the device has a tight flash layout, add a **`packages:`** override for that target only.

---

## 6. Updating the `lime-docs` source pin

Procedure lives in the upstream-style README of the fork: section **“Updating lime-docs source pin”** in [lime-packages README](https://github.com/fcefyn-testbed/lime-packages/blob/master/README.md) (`packages/lime-docs/Makefile`: `PKG_SOURCE_VERSION`, `PKG_VERSION`, `PKG_MIRROR_HASH`).
