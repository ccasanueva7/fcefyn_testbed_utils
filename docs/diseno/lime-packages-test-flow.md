# lime-packages CI: hardware test stage

How **fcefyn-testbed/lime-packages** consumes the firmware artifacts
produced by `build-image` and exercises them on the self-hosted lab
runner (`testbed-fcefyn`) and on QEMU. Single source of truth:
[build-firmware.yml][wf].

Build pipeline overview:
[lime-packages CI: firmware build](lime-packages-ci-flow.md).

[wf]: https://github.com/fcefyn-testbed/lime-packages/blob/master/.github/workflows/build-firmware.yml

---

## 0. Two-repo model: workflow vs. tests

The test infrastructure is deliberately split across two repositories:

| Repo | What it owns |
|------|-------------|
| `fcefyn-testbed/lime-packages` | The CI workflow (`.github/workflows/build-firmware.yml`), the build scripts, and the matrix config. This is the fork of `libremesh/lime-packages`. |
| `fcefyn-testbed/libremesh-tests` | The pytest test suite (`tests/test_libremesh.py`, `test_mesh.py`, etc.), labgrid environment files (`targets/<device>.yaml`), and the `uv` project that pins test dependencies. |

The workflow checks out `libremesh-tests@staging` during each test
job and calls `uv run pytest` from there. No test code lives inside
`lime-packages` itself.

### Why the split?

`libremesh-tests` can be used independently:

- Local runs against any firmware (pre-built or downloaded) without
  going through the CI workflow.
- Future reuse by other forks of `lime-packages` (or the upstream
  `libremesh/lime-packages`) with zero changes to the test code.
- Allows separate versioning - test improvements land in
  `libremesh-tests` without touching `lime-packages`.

### Repo ownership requirements

For the CI workflow in `lime-packages` to access `libremesh-tests`,
the self-hosted runner must be able to check out both repos. Two
layouts work:

**Option A: same GitHub organisation (current setup)**

Both repos live in `fcefyn-testbed`. The runner is registered at the
organisation level (`Settings > Actions > Runners`), so it can
service workflows from any repo in the org.

```
fcefyn-testbed/lime-packages   <- workflow here
fcefyn-testbed/libremesh-tests <- checked out by the workflow
```

The `actions/checkout` step in the workflow uses
`repository: fcefyn-testbed/libremesh-tests` - this is a public
repo, so no `token:` override is needed.

**Option B: different organisations (future: upstream contribution)**

The upstream `libremesh/lime-packages` workflow can still check out
`fcefyn-testbed/libremesh-tests` (public repo, no auth needed):

```yaml
- uses: actions/checkout@v6
  with:
    repository: fcefyn-testbed/libremesh-tests
    ref: staging
    path: libremesh-tests
```

The runner, however, must be registered in the `libremesh` org (or in
the specific `libremesh/lime-packages` repo) for the workflow to be
eligible for self-hosted execution. The lab runner registration is the
only thing that needs to change when contributing upstream - the
`libremesh-tests` checkout line stays the same as long as the test
repo remains public.

**When `libremesh` eventually merges this CI approach,** the expected
final state is:

- Runner registered in `libremesh` org.
- Workflow in `libremesh/lime-packages` checks out
  `libremesh/libremesh-tests` (a fork/equivalent living in the same
  upstream org).
- `fcefyn-testbed/lime-packages` goes back to tracking upstream with
  only testbed-specific device entries in `targets.yml`.

### Pinned branch (`staging`)

The workflow always checks out `libremesh-tests@staging`. This is the
integration branch where reviewed test improvements land before going
to `main`. Using a named branch (not a SHA) means test fixes propagate
automatically to the next CI run without a `lime-packages` PR.

---

## 1. Trigger matrix

