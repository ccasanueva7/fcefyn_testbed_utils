# GitHub Actions self-hosted runner

To run libremesh-tests workflows on the lab host, install a **GitHub Actions self-hosted runner**. Daily, Healthcheck, and Pull Request jobs run on this hardware instead of GitHub-hosted or third-party runners.

---

## 1. Requirements

- GitHub account/repo (e.g. `francoriba/libremesh-tests` or the relevant org).
- SSH access to the lab host.

---

## 2. Installation

1. Download the runner from [GitHub Actions Runner](https://github.com/actions/runner/releases) (Linux x64).

2. In the repo: **Settings** → **Actions** → **Runners** → **New self-hosted runner**. Copy the configure command.

3. On the lab host:

   ```bash
   mkdir -p ~/actions-runner && cd ~/actions-runner
   # Download the .tar.gz from the release, extract
   ./config.sh --url https://github.com/OWNER/REPO --token TOKEN
   ```

4. During setup:
   - **Runner name**: e.g. `runner-fcefyn` or `labgrid-fcefyn`
   - **Additional labels**: e.g. `testbed-fcefyn` (for `runs-on: [self-hosted, testbed-fcefyn]` in workflows)

5. Install and start the service:

   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

---

## 3. Verification

```bash
sudo systemctl status actions.runner.*
```

In GitHub, the runner should show **Idle** under **Settings** → **Actions** → **Runners**.

---

## 4. Permissions on /etc/labgrid

The Labgrid coordinator writes under `/etc/labgrid` (place/resource state). Wrong permissions cause `PermissionError` on save. The libremesh-tests playbook should create `/etc/labgrid` with `owner: labgrid-dev` and `group: labgrid-dev`. To fix manually:

```bash
sudo chown -R labgrid-dev:labgrid-dev /etc/labgrid
sudo systemctl restart labgrid-coordinator
```

---

## 5. Move runner to another repo

To move the runner from one repo to another (or user to org):

1. On host: `./config.sh remove --token TOKEN` (token from current repo/org UI).
2. In new repo/org: **New self-hosted runner** → copy the new command.
3. Run `./config.sh` with new URL and token.
4. `sudo ./svc.sh uninstall` then `sudo ./svc.sh install` + `sudo ./svc.sh start`.

---

## 6. Ownership transfer

When the repo transfers to an org, attached runners move with it. The systemd service name may still reference the old owner; this should not affect operation.

---

## 7. Setup performed (FCEFyN)

Summary of steps to bring the runner online on host labgrid-fcefyn:

1. **Runner install** under `~/actions-runner` per [section 2](#2-installation).
2. **Initial config:** Runner linked to fork (`francoriba/libremesh-tests`). Name: `runner-fcefyn`. Labels: `self-hosted`, `testbed-fcefyn`.
3. **systemd service:** Installed with `sudo ./svc.sh install`. Service name: `actions.runner.francoriba-libremesh-tests.runner-fcefyn.service`.
4. **Re-registration:** The runner was first installed on `libremesh-tests Private`. To attach it to the fork: `./config.sh remove --token TOKEN` (token from original repo UI), then `./config.sh` with fork URL, then `sudo ./svc.sh uninstall` + `sudo ./svc.sh install` + `sudo ./svc.sh start`.
5. **Permissions /etc/labgrid:** Coordinator failed with `PermissionError` writing `/etc/labgrid`. Fixed with `sudo chown -R labgrid-dev:labgrid-dev /etc/labgrid`. openwrt-tests playbook updated so "Create labgrid folder" uses `owner: labgrid-dev` and `group: labgrid-dev`.
6. **Verification:** Daily, Healthcheck, and Pull Request jobs run on the runner with `runs-on: [self-hosted, testbed-fcefyn]`. Tests validated with openwrt_one.
