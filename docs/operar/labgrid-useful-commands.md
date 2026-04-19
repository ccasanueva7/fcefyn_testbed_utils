# Labgrid useful commands

Copy-paste `labgrid-client` usage for the **labgrid-fcefyn** coordinator. Place names and exporter layout live in **libremesh-tests** (`ansible/files/exporter/labgrid-fcefyn/exporter.yaml`). Ansible deployment: [Ansible and Labgrid](../configuracion/ansible-labgrid.md). SSH to DUTs: [SSH access to DUTs](dut-ssh-access.md).

---

## Runtime context

| Context | `LG_PROXY` | Typical use |
|---------|------------|-------------|
| On the **lab host** (or SSH session to it) | **Unset** | `who`, `places`, manual `unlock` (talks to local coordinator). |
| **CI runner** or laptop via SSH jump | `ssh://labgrid-fcefyn` (or `labs.<lab>.proxy` from [openwrt-tests labnet.yaml](https://github.com/aparcar/openwrt-tests/blob/main/labnet.yaml)) | `reserve`, pytest, workflows that expect the remote proxy. |

For `who` / `places` / freeing stuck places, run on the host **without** `LG_PROXY` so the client hits the coordinator directly.

---

## Coordinator inspection

| Command | Purpose |
|---------|---------|
| `labgrid-client who` | Which user holds which place (acquired / reserved). |
| `labgrid-client -v places` | Verbose place list; shows **acquired** and owner (`labgrid-fcefyn/user`). |
| `labgrid-client places` | Short place list. |

---

## Places (labgrid-fcefyn)

Top-level keys in `exporter.yaml` (use as `-p` argument):

| Place name |
|------------|
| `labgrid-fcefyn-belkin_rt3200_1` |
| `labgrid-fcefyn-belkin_rt3200_2` |
| `labgrid-fcefyn-belkin_rt3200_3` |
| `labgrid-fcefyn-bananapi_bpi-r4` |
| `labgrid-fcefyn-openwrt_one` |
| `labgrid-fcefyn-librerouter_1` |

---

## Lock and unlock a place

Same verbs as [libremesh-tests workflows](https://github.com/fcefyn-testbed/libremesh-tests/tree/main/.github/workflows) (`lock` after reserve token, `unlock` in `always`).

```bash
labgrid-client -p labgrid-fcefyn-bananapi_bpi-r4 lock
labgrid-client -p labgrid-fcefyn-bananapi_bpi-r4 unlock
```

Unlock every stuck place after a crashed session or aborted manual test:

```bash
for p in \
  labgrid-fcefyn-belkin_rt3200_1 \
  labgrid-fcefyn-belkin_rt3200_2 \
  labgrid-fcefyn-belkin_rt3200_3 \
  labgrid-fcefyn-bananapi_bpi-r4 \
  labgrid-fcefyn-openwrt_one \
  labgrid-fcefyn-librerouter_1
do
  labgrid-client -p "$p" unlock
done
```

**Symptom:** `reserve` stays in *waiting* / `matches nothing` in CI. **Cause:** all matching places are **locked** by someone. Coordinator only assigns free places. **Fix:** `unlock` as above (or identify the holder with `who`), then re-run the job.

---

## Release between test runs (host or dev laptop)

After a **crashed pytest**, an **aborted mesh run**, or before the **next** manual/CI run, places can stay **acquired** or locked by the previous session. Run **`release`** (same as `unlock`) on the **lab host** (coordinator local, `LG_PROXY` unset; see [Runtime context](#runtime-context)) or from a **developer machine** with `LG_PROXY` set if that machine has coordinator access to the same lab.

**`-k` / `--kick`:** releases the place **even if another user** currently holds it. Use when the holder is stale (dead SSH, killed pytest). On a **shared** lab, coordinate before kicking someone else's session.

Examples for two common mesh nodes:

```bash
labgrid-client -p labgrid-fcefyn-openwrt_one release -k
labgrid-client -p labgrid-fcefyn-librerouter_1 release -k
```

To clear **every** listed place in one go (same pattern as the unlock loop above):

```bash
for p in \
  labgrid-fcefyn-belkin_rt3200_1 \
  labgrid-fcefyn-belkin_rt3200_2 \
  labgrid-fcefyn-belkin_rt3200_3 \
  labgrid-fcefyn-bananapi_bpi-r4 \
  labgrid-fcefyn-openwrt_one \
  labgrid-fcefyn-librerouter_1
do
  labgrid-client -p "$p" release -k
done
```

---

## Reservations (CI and manual)

Typical split used in workflows (some forks return the reservation token before allocation is final):

```bash
labgrid-client reserve --shell '<filter>'   # e.g. device=bananapi_bpi-r4
labgrid-client wait '<token>'
```

Adjust filters to match [places/resources](https://labgrid.readthedocs.io/) in the suite.

---

## Stuck GitHub Actions `labgrid-client wait`

If canceling the workflow does not stop the job, on the **runner** host:

```bash
pkill -9 -f "labgrid-client wait"
```

Then **unlock** any orphaned places from the lab host (see loop above).

---

## Host services look broken after reboot

If SSH to DUTs times out while ping works, coordinator/exporter/config may be stale. Redeploy Labgrid stack on the host:

```bash
ansible-playbook playbook_labgrid.yml -l labgrid-fcefyn
```

(Playbook path and inventory as in [ansible-labgrid](../configuracion/ansible-labgrid.md).)

VLAN or switch issues are outside `labgrid-client`; see [Routine operations - DUTs and VLANs](lab-routine-operations.md#duts-and-vlans) and [switch-config](../configuracion/switch-config.md).
