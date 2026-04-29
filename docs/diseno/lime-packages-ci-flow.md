# lime-packages CI: firmware build

The [fcefyn-testbed/lime-packages](https://github.com/fcefyn-testbed/lime-packages) fork adds a
CI pipeline that builds firmware images automatically on pull requests and manual dispatches,
without requiring a full OpenWrt buildroot.

---

## Overview

```
PR or manual dispatch
        ↓
  OpenWrt SDK (Docker)
  compile lime-packages feed
        ↓
  OpenWrt ImageBuilder (Docker)
  assemble firmware per target
        ↓
  Upload artifacts:
    firmware-<device>.*
    lime-feed-<arch>
```

The SDK and ImageBuilder images come from `ghcr.io/openwrt/sdk` and
`ghcr.io/openwrt/imagebuilder`, pinned to a specific OpenWrt version.

---

## Workflow file

`.github/workflows/build-firmware.yml` in the fork. Triggered on:

- Pull requests to the default branch
- Manual dispatch (`workflow_dispatch`)

---

## Target matrix

Build targets are defined in `.github/ci/targets.yml`. Each row specifies:

| Field | Example | Description |
|-------|---------|-------------|
| `target` | `mediatek` | OpenWrt target architecture |
| `subtarget` | `mt7622` | OpenWrt subtarget |
| `profile` | `linksys_e8450-ubi` | Device profile |
| `openwrt_version` | `23.05.5` | OpenWrt release |

One firmware image is produced per row, in parallel.

---

## Artifacts

Successful runs upload:

- **`firmware-<device>.*`** — firmware image (`.bin` or `.itb`) with lime-packages included
- **`lime-feed-<arch>`** — compiled `.ipk` feed for the target architecture, usable by an
  ImageBuilder directly

Artifacts are kept for a configurable number of days (default: 7).

---

## Relationship to this repo

The firmware artifacts from the lime-packages fork CI feed into the
`flash_and_test` job of [build-and-test-libremesh.yml](../operar/ci-build-and-test.md)
in this repo. Both pipelines use the same SDK + ImageBuilder approach.

See also: [lime-packages CI: hardware tests](lime-packages-test-flow.md).