| Trigger                  | `test-firmware` | `test-mesh` | `test-mesh-pairs` | `test-firmware-qemu` | `test-mesh-qemu` |
|--------------------------|-----------------|-------------|-------------------|----------------------|-------------------|
| `pull_request`           | 1 random place  | forced N=3  | skipped           | run                  | run               |
| `workflow_dispatch` (`physical_single=true`) | every place    | per `physical_mesh_count` (0/2/3) | skipped | run                  | run               |
| `schedule` (cron 06:00 UTC) | every place  | skipped     | 3 walking pairs   | run                  | run               |

Notes:

- All jobs that touch the lab use `environment: physical-lab` for
  GitHub-side approval gating. One environment approval covers every
  `physical-lab`-bound job in the run (i.e. one click per PR).
- The workflow concurrency group `physical-lab-shared` makes sure that
  no two lab-bound triggers run at once.
- Fork PRs (no environment access) get the QEMU jobs only.

The `prepare-matrix` job downsamples `test_targets_matrix` to one
random entry on `pull_request` so PRs do not block the lab on every
device.

---

## 2. End-to-end flow

```mermaid
flowchart LR
  A[firmware-* artifacts] --> B[download-artifact on testbed-fcefyn]
  B --> C[Stage under /srv/tftp/firmwares/ci/RUN_ID/]
  C --> D[labgrid lock]
  D --> E[pytest libremesh-tests]
  E --> F[upload test-results-*]
```

| Step      | What happens                                                      |
|-----------|-------------------------------------------------------------------|
| Artifacts | `build-image` uploads `firmware-<device>-<release>` per matrix.   |
| Checkout  | `libremesh-tests@staging`, `aparcar/openwrt-tests@main`.          |
| Staging   | Firmware copied to `/srv/tftp/firmwares/ci/<run_id>/<place>/<release>/` (single-node), `.../mesh/<release>/`, or `.../mesh-pairs/<pair>/<release>/`. Per-job staging dirs avoid races. |
| Single    | Per place: lock `labgrid-fcefyn-<place>`, set `LG_IMAGE`, run `pytest tests/test_libremesh.py`. |
| Mesh      | `test-mesh`: stage every device the mesh shape needs, set `LG_MESH_PLACES` + `LG_IMAGE_MAP`, run `pytest tests/test_mesh.py`. |
| Pairs     | `test-mesh-pairs` (cron only): three sequential 2-node pairs, `max-parallel: 1`. Covers every active lab device twice per day. |

Each step is implemented in [tools/ci/lab_stage_firmware.sh][stage-fw]
and [tools/ci/lab_stage_mesh.sh][stage-mesh]; the workflow steps
themselves are 2-3 lines plus env vars.

[stage-fw]: https://github.com/fcefyn-testbed/lime-packages/blob/master/tools/ci/lab_stage_firmware.sh
[stage-mesh]: https://github.com/fcefyn-testbed/lime-packages/blob/master/tools/ci/lab_stage_mesh.sh

---

## 3. Mesh-after-firmware serialisation

`test-mesh` and `test-mesh-pairs` declare `needs: [..., test-firmware]`
so they cannot start while a `test-firmware` job is holding a labgrid
lock on the same place. Without this, both jobs race for the same lock
and one fails with `You have already acquired this place`.

The QEMU jobs run in parallel with the lab jobs since they do not
share lab resources.

---

## 4. PR strategy

```mermaid
flowchart LR
  PR[Pull request] --> PM[prepare-matrix downsample]
  PM -->|1 random place| TF[test-firmware]
  PM -->|forced N=3| TM[test-mesh]
  PR --> TQ[test-firmware-qemu + test-mesh-qemu]
```

- One random target from `test_targets_matrix` runs single-node
  (cheap representative coverage).
- `test-mesh` is forced to `physical_mesh_count=3` on PRs because
  `pull_request` cannot pass workflow inputs and N=3 is the most
  representative shape (3 different SoC families).
- The full sweep is reserved for the daily cron.

---

## 5. Walking-chain mesh (cron only)

