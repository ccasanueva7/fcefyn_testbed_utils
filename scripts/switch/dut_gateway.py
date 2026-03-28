"""
DUT Gateway - Update default gateway on OpenWrt DUTs via parallel SSH.

Shared module used by switch_vlan_preset.py (all DUTs same mode) and
pool-manager.py (hybrid: each DUT in its own pool/mode).

For each DUT, builds a shell script that:
  - Persists gateway and DNS in UCI (survives reboot)
  - Applies the route immediately via ip route replace (no network restart)
  - Ensures an IP in the gateway's subnet exists on br-lan so the upstream/gateway
    router can route replies back to the DUT
  - Stops the firewall (fw3/fw4) since test DUTs don't need it
"""

import logging
import subprocess
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from constants import MESH_GATEWAY, MESH_DNS

logger = logging.getLogger(__name__)

SSH_TIMEOUT = 10
SSH_BASE_CMD = [
    "ssh",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", f"ConnectTimeout={SSH_TIMEOUT}",
    "-o", "LogLevel=ERROR",
]

DEFAULT_SETTLE_SECONDS = 5


def load_duts(config_path: Path) -> list[dict]:
    """Load DUT info from pool-config.yaml.

    Returns list of dicts with keys: id, vlan, ssh_alias, mesh_src_ip,
    ip_last_octet.
    """
    if yaml is None or not config_path.exists():
        return []
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    duts = data.get("duts") or {}
    result = []
    for dut_id, hw in duts.items():
        vlan = hw.get("switch_vlan_isolated")
        ssh_alias = hw.get("ssh_alias")
        mesh_ip = hw.get("libremesh_fixed_ip", "")
        if vlan and ssh_alias:
            last_octet = mesh_ip.split(".")[-1] if mesh_ip else ""
            result.append({
                "id": dut_id,
                "vlan": vlan,
                "ssh_alias": ssh_alias,
                "mesh_src_ip": f"192.168.200.{last_octet}" if last_octet else "",
                "ip_last_octet": last_octet,
            })
    return result


def build_gateway_script(
    mode: str, vlan: int, mesh_src_ip: str = "", ip_last_octet: str = ""
) -> str:
    """Build a shell script that updates the gateway on a DUT instantly.

    Args:
        mode: "mesh" or "isolated".
        vlan: The DUT's isolated VLAN number (used to derive the isolated gateway).
        mesh_src_ip: The DUT's 192.168.200.x IP for mesh mode source routing.
        ip_last_octet: Last octet derived from libremesh_fixed_ip, used to
            build a per-DUT IP in the isolated VLAN subnet so the upstream
            router can route replies back.
    """
    if mode == "mesh":
        gateway = MESH_GATEWAY
    else:
        gateway = f"192.168.{vlan}.254"

    lines = [
        "#!/bin/sh",
        "set -e",
        "while uci delete network.@route[0] 2>/dev/null; do :; done; true",
        "uci delete network.lan.gateway 2>/dev/null; true",
        f"uci set network.lan.gateway='{gateway}'",
        f"uci set network.lan.dns='{MESH_DNS}'",
        "uci set network.mesh_route=route",
        "uci set network.mesh_route.interface='lan'",
        "uci set network.mesh_route.target='10.13.0.0'",
        "uci set network.mesh_route.netmask='255.255.0.0'",
        "uci set network.mesh_route.gateway='0.0.0.0'",
        "uci commit network",
    ]

    if mode == "mesh" and mesh_src_ip:
        src_ip = mesh_src_ip
        lines += [
            f"ip addr show dev br-lan | grep -q '{src_ip}/' || "
            f"ip addr add {src_ip}/24 dev br-lan",
            f"ip route replace default via {gateway} dev br-lan src {src_ip}",
        ]
    elif ip_last_octet:
        src_ip = f"192.168.{vlan}.{ip_last_octet}"
        lines += [
            f"ip addr show dev br-lan | grep -q '{src_ip}/' || "
            f"ip addr add {src_ip}/24 dev br-lan",
            f"ip route replace default via {gateway} dev br-lan src {src_ip}",
        ]
    else:
        lines.append(f"ip route replace default via {gateway} dev br-lan onlink")

    lines += [
        "ip route replace 10.13.0.0/16 dev br-lan scope link 2>/dev/null || true",
        "echo 'nameserver 8.8.8.8' > /etc/resolv.conf",
        "echo 'nameserver 8.8.4.4' >> /etc/resolv.conf",
        "if [ -x /etc/init.d/firewall ]; then /etc/init.d/firewall stop 2>/dev/null; fi || true",
        "iptables -P OUTPUT ACCEPT 2>/dev/null || true",
        "iptables -F OUTPUT 2>/dev/null || true",
        "echo OK",
    ]
    return "\n".join(lines)


