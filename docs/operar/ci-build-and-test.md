# CI: Build & Test LibreMesh

This workflow builds a LibreMesh firmware image from source and runs automated
tests on a physical device in the FCEFYN lab.

It is triggered **manually** — it does not run automatically on every commit.
You decide when to run it and with which parameters.

---

## When to use it

Run this workflow when you want to:

- Test a specific version or branch of
  [lime-packages](https://github.com/libremesh/lime-packages) on real hardware
- Verify that a set of packages installs and boots correctly on a lab device
- Produce a firmware image with custom packages for a specific device

---

## How to run it

1. Go to the repository on GitHub
2. Click the **Actions** tab
3. Select **Build LibreMesh and Test on DUT** in the left panel
4. Click **Run workflow**
5. Fill in the inputs (see below) and click the green **Run workflow** button

---

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `duts` | yes | `belkin_rt3200` | Device(s) to build and test. Comma-separated. Use `all` for every lab device. |
| `lime_ref` | yes | `v2024.1` | Branch, tag, or commit SHA of lime-packages to build from. |
| `openwrt_version` | no | `23.05.5` | OpenWrt version to use. Must be compatible with `lime_ref`. |
| `extra_packages` | no | _(empty)_ | Space-separated packages to add or remove from the base set. Prefix with `-` to remove. Example: `luci-app-dawn -lime-proto-batadv` |
| `config_file` | no | _(empty)_ | Repo-relative path to a config file to inject as `/etc/config/<name>` in the firmware. Example: `firmware/configs/belkin_rt3200.conf` |

### Supported devices

| `duts` value | Hardware | OpenWrt target |
|---|---|---|
| `belkin_rt3200` | Belkin RT3200 / Linksys E8450 | `mediatek/mt7622` |
| `openwrt_one` | OpenWrt One | `mediatek/filogic` |
| `bananapi_r4` | Banana Pi R4 | `mediatek/filogic` |
| `librerouter` | LibreRouter v1 | `ath79/generic` |

### OpenWrt / lime-packages compatibility

| `openwrt_version` | Compatible `lime_ref` |
|---|---|
| `23.05.5` | `v2024.1` |
| `24.10.5` | `master` or newer tags |
| `25.12.0` | `master` or newer tags |

---

## What happens when you run it

The workflow has three jobs that run in sequence:

### 1. Resolve matrix (~5 seconds, GitHub-hosted)

Parses the `duts` input and builds a job matrix so each device runs in
parallel. For example, `"belkin_rt3200,librerouter"` becomes two independent
build jobs.

### 2. Build (~20–25 min per device, GitHub-hosted)

For each device, two Docker containers run back to back:

**Step 1 — OpenWrt SDK**
Downloads `ghcr.io/openwrt/sdk:<target>-<subtarget>-v<openwrt_version>` and
compiles the lime-packages listed below from source, using the exact git ref
you specified in `lime_ref`. This is the slow step.

Packages compiled:

- `lime-system`
- `lime-proto-babeld`
- `lime-proto-batadv`
- `lime-proto-anygw`
- `lime-hwd-openwrt-wan`
- `lime-app`
- `shared-state` + `shared-state-babeld_hosts` + `shared-state-bat_hosts` + `shared-state-nodes_and_links`
- `babeld-auto-gw-mode`
- anything you add via `extra_packages`

**Step 2 — OpenWrt ImageBuilder**
Downloads `ghcr.io/openwrt/imagebuilder:<target>-<subtarget>-v<openwrt_version>`
and assembles the compiled `.ipk` packages into a complete firmware image
(`.bin` or `.itb`). This step takes ~2–3 minutes.

The firmware is uploaded as a GitHub Actions artifact named
`firmware-<dut>-<lime_ref>-<short_sha>` and kept for 7 days.

### 3. Flash and test (lab self-hosted runner, `testbed-fcefyn`)

Runs on the physical T430 machine in the FCEFYN lab.

1. Downloads the firmware artifact from step 2
2. Reserves the target device via [labgrid](https://labgrid.readthedocs.io)
   (waits if the device is busy)
3. Loads the firmware onto the device
4. Runs the [libremesh-tests](https://github.com/fcefyn-testbed/libremesh-tests)
   test suite with pytest
5. Releases the device when done (even if tests fail)

---

## Examples

**Test the latest stable lime-packages on the Belkin RT3200:**
```
duts: belkin_rt3200
lime_ref: v2024.1
openwrt_version: 23.05.5
```

**Test a feature branch on all devices:**
```
duts: all
lime_ref: my-feature-branch
openwrt_version: 24.10.5
```

**Add a package and remove another:**
```
duts: belkin_rt3200
lime_ref: v2024.1
extra_packages: luci-app-dawn -lime-proto-batadv
```

**Inject a custom network config:**
```
duts: belkin_rt3200
lime_ref: v2024.1
config_file: firmware/configs/belkin_rt3200.conf
```

---

## Testing the build locally with `act`

[act](https://github.com/nektos/act) lets you run the build job on your own
machine without pushing to GitHub. Only the `build` job works locally — the
`flash_and_test` job requires physical lab hardware and is automatically
skipped.

```bash
act workflow_dispatch \
  --workflows .github/workflows/build-and-test-libremesh.yml \
  --job build \
  --input duts="belkin_rt3200" \
  --input lime_ref="v2024.1" \
  --input openwrt_version="23.05.5" \
  --input config_file="" \
  --input extra_packages="" \
  -P ubuntu-latest=catthehacker/ubuntu:act-22.04 \
  --artifact-server-path /tmp/act-artifacts
```

The firmware is saved to `/tmp/act-artifacts` and to `./images/` in the repo
root (not committed).
