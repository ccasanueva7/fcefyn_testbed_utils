# PC Ethernet addressing for U-Boot TFTP recovery (Belkin RT3200 / Linksys E8450)

When recovering a **MediaTek MT7622** unit (Belkin RT3200, Linksys E8450) from U-Boot over **TFTP**, the stock menu often assumes:

- **DUT:** `ipaddr` ≈ `192.168.1.1`
- **TFTP server:** `serverip` ≈ `192.168.1.254`

If the PC connected **directly** to the router has another address on that cable (for example `192.168.0.5/24`), U-Boot sends ARP for `192.168.1.254` and **no host answers**. The console shows **`ARP Retry count exceeded`** and TFTP never starts.

If the console shows **`TFTP from server 192.168.200.1`** while **`our IP address is 192.168.1.1`**, `serverip` is **stale from lab mesh** (`TFTP_SERVER_IP` / VLAN 200). Your PC is on **`192.168.1.254`**, not `192.168.200.1`. In U-Boot run **`setenv serverip 192.168.1.254`**, then **`ping 192.168.1.254`**, then retry TFTP. Avoid **`saveenv`** until you intend to persist values.

Full OKD / menu procedure: [Kiss of Death (OKD) on Belkin RT3200](../configuracion/duts-config.md#kiss-of-death-okd-on-belkin-rt3200--linksys-e8450).

---

## 1. Pick the Ethernet interface

Use the interface that has the **cable to the DUT** (not Wi‑Fi, not ZeroTier):

```bash
ip -br link
```

Typical names: `enp0s25`, `enx…` (USB Ethernet), `eth0`.

Set a shell variable so the commands below stay generic:

```bash
export ETH=enx7cc2c6338d1d   # example: replace with your interface name
```

---

## 2. Assign `192.168.1.254/24` on that interface

**Flush old addresses first** so no stale `192.168.0.x` (or DHCP lease) stays on the link and confuses routing or your own expectations:

```bash
sudo ip addr flush dev "$ETH"
sudo ip addr add 192.168.1.254/24 dev "$ETH"
sudo ip link set "$ETH" up
```

Check:

```bash
ip a show "$ETH"
ip -br link show "$ETH"
```

You should see **`inet 192.168.1.254/24`** on that interface **and** a **live Ethernet link**.

### NO-CARRIER: same ARP error even with `192.168.1.254`

If `ip a` shows **`NO-CARRIER`** and **`state DOWN`** on `$ETH`, the NIC has **no physical link**. ARP and TFTP **cannot** work until the cable negotiates (the PC is not “on the wire” with the router).

```text
5: enx…: <NO-CARRIER,BROADCAST,MULTICAST,UP> … state DOWN
```

**Fix (physical layer first):**

1. **Router powered on** before or right after plugging the cable.
2. **Cable** seated on both ends; try **another cable** if unsure.
3. **Port on the router:** recovery docs often use **LAN1**; if there is no link, try the **other** Ethernet port (some boards only bring up one PHY in U-Boot).
4. **USB Ethernet dongle:** unplug/replug; try another USB port; confirm the adapter’s LED blinks with link.
5. Re-check until **`ip -br link`** shows **`UP`** and **`LOWER_UP`** (no `NO-CARRIER`), e.g.:

```bash
ip -br link show "$ETH"
# expect: enx…  UP  (not NO-CARRIER / DOWN)
```

Only then use U-Boot **ping** / TFTP again.

Then run your **TFTP server** so it serves the file U-Boot requests (e.g. `openwrt-mediatek-mt7622-linksys_e8450-ubi-preloader.bin`) from the documented directory. OKD checklist (tftpd-hpa paths): [duts-config § OKD prerequisites](../configuracion/duts-config.md#prerequisites).

Optional check from U-Boot (serial): `ping 192.168.1.254` should succeed before TFTP.

---

## 3. Alternative: keep your PC IP, change U-Boot

If you prefer the PC on another address in `192.168.1.0/24` (e.g. `192.168.1.10`), configure that on `$ETH` and in U-Boot:

```text
setenv serverip 192.168.1.10
```

Use `saveenv` only if you intend to persist; for a one-off recovery you can omit it.

The DUT and PC must remain in the **same /24** as configured in U-Boot (`ipaddr` / `serverip`).

---

## 4. After recovery

Restore normal networking on the laptop (NetworkManager, DHCP, or remove the static address) so day‑to-day use is unchanged. A reboot clears transient `ip addr` changes unless you made them persistent in NM.

---

## Related

- [DUTs: Belkin / OKD](../configuracion/duts-config.md#kiss-of-death-okd-on-belkin-rt3200--linksys-e8450)
- [TFTP / dnsmasq on the lab host](../configuracion/tftp-server.md) (orchestration host, not this direct-recovery layout)
