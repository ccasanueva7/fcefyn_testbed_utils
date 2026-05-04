# Manual firmware build

Quick guide to build firmware images for use in the lab (`LG_IMAGE`, TFTP, flash). The same DUT profiles apply whether the stack is **vanilla OpenWrt**, **LibreMesh**, or **LibreRouter OS**.

---

## Build config per DUT

Pick **Target System**, **Subtarget**, and **Target Profile** in `make menuconfig` from this table (or the device vendor docs).

| DUT | Arch | Subtarget | Profile |
|-----|------|-----------|---------|
| Belkin RT3200 | Mediatek (ARM) | mt7622 | linksys_e8450-ubi |
| Banana Pi R4 | Mediatek (ARM) | filogic | bananapi_bpi-r4 |
| OpenWRT One | Mediatek (ARM) | filogic | openwrt_one |
| LibreRouter 1 | ath79 (MIPS 24Kc) | generic | librerouter_librerouter-v1 |
| Gateway TL-WDR3500 | ath79 (MIPS 74Kc) | generic | tplink_tl-wdr3500-v1 |
| **QEMU x86-64** | x86 | x86_64 | generic |
| **QEMU Malta BE** | malta | be | generic |
| **QEMU armsr-armv8** | armsr | armv8 | generic |

**Path in menuconfig:** Target System → (Arch) → Subtarget → Target Profile → (Profile).

---

## 1. Vanilla OpenWrt

Use when tests or workflows expect **stock OpenWrt** packages only (no `lime-*`, no LibreRouterOS bundle).

1. **Clone** OpenWrt (pin a release branch or tag, e.g. `v23.05.5`):

   ```bash
   git clone -b v23.05.5 --single-branch https://git.openwrt.org/openwrt/openwrt.git
   cd openwrt
   ```

2. **Feeds** (defaults only):

   ```bash
   ./scripts/feeds update -a
   ./scripts/feeds install -a
   ```

3. **Configure** target and profile: `make menuconfig` using the [table above](#build-config-per-dut). Add any extra packages the suite requires.

4. **Build:**

   ```bash
   make -j$(nproc)
   ```

Artifacts: `bin/targets/<target>/<subtarget>/`.

**References:** [OpenWrt build system](https://openwrt.org/docs/guide-developer/build-system/use-buildsystem), [install build dependencies](https://openwrt.org/docs/guide-developer/build-system/install-buildsystem).

---

## 2. LibreMesh (lime-packages)

Use for **community mesh** images: add the LibreMesh feeds and select `lime-*` packages (as required by the test suite or [libremesh-tests](https://github.com/fcefyn-testbed/libremesh-tests)).

**1. Clone OpenWrt and enter build root**

```bash
git clone -b v23.05.5 --single-branch https://git.openwrt.org/openwrt/openwrt.git
cd openwrt
```

**2. Feeds - OpenWrt default + LibreMesh**

```bash
cp feeds.conf.default feeds.conf
cat << 'EOF' >> feeds.conf

src-git libremesh https://github.com/libremesh/lime-packages.git;v2024.1
src-git profiles https://github.com/libremesh/network-profiles.git
EOF
```

`v2024.1` matches OpenWrt 23.05.5. Using `master` without a tag typically tracks OpenWrt 24.10+.

**3. Update and install packages**

```bash
./scripts/feeds update -a
./scripts/feeds install -a
```

**4. `make menuconfig` - Deselect**

| Location | Action |
|----------|--------|
| Image configuration → Separate feed repositories → Enable feed **libremesh** | Deselect |
| Image configuration → Separate feed repositories → Enable feed **profiles** | Deselect |
| Base system → **dnsmasq** | Deselect |
| Network → **odhcpd-ipv6only** | Deselect |

**5. `make menuconfig` - Select LibreMesh (example set)**

| Location |
|----------|
| LibreMesh → **babeld-auto-gw-mode** |
| LibreMesh → Offline Documentation → **lime-docs-minimal** |
| LibreMesh → **lime-app** |
| LibreMesh → **lime-hwd-openwrt-wan** |
| LibreMesh → **lime-proto-anygw** |
| LibreMesh → **lime-proto-babeld** |
| LibreMesh → **lime-proto-batadv** |
| LibreMesh → **shared-state** → shared-state-babeld_hosts |
| LibreMesh → **shared-state** → shared-state-bat_hosts |
| LibreMesh → **shared-state** → shared-state-nodes_and_links |

Set **Target System / Profile** from the [DUT table](#build-config-per-dut).

**5.1 Virtual targets with vwifi (optional)**

For mesh tests in QEMU (x86-64, Malta, armsr-armv8) with virtual WiFi:

| Step | Action |
|------|--------|
| Feeds | Add to `feeds.conf`: `src-git vwifi https://github.com/javierbrk/vwifi_cli_package` |
| Update | `./scripts/feeds update vwifi && ./scripts/feeds install -a` |
| Menuconfig | Network → **vwifi** |
| wpad | Include **wpad-basic-mbedtls** (needed for batman on vwifi) |

**6. Build**

```bash
make -j$(nproc)
```

Output layout: `bin/targets/.../`.  
Upstream: [libremesh.org development](https://libremesh.org/development.html).

---

## 3. LibreRouter OS

[LibreRouterOS](https://gitlab.com/librerouter/librerouteros) is also an OpenWrt-based tree with feeds and defaults oriented to **LibreRouter** hardware with LibreMesh networking capabilities. Prebuilt images: [GitLab releases](https://gitlab.com/librerouter/librerouteros/-/releases).

**Dependencies:** Same base toolchain as OpenWrt ([install packages](https://openwrt.org/docs/guide-developer/build-system/install-buildsystem) for your distro).

**Build steps (from upstream README)**

1. Clone and enter the repo:

   ```bash
   git clone https://gitlab.com/librerouter/librerouteros.git
   cd librerouteros
   ```

   Use a **tag or branch** that matches the release you need (e.g. check [branches / tags](https://gitlab.com/librerouter/librerouteros/-/tags) on GitLab).

2. Feeds:

   ```bash
   ./scripts/feeds update -a
   ./scripts/feeds install -a
   ```

3. Default configuration:

   ```bash
   cp configs/default_config .config
   ```

4. **Non-LibreRouter board:** apply the vendor patch so cmdline defaults match generic hardware:

   ```bash
   patch -p1 < configs/revert-cmdline-config.patch
   ```

5. Optional: `make menuconfig` to change target profile (see [DUT table](#build-config-per-dut) for lab devices) or packages.

6. Build:

   ```bash
   make -j$(nproc)
   ```

Firmware appears under `bin/` as in standard OpenWrt.

---

## Automatic builds via PR (lime-packages fork)

The **fcefyn-testbed/lime-packages** fork includes `.github/workflows/build-firmware.yml`: on pull requests (and manual dispatch), GitHub Actions builds a **local lime_packages feed** with the OpenWrt SDK, then one **firmware image per row** in `.github/ci/targets.yml` using ImageBuilder. Successful runs upload **`firmware-<device>.*`** and **`lime-feed-<arch>`** artifacts.

For architecture, caching, and feed indexing details, see:

- [lime-packages CI: firmware build](../diseno/lime-packages-ci-flow.md)
- [lime-packages CI: hardware tests](../diseno/lime-packages-test-flow.md) (downstream **libremesh-tests** on the `testbed-fcefyn` self-hosted runner)

Manual procedures above still apply when you build outside CI or need a custom `menuconfig` / full Buildroot tree.

For the automated CI workflow that builds and tests firmware directly in this repo, see [CI: Build & Test](ci-build-and-test.md).
