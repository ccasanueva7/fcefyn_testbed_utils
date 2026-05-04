# Video demos

This section collects demo videos showing various operations on the testbed.

---

## Remote access to the HIL testbed

Demonstration of **administrator remote access** to the testbed, including the recovery and access path used to operate the lab infrastructure.

**Watch on YouTube:** [Demo Remote Access to HIL Testbed](https://www.youtube.com/watch?v=QeCQGfZZQgE)

<div class="video-embed">
  <iframe
    src="https://www.youtube.com/embed/QeCQGfZZQgE"
    title="Demo Remote Access to HIL Testbed"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    allowfullscreen
    loading="lazy"
    referrerpolicy="strict-origin-when-cross-origin"
  ></iframe>
</div>

---

## Developer remote access through Labgrid

In this demo we show the process that a LibreMesh or OpenWrt developer should follow in order to access devices in a remote lab and run tests. For this particular example, we run a multi-node mesh test suite through Labgrid.

**Watch on YouTube:** [Developer Remote Access through Labgrid](https://www.youtube.com/watch?v=RuzFpWzVGxI)

<div class="video-embed">
  <iframe
    src="https://www.youtube.com/embed/RuzFpWzVGxI"
    title="Developer Remote Access through Labgrid"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    allowfullscreen
    loading="lazy"
    referrerpolicy="strict-origin-when-cross-origin"
  ></iframe>
</div>

---

## LibreMesh CI/CD — from pull request to physical hardware

This demo shows the end-to-end CI/CD workflow for the
[libremesh-tests](https://github.com/fcefyn-testbed/libremesh-tests) repository,
illustrating how changes are validated automatically at two levels before and after merging.

**When a pull request is opened**, the `Pull Requests` workflow triggers and runs the test
suite in parallel against three QEMU virtual machine targets:

- `malta-be` — MIPS big-endian, emulated with `qemu-system-mips`
- `x86-64` — x86 64-bit, emulated with `qemu-system-x86`
- `armsr-armv8` — AArch64, emulated with `qemu-system-aarch64`

This provides fast, architecture-wide feedback on every proposed change without requiring
access to physical hardware.

**Once the pull request is approved and merged into `main`**, the `Daily test` workflow runs
the same test suite against the **physical devices** in the HIL testbed, managed remotely via
[Labgrid](https://labgrid.readthedocs.io). Devices are reserved, flashed over the network,
tested, and released automatically. Results are published to the testbed's CI dashboard on
GitHub Pages.

**Watch on YouTube:** [Demo LibreMesh CI/CD Workflow](https://www.youtube.com/watch?v=P8dggBEgez8)

<div class="video-embed">
  <iframe
    src="https://www.youtube.com/embed/P8dggBEgez8"
    title="Demo LibreMesh CI/CD — from pull request to physical hardware"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    allowfullscreen
    loading="lazy"
    referrerpolicy="strict-origin-when-cross-origin"
  ></iframe>
</div>

---