def update_dut_gateways(
    dut_modes: dict[str, str],
    config_path: Path,
    dry_run: bool = False,
    settle_seconds: int = DEFAULT_SETTLE_SECONDS,
) -> None:
    """Update the default gateway on DUTs via parallel SSH.

    Args:
        dut_modes: Mapping of DUT id -> mode ("mesh" or "isolated").
                   Only DUTs present in this dict are updated.
        config_path: Path to pool-config.yaml (for ssh_alias, vlan, mesh IP).
        dry_run: If True, print commands without connecting.
        settle_seconds: Seconds to wait before SSH (for VLAN switch to settle).
    """
    all_duts = load_duts(config_path)
    duts = [d for d in all_duts if d["id"] in dut_modes]
    if not duts:
        logger.info("No matching DUTs found; skipping gateway update")
        return

    mode_summary = {}
    for dut in duts:
        m = dut_modes[dut["id"]]
        mode_summary.setdefault(m, []).append(dut["id"])
    logger.info(
        "Updating gateway on %d DUTs (SSH parallel): %s",
        len(duts),
        {m: len(ids) for m, ids in mode_summary.items()},
    )

    if not dry_run and settle_seconds > 0:
        logger.info("  Waiting %ds for VLAN switch to settle...", settle_seconds)
        time.sleep(settle_seconds)

    if dry_run:
        for dut in duts:
            mode = dut_modes[dut["id"]]
            script = build_gateway_script(
                mode, dut["vlan"], dut.get("mesh_src_ip", ""), dut.get("ip_last_octet", ""),
            )
            logger.info("  [DRY-RUN] %s (%s, %s):\n%s", dut["id"], dut["ssh_alias"], mode, script)
        return

    procs: list[tuple[dict, subprocess.Popen]] = []
    for dut in duts:
        ssh_alias = dut.get("ssh_alias")
        if not ssh_alias:
            logger.warning("  SKIP %s: no ssh_alias in pool-config", dut["id"])
            continue

        mode = dut_modes[dut["id"]]
        script = build_gateway_script(
            mode, dut["vlan"], dut.get("mesh_src_ip", ""), dut.get("ip_last_octet", ""),
        )
        cmd = SSH_BASE_CMD + [ssh_alias, script]
        logger.debug("  Launching SSH to %s (%s, mode=%s)", dut["id"], ssh_alias, mode)
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        procs.append((dut, proc))

    for dut, proc in procs:
        try:
            stdout, stderr = proc.communicate(timeout=SSH_TIMEOUT + 5)
            out_text = stdout.decode(errors="replace").strip()
            err_text = stderr.decode(errors="replace").strip()
            if out_text:
                logger.debug("  [stdout] %s: %s", dut["id"], out_text[:500])
            if proc.returncode == 0 and "OK" in out_text:
                logger.info("  OK %s -> gateway updated", dut["id"])
            elif proc.returncode == 0:
                logger.warning("  PARTIAL %s (script may have failed): stdout=%s", dut["id"], out_text[:300])
            else:
                logger.warning("  FAIL %s (exit %d): %s", dut["id"], proc.returncode, err_text[:300])
        except subprocess.TimeoutExpired:
            proc.kill()
            logger.warning("  TIMEOUT %s -> killed", dut["id"])
