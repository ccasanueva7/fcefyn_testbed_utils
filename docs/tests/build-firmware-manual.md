# Build manual de firmware (OpenWrt / LibreMesh)

Guia para buildear imágenes para en el lab (`LG_IMAGE`, TFTP).

---

## Config de build por DUT

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

**Uso:** `make menuconfig` → Target System → (Arch) → Subtarget → (Subtarget) → Target Profile → (Profile).

### LibreMesh (lime-packages)

**1. Descargar OpenWrt y entrar al build root**

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

`v2024.1` = LibreMesh 2024.1 (compatible con OpenWrt 23.05.5). Sin sufijo se usa `master`, que requiere OpenWrt 24.10.

**3. Actualizar e instalar paquetes**

```bash
scripts/feeds update -a
scripts/feeds install -a
```

**4. `make menuconfig` - Deseleccionar**

| Ubicación | Acción |
|-----------|--------|
| Image configuration → Separate feed repositories → Enable feed **libremesh** | Deseleccionar |
| Image configuration → Separate feed repositories → Enable feed **profiles** | Deseleccionar |
| Base system → **dnsmasq** | Deseleccionar |
| Network → **odhcpd-ipv6only** | Deseleccionar |

**5. `make menuconfig` - Seleccionar LibreMesh**

| Ubicación |
|-----------|
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

**5.1 Targets virtuales con vwifi (opcional)**

Solo para tests mesh en QEMU (x86-64, Malta, armsr-armv8) que usan virtual wifi:

| Paso | Acción |
|------|--------|
| Feeds | Añadir a `feeds.conf`: `src-git vwifi https://github.com/javierbrk/vwifi_cli_package` |
| Actualizar | `scripts/feeds update vwifi && scripts/feeds install -a` |
| Menuconfig | Network → **vwifi** |
| wpad | Incluir **wpad-basic-mbedtls** en la imagen (sin él batman no ve interfaces en vwifi) |

**6. Compilar**

```bash
make -j$(nproc)
```

Binarios en `bin/targets/.../.../`.  
Fuente: [libremesh.org/development](https://libremesh.org/development.html)