Three sequential pairs run in `test-mesh-pairs` with `max-parallel: 1`:

| Pair | A                 | B                 |
|------|-------------------|-------------------|
| 1    | belkin_rt3200_2   | openwrt_one       |
| 2    | openwrt_one       | bananapi_bpi-r4   |
| 3    | bananapi_bpi-r4   | belkin_rt3200_3   |

Every active device is exercised twice per day with a different mesh
peer. `belkin_rt3200_1` is excluded (in repair) - re-include it by
adding it back to `mesh_pairs:` in `prepare_matrix.sh`.

---

## 6. QEMU coverage

| Job                  | Purpose                                                             |
|----------------------|---------------------------------------------------------------------|
| `test-firmware-qemu` | Single-node `qemu_x86_64` boot: `test_libremesh.py`, `test_base.py`, `test_lan.py`. |
| `test-mesh-qemu`     | Multi-node mesh on QEMU using `vwifi` (kmod-mac80211-hwsim with USR1 broadcast). |

Both run on GitHub-hosted runners with KVM. The
[tools/ci/enable_kvm.sh][kvm] step installs a udev rule that grants the
runner user `rw` on `/dev/kvm` (default permissions deny non-root
access). `udevadm trigger --name-match=kvm` is used so the rule applies
to the existing device node, not just future hot-plugs.

[kvm]: https://github.com/fcefyn-testbed/lime-packages/blob/master/tools/ci/enable_kvm.sh

---

## 7. Labgrid reservation contract

### Single-node

- **Lock:** `uv run labgrid-client -v -p labgrid-fcefyn-<place> lock`.
- **Unlock + power-off:** in an `if: always()` step,
  `labgrid-client -p $LG_PLACE power off` then `... unlock`. The `-p`
  flag is required: without it labgrid falls back to its empty default
  and refuses to act.
- **Teardown:** remove `/srv/tftp/firmwares/ci/<run_id>/<place>/<release>/`.

The three Belkin RT3200 units (`belkin_rt3200_1`/`_2`/`_3`) all run
the `linksys_e8450` artefact under per-place TFTP staging and per-place
labgrid locks - the lock keys on the place name, not the device.

Environment for pytest: `LG_PROXY=labgrid-fcefyn`,
`LG_PLACE=labgrid-fcefyn-<place>`, `LG_ENV=targets/<device>.yaml`,
`OPENWRT_TESTS_DIR=<aparcar/openwrt-tests checkout>`.

### Mesh

Mesh fixtures (`tests/conftest_mesh.py` in libremesh-tests) require:

- `LG_MESH_PLACES`: comma-separated place names.
- `LG_IMAGE_MAP`: `place1=/abs/path1,place2=/abs/path2`.

VLAN 200 / switch configuration is handled by `conftest_vlan` (lab host
SSH); set `VLAN_SWITCH_DISABLED=1` to skip it.

---

## 8. Debugging a failed run

1. Open the run on GitHub, find the failed `test-firmware*` or
   `test-mesh*` job.
2. Download `test-results-<device>` / `test-results-mesh-*`. Each
   bundle has `--lg-log` console output and `report.xml` (JUnit).
3. On the lab host, check coordinator/exporter, TFTP permissions under
   `/srv/tftp/firmwares/ci/`, and stale locks via `labgrid-client who`.
4. For QEMU jobs, the `qemu-*-logs` artifact contains the QEMU console
   plus pytest's `--lg-log`.

---

## 9. Runner prerequisites

The `testbed-fcefyn` runner must already run libremesh-tests
workflows: `uv` and `labgrid-client` on `PATH` (via `uv run`), write
access to `/srv/tftp/firmwares/`, reachability of `LG_PROXY`.
See [CI runner](../configuracion/ci-runner.md) and
[Running tests](../operar/lab-running-tests.md).

For a brand-new device that has not been onboarded yet, follow
[Adding a device](lime-packages-add-device.md).
