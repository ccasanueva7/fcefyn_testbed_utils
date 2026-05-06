# Onboarding to openwrt-tests

Process for contributing hardware from a local lab to the [openwrt-tests](https://github.com/aparcar/openwrt-tests) ecosystem. Covers architecture, exporter connection, access management, Ansible, and the step sequence to integrate DUTs with the upstream coordinator.

!!! info "Two contribution paths"
    This page focuses on the base openwrt-tests lab (Scenario A). For contributing a **libremesh-capable** lab (own self-hosted runner, managed switch with VLAN switching, multi-node mesh suite), see [Contributing a new lab](new-lab-contribution.md) which contrasts both paths.

---

## 1. Global-coordinator architecture

The openwrt-tests **global-coordinator** is a **VM in a datacenter** with a public IP, maintained by Paul (aparcar). All remote labs connect to it over **WireGuard**. **GitHub Actions self-hosted runners** also run on that VM and reach labs through the WireGuard tunnel to run tests.

```mermaid
flowchart TD
    subgraph datacenter ["Datacenter VM"]
        GC["labgrid-coordinator :20408"]
        RUNNERS["GitHub Actions runners"]
    end

    subgraph lab_aparcar ["Aparcar lab"]
        EXP_A["labgrid-exporter"]
        BC_A["labgrid-bound-connect"]
        DUT_A["DUTs"]
    end

    subgraph lab_fcefyn ["FCEFyN lab"]
        EXP_F["labgrid-exporter"]
        BC_F["labgrid-bound-connect"]
        DUT_F["DUTs"]
    end

    RUNNERS -- "1" --> GC
    EXP_A -- "2" --> GC
    EXP_F -- "2" --> GC
    RUNNERS -- "3" --> BC_A
    RUNNERS -- "3" --> BC_F
    BC_A -- "4" --> DUT_A
    BC_F -- "4" --> DUT_F
```

| # | Connection | Detail |
|---|---|---|
| 1 | Runners → Coordinator | gRPC localhost:20408 (reserve / lock / unlock) |
| 2 | Exporter → Coordinator | gRPC via WireGuard (register resources) |
| 3 | Runners → bound-connect | SSH via WireGuard (LG_PROXY=labgrid-X) |
| 4 | bound-connect → DUTs | socat with so-bindtodevice on correct VLAN interface |

All connections between labs and the VM traverse a **WireGuard** tunnel (point-to-point VPN).

| Component | Location | Role |
|-----------|----------|------|
| **Coordinator** | Datacenter VM (public IP) | gRPC server (port 20408). Registers places (`places.yaml`), coordinates reservations and locks. Does **not** proxy SSH. |
| **GitHub runners** | Same VM | Self-hosted runners executing CI workflow jobs against remote DUTs via `LG_PROXY`. |
| **WireGuard** | Between each lab and the VM | Tunnel so runners can SSH to lab hosts and lab exporters can reach the coordinator. |
| **Exporter** | Lab host | Registers local DUT resources (serial, power, network) with the coordinator over gRPC. |
| **`labgrid-bound-connect`** | Lab host | SSH ProxyCommand invoked by the runner. Uses `socat` with `so-bindtodevice` to connect to a DUT IP on the correct VLAN interface. |
| **Place** | Configuration | Abstraction of one DUT: resources (serial, power, SSH target), boot strategy, firmware. |

See [CI execution flow](openwrt-tests-ci-flow.md) for the full sequence of how a workflow job runs end-to-end.

!!! note "WireGuard latency"
    If the WireGuard link between the datacenter and the lab is poor (high latency), tests may fail on timeout. The maintainer cited this as a known issue with labs in Eastern Europe.

---

## 2. Exporter connection to the coordinator

The exporter initiates the connection *toward* the coordinator.

```bash
labgrid-exporter --coordinator <coordinator_host>:<port> /etc/labgrid/exporter.yaml
```

In practice the exporter runs as a systemd service (`labgrid-exporter.service`) and the coordinator is set in config or environment (`LG_COORDINATOR=<host>:<port>`, default `127.0.0.1:20408`). Since Labgrid 25.0 (May 2025) the transport is **gRPC**; previous versions used WebSocket/WAMP via crossbar.

**What you need from the upstream maintainer:**

- Coordinator address (host and gRPC port, typically `20408`).
- Coordinator SSH public key to add to `authorized_keys` for user `labgrid-dev` on the lab (already included in the openwrt-tests Ansible playbook).

**Firewalls / NAT:** The lab must be able to connect *outbound* to the coordinator (outgoing gRPC over TCP). The coordinator then uses SSH proxy over the same path to reach DUTs.

---

## 3. SSH access and proxy

When a developer or CI runs `labgrid-client console` or `labgrid-client ssh`, the flow is:

```
client → SSH to coordinator (jump host) → SSH to exporter → serial/SSH to DUT
```

The coordinator must SSH to the lab host. That is done with the coordinator public key in `authorized_keys` for user `labgrid-dev`.

### 3.1 Keys involved

| Key | Where it is configured | Purpose |
|-----|------------------------|---------|
| **Coordinator** public key | `~labgrid-dev/.ssh/authorized_keys` on the lab | Lets the coordinator SSH to the lab (proxy to DUTs). Deployed by Ansible. |
| Each **developer** public key | Fetched from `https://github.com/<username>.keys` at Ansible deploy time; users listed in `labnet.yaml` `maintainers` + `access` | Lets the developer reach lab DUTs via `LG_PROXY`. |
| Lab **WireGuard** public key | Manual exchange with maintainer | Establishes VPN tunnel between lab and coordinator. |

The coordinator key is already in the openwrt-tests Ansible playbook; it deploys when you run the playbook.

#### Developer access in `labnet.yaml`

Each developer who needs remote DUT access needs:

1. At least one **SSH public key** (ed25519) registered on their **GitHub profile** (Settings > SSH and GPG keys).
2. Their **GitHub username** listed in `access:` for the target lab in `labnet.yaml`.

The openwrt-tests Ansible playbook iterates the union of `maintainers` + `access` for each lab, fetches SSH keys from `https://github.com/<username>.keys`, and appends them to `~labgrid-dev/.ssh/authorized_keys` on the lab host. Each developer can then SSH as `labgrid-dev` to use `labgrid-client`. Key rotation on GitHub takes effect on the next Ansible run.

---

## 4. Ansible: control node and managed node

| Role | In upstream openwrt-tests |
|------|---------------------------|
| **Control node** | Maintainer machine (Paul/Aparcar) that runs `ansible-playbook`. |
| **Managed node** | The lab host (the Lenovo in our case). |

For the upstream maintainer to apply the playbook to the FCEFyN lab:

1. **SSH to the lab host** (access as `labgrid-dev` or inventory user).
2. **Control node public key** in `authorized_keys` on the managed node.

This is coordinated manually: the maintainer shares their public key and the lab owner adds it to `authorized_keys`, or the lab owner runs the playbook locally (if they have inventory access).

---

## 5. PR contents to contribute hardware

A PR to openwrt-tests to add a new lab includes:

| File | Description |
|------|-------------|
| `labnet.yaml` | Lab entry under `labs:`, devices, instances, `maintainers`, `access` (GitHub usernames). |
| `ansible/files/exporter/<lab>/exporter.yaml` | Exporter config: places with resources (serial, power, SSH target). |
| `ansible/files/exporter/<lab>/netplan.yaml` | Host network config (VLANs). |
| `ansible/files/exporter/<lab>/dnsmasq.conf` | DHCP/TFTP for lab VLANs. |
| `ansible/files/exporter/<lab>/pdudaemon.conf` | PDUDaemon config (power control). |
| `docs/labs/<lab>.md` | Lab documentation: hardware, DUTs, maintainers. |

### 5.1 Access lists in labnet.yaml

Each lab defines two lists of GitHub usernames (without `@` prefix):

- **`maintainers:`** - notified via `@username` mentions in healthcheck issues.
- **`access:`** - SSH access to the lab host (keys fetched from GitHub).

Include the upstream maintainer (`aparcar`) in `access:` so they can debug.

```yaml
labs:
  labgrid-fcefyn:
    maintainers:
      - francoriba
      - ccasanueva7
      - javierbrk
    access:
      - francoriba
      - aparcar         # upstream maintainer (debugging)
```

No `sshkey` field is needed. Ansible fetches keys from `https://github.com/<username>.keys` at deploy time.

### 5.2 Register GitHub username for a new developer {: #52-register-github-username }

1. Ensure the developer has at least one ed25519 SSH key on their GitHub profile (**Settings > SSH and GPG keys**).
2. Add their GitHub username to `access:` in the target lab entry in `labnet.yaml`.
3. Open a PR to openwrt-tests.

To use multiple PCs, add all SSH keys to the GitHub profile. One `labnet.yaml` entry covers all keys for the same developer. Key rotation on GitHub takes effect on the next Ansible run.

!!! warning "Do not confuse with host keys"
    Orchestration host keys (`/etc/wireguard/public.key`, keys in `~labgrid-dev/.ssh/`) serve other purposes. `labnet.yaml` `access:` lists only contain **GitHub usernames** of people who will run `labgrid-client` from their machines.

---

## 6. Onboarding sequence

Suggested order: first the **WireGuard** tunnel (the coordinator VM must register the lab peer; without the tunnel there is no return SSH from the VM). In parallel prepare the **PR** with inventory, exporter, and `access` usernames ([5.2](#52-register-github-username)). After merge, the openwrt-tests **playbook_labgrid** fetches SSH keys from GitHub and deploys `authorized_keys` and services on the host.

```mermaid
sequenceDiagram
    participant Lab as Lab_owner_host
    participant Maint as Upstream_maintainer
    participant DC as VM_coordinator_runners
    participant PR as PR_openwrt_tests

    Lab->>Lab: WireGuard keypair on lab host
    Lab->>Maint: WireGuard public key
    Maint->>Lab: Peer config IP endpoint server pubkey
    Maint->>DC: Register lab peer on WireGuard server
    Lab->>Lab: Deploy wg0 Ansible wireguard or manual
    Lab->>DC: WireGuard tunnel active handshake
    Lab->>Lab: Register GitHub usernames in access section_5_2
    Lab->>PR: PR labnet maintainers access exporter netplan dnsmasq pdu docs
    Maint->>PR: Review and merge
    Maint->>Lab: Coordinator gRPC address if needed
    Lab->>Lab: playbook_labgrid openwrt_tests authorized_keys exporter
    Lab->>DC: Outbound exporter gRPC
    DC->>Lab: SSH to lab via tunnel proxy DUTs
    DC->>DC: Places registered CI runners on VM
```

### 6.1 Checklist

* ~~Generate WireGuard keypair on the lab host and send the public key to the maintainer (Matrix)~~ **Done**
* ~~Receive WireGuard config from the maintainer (assigned IP, endpoint, server public key)~~ **Done** - IP `10.0.0.10/24`, endpoint `195.37.88.188:51820`
* ~~Apply tunnel on the host: Ansible role `wireguard` in `fcefyn_testbed_utils`~~ **Done** - see [section 9](#wireguard-ansible-fcefyn)
* ~~Verify tunnel: `sudo wg show wg0` (recent handshake)~~ **Done**
* Per developer: ensure ed25519 key is on their GitHub profile and add GitHub username to `labs.<lab>.access` in `labnet.yaml` ([5.2](#52-register-github-username))
* Prepare lab files: `exporter.yaml`, `netplan.yaml`, `dnsmasq.conf`, `pdudaemon.conf`
* Document the lab in `docs/labs/<lab>.md` (upstream)
* Open PR to openwrt-tests with the above
* After merge: run `playbook_labgrid.yml` from openwrt-tests on the host (or have the maintainer run it): coordinator SSH key ends up in `~labgrid-dev/.ssh/authorized_keys` and exporter is configured
* Confirm `labgrid-exporter` points at the coordinator gRPC address (`LG_COORDINATOR=<host>:20408`)
* Verify places: `labgrid-client places` (with `LG_PROXY` per upstream README)

---

## 7. Maintainer coordination

| What you need | How to get it |
|---------------|---------------|
| WireGuard config (IP, endpoint, peer key) | Send lab WireGuard public key to the maintainer; receive data back. |
| Coordinator URL | Ask the maintainer or see project docs. |
| Coordinator SSH key | Already in Ansible playbook; deploys when applied. Alternatively the maintainer provides it. |
| Ansible access to lab | Lab owner gives SSH to the maintainer (Ansible control node public key), or runs the playbook locally. |
| VLAN configuration | Defined by the lab owner for their hardware; files go in the PR. |

---

## 8. Differences from libremesh-tests

| Aspect | openwrt-tests (upstream) | libremesh-tests (fork) |
|--------|--------------------------|------------------------|
| Coordinator | Global (datacenter VM) | Same global coordinator |
| CI runner | aparcar runners (datacenter VM) | Self-hosted runner per lab (e.g. `testbed-fcefyn`) |
| Ansible control node | Aparcar infrastructure | The lab itself (self-setup) |
| Managed switch | Optional | Required |
| VLANs | Dynamic per test (isolated default, 192.168.1.x) | Dynamic per test (mesh VLAN 200, 10.13.x.x for multi-node) |
| Multi-node tests | Not supported | Implemented in `conftest_mesh.py` |

Both projects use the **same Labgrid inventory** ([Lab architecture](lab-architecture.md)): each test locks DUTs via Labgrid and sets the VLAN it needs at runtime.

For a full side-by-side contribution walkthrough (which steps are shared, which are Scenario-B-only), see [Contributing a new lab](new-lab-contribution.md).

---

## 9. WireGuard in Ansible (fcefyn_testbed_utils) {: #wireguard-ansible-fcefyn }

Role in `fcefyn_testbed_utils` to bring up the lab host tunnel toward the **global-coordinator**. It does not replace key exchange with the upstream maintainer: it only automates install, `wg0.conf`, and systemd on Debian/Ubuntu.

| Item | Location |
|------|----------|
| Role | `ansible/roles/wireguard/` |
| Playbook that uses it | `ansible/playbook_testbed.yml` (comments and tag `wireguard`) |
| Variables | `ansible/roles/wireguard/defaults/main.yml` |
| Template | `ansible/roles/wireguard/templates/wg0.conf.j2` |
| Service | `wg-quick@wg0` (enabled and started by the role) |

Variables in `defaults/main.yml` hold the coordinator peer values (public key, endpoint, assigned IP `10.0.0.10/24`). The **private** key does not go in the repo: the role generates it on the host if missing (`/etc/wireguard/private.key`) and prints the public key in Ansible output to share with the maintainer.

**Run** (from `ansible/` directory):

```bash
ansible-playbook playbook_testbed.yml --tags wireguard -K
```

---
