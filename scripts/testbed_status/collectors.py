"""Data collectors that query each state source for the TUI."""

from __future__ import annotations

import asyncio
import json
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .config import (
    ARDUINO_DAEMON_SOCKET,
    POOL_CONFIG_PATH,
    RUNNER_SERVICE_GLOB,
    SSH_CONNECT_TIMEOUT,
    SYSTEMD_SERVICES,
    VLAN_MODE_FILE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ModeInfo:
    mode: str = "unknown"
    detail: str = ""


@dataclass
class RelayState:
    connected: bool = False
    channels: Dict[int, bool] = field(default_factory=dict)
    error: str = ""


@dataclass
class ServiceState:
    name: str = ""
    status: str = "unknown"


@dataclass
class PoolConfig:
    duts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    pools: Dict[str, List[str]] = field(default_factory=dict)
    error: str = ""


@dataclass
class DutStatus:
    name: str = ""
    ssh_alias: str = ""
    pdu_name: str = ""
    pdu_index: Optional[int] = None
    switch_port: int = 0
    switch_vlan: int = 0
    pool: str = ""
    relay_on: Optional[bool] = None
    ssh_ok: Optional[bool] = None
    place_status: str = ""


@dataclass
class PlaceInfo:
    name: str = ""
    acquired: bool = False
    acquired_by: str = ""


# ---------------------------------------------------------------------------
# Mode
# ---------------------------------------------------------------------------
async def get_mode() -> ModeInfo:
    try:
        if VLAN_MODE_FILE.exists():
            raw = VLAN_MODE_FILE.read_text().strip()
            mode_map = {"isolated": "openwrt", "mesh": "libremesh"}
            mode = mode_map.get(raw, raw)
            detail_map = {
                "openwrt": "isolated – VLANs 100-108",
                "libremesh": "mesh – VLAN 200",
            }
            return ModeInfo(mode=mode, detail=detail_map.get(mode, raw))

        pool_cfg = _load_pool_config_sync()
        if pool_cfg and not pool_cfg.error:
            openwrt_duts = pool_cfg.pools.get("openwrt", [])
            libremesh_duts = pool_cfg.pools.get("libremesh", [])
            if openwrt_duts and libremesh_duts:
                return ModeInfo(mode="hybrid", detail="DUTs split across pools")
            if openwrt_duts:
                return ModeInfo(mode="openwrt", detail="isolated – VLANs 100-108")
            if libremesh_duts:
                return ModeInfo(mode="libremesh", detail="mesh – VLAN 200")
        return ModeInfo(mode="unknown", detail="mode file not found")
    except Exception as exc:
        return ModeInfo(mode="error", detail=str(exc))


# ---------------------------------------------------------------------------
# Relay status via daemon socket
# ---------------------------------------------------------------------------
async def get_relay_status() -> RelayState:
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None, _get_relay_status_sync
        )
    except Exception as exc:
        return RelayState(error=str(exc))


def _get_relay_status_sync() -> RelayState:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(2.0)
            sock.connect(ARDUINO_DAEMON_SOCKET)
            request = json.dumps({"command": "STATUS"}).encode("utf-8")
            sock.send(request)
            data = sock.recv(4096)
            resp = json.loads(data.decode("utf-8"))

        if not resp.get("success", False):
            return RelayState(error=resp.get("error", "unknown daemon error"))

        raw = resp.get("response", "")
        channels = _parse_status_line(raw)
        return RelayState(connected=True, channels=channels)
    except FileNotFoundError:
        return RelayState(error="daemon not running (socket not found)")
    except ConnectionRefusedError:
        return RelayState(error="daemon not responding")
    except Exception as exc:
        return RelayState(error=str(exc))


def _parse_status_line(raw: str) -> Dict[int, bool]:
    channels: Dict[int, bool] = {}
    for line in raw.splitlines():
        if line.startswith("STATUS"):
            for tok in line.split()[1:]:
                if ":" in tok:
                    idx_s, val = tok.split(":", 1)
                    try:
                        channels[int(idx_s)] = val.upper() == "ON"
                    except ValueError:
                        continue
            break
    return channels


# ---------------------------------------------------------------------------
# Systemd services
# ---------------------------------------------------------------------------
async def get_services_status() -> List[ServiceState]:
    results: List[ServiceState] = []

    procs = []
    for svc in SYSTEMD_SERVICES:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "is-active", svc,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        procs.append((svc, proc))

    runner_proc = await asyncio.create_subprocess_exec(
        "systemctl", "list-units", "--type=service", "--state=active",
        "--no-legend", "--no-pager", RUNNER_SERVICE_GLOB,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    for svc, proc in procs:
        stdout, _ = await proc.communicate()
        status = stdout.decode().strip() if stdout else "unknown"
        results.append(ServiceState(name=svc, status=status))

    runner_stdout, _ = await runner_proc.communicate()
    runner_lines = runner_stdout.decode().strip().splitlines() if runner_stdout else []
    if runner_lines:
        results.append(ServiceState(name="actions.runner", status="active"))
    else:
        results.append(ServiceState(name="actions.runner", status="inactive"))

    return results


# ---------------------------------------------------------------------------
# Pool config
# ---------------------------------------------------------------------------
async def get_pool_config() -> PoolConfig:
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None, _load_pool_config_sync
        )
    except Exception as exc:
        return PoolConfig(error=str(exc))


def _load_pool_config_sync() -> PoolConfig:
    path = Path(POOL_CONFIG_PATH)
    if not path.exists():
        return PoolConfig(error=f"file not found: {path}")
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        duts = data.get("duts", {})
        pools_raw = data.get("pools", {})
        pools = {
            name: pool_data.get("duts", [])
            for name, pool_data in pools_raw.items()
        }
        return PoolConfig(duts=duts, pools=pools)
    except Exception as exc:
        return PoolConfig(error=str(exc))


# ---------------------------------------------------------------------------
# SSH healthcheck
# ---------------------------------------------------------------------------
async def check_dut_ssh(ssh_alias: str) -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh",
            "-o", f"ConnectTimeout={SSH_CONNECT_TIMEOUT}",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            ssh_alias,
            "echo", "OK",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        return proc.returncode == 0 and b"OK" in (stdout or b"")
    except Exception:
        return False


async def check_all_duts_ssh(
    duts: Dict[str, Dict[str, Any]],
) -> Dict[str, bool]:
    tasks = {}
    for name, info in duts.items():
        alias = info.get("ssh_alias", "")
        if alias:
            tasks[name] = asyncio.create_task(check_dut_ssh(alias))

    results: Dict[str, bool] = {}
    for name, task in tasks.items():
        results[name] = await task
    return results


# ---------------------------------------------------------------------------
# Labgrid places
# ---------------------------------------------------------------------------
async def get_labgrid_places() -> List[PlaceInfo]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "labgrid-client", "places",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return []
        return _parse_places_output(stdout.decode() if stdout else "")
    except FileNotFoundError:
        return []
    except Exception:
        return []


def _parse_places_output(output: str) -> List[PlaceInfo]:
    places: List[PlaceInfo] = []
    for line in output.strip().splitlines():
        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        acquired = False
        acquired_by = ""
        for part in parts[1:]:
            if part.startswith("acquired:"):
                acquired_by = part.split(":", 1)[1] if ":" in part else ""
                acquired = bool(acquired_by)
        places.append(PlaceInfo(
            name=name, acquired=acquired, acquired_by=acquired_by,
        ))
    return places


# ---------------------------------------------------------------------------
# Composite: build full DUT status list
# ---------------------------------------------------------------------------
def build_dut_statuses(
    pool_cfg: PoolConfig,
    relay: RelayState,
    ssh_results: Dict[str, bool],
    places: List[PlaceInfo],
) -> List[DutStatus]:
    place_map = {p.name: p for p in places}
    dut_pool_map: Dict[str, str] = {}
    for pool_name, dut_list in pool_cfg.pools.items():
        for d in dut_list:
            dut_pool_map[d] = pool_name

    statuses: List[DutStatus] = []
    for name, info in pool_cfg.duts.items():
        pdu_name = info.get("pdu_name", "")
        pdu_index = info.get("pdu_index")
        is_poe = "poe" in pdu_name.lower()

        relay_on: Optional[bool] = None
        if not is_poe and pdu_index is not None and relay.connected:
            relay_on = relay.channels.get(pdu_index)

        place_key = f"labgrid-fcefyn-{name}"
        place = place_map.get(place_key)
        place_status = ""
        if place is not None:
            place_status = (
                f"acquired ({place.acquired_by})" if place.acquired else "free"
            )

        statuses.append(DutStatus(
            name=name,
            ssh_alias=info.get("ssh_alias", ""),
            pdu_name=pdu_name,
            pdu_index=pdu_index,
            switch_port=info.get("switch_port", 0),
            switch_vlan=info.get("switch_vlan_isolated", 0),
            pool=dut_pool_map.get(name, "-"),
            relay_on=relay_on,
            ssh_ok=ssh_results.get(name),
            place_status=place_status,
        ))
    return statuses


# ---------------------------------------------------------------------------
# Mutators
# ---------------------------------------------------------------------------
def _relay_send_sync(command: str) -> bool:
    """Send a command to the arduino daemon and return True on success."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(3.0)
            sock.connect(ARDUINO_DAEMON_SOCKET)
            sock.send(json.dumps({"command": command}).encode("utf-8"))
            data = sock.recv(4096)
            resp = json.loads(data.decode("utf-8"))
            return bool(resp.get("success", False))
    except Exception:
        return False


async def relay_toggle_channel(channel: int) -> bool:
    """Toggle a relay channel via the daemon socket."""
    return await asyncio.get_event_loop().run_in_executor(
        None, _relay_send_sync, f"TOGGLE {channel}"
    )


async def relay_set_channel(channel: int, state: bool) -> bool:
    """Explicitly set a relay channel ON or OFF via the daemon socket."""
    cmd = f"ON {channel}" if state else f"OFF {channel}"
    return await asyncio.get_event_loop().run_in_executor(
        None, _relay_send_sync, cmd
    )


async def service_action(name: str, action: str) -> Tuple[bool, str]:
    """Run a systemctl action on a service. Returns (success, output)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "systemctl", action, name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        success = proc.returncode == 0
        output = ((stdout or b"") + (stderr or b"")).decode().strip()
        return success, output
    except Exception as exc:
        return False, str(exc)


def pool_move_dut(dut_name: str, target_pool: str) -> Tuple[bool, str]:
    """
    Move dut_name to target_pool in pool-config.yaml.
    Removes the DUT from all other pools first.
    """
    path = Path(POOL_CONFIG_PATH)
    if not path.exists():
        return False, f"config file not found: {path}"
    try:
        with open(path) as f:
            data = yaml.safe_load(f)

        pools = data.get("pools", {})
        for pool_name, pool_data in pools.items():
            duts = pool_data.get("duts") or []
            if dut_name in duts:
                duts.remove(dut_name)
            pool_data["duts"] = duts

        target = pools.setdefault(target_pool, {})
        target_duts = target.get("duts") or []
        if dut_name not in target_duts:
            target_duts.append(dut_name)
        target["duts"] = target_duts

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        return True, f"moved {dut_name} → {target_pool}"
    except Exception as exc:
        return False, str(exc)


async def change_testbed_mode(target_mode: str) -> Tuple[bool, str]:
    """
    Change testbed mode by moving all DUTs to the appropriate pool(s)
    and running pool-manager.py --apply.

    target_mode: 'libremesh', 'openwrt', or 'hybrid'
    """
    path = Path(POOL_CONFIG_PATH)
    if not path.exists():
        return False, f"config file not found: {path}"

    try:
        with open(path) as f:
            data = yaml.safe_load(f)

        all_duts = list(data.get("duts", {}).keys())
        pools = data.get("pools", {})

        if target_mode == "libremesh":
            pools["libremesh"] = {"duts": all_duts}
            pools["openwrt"] = {"duts": []}
        elif target_mode == "openwrt":
            pools["openwrt"] = {"duts": all_duts}
            pools["libremesh"] = {"duts": []}
        elif target_mode == "hybrid":
            half = len(all_duts) // 2
            pools["libremesh"] = {"duts": all_duts[:half]}
            pools["openwrt"] = {"duts": all_duts[half:]}
        else:
            return False, f"unknown mode: {target_mode}"

        data["pools"] = pools
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        proc = await asyncio.create_subprocess_exec(
            "pool-manager.py", "--apply", "--force",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = ((stdout or b"") + (stderr or b"")).decode().strip()

        if proc.returncode == 0:
            return True, f"Modo cambiado a {target_mode}"
        return False, output or f"pool-manager.py exit code {proc.returncode}"

    except Exception as exc:
        return False, str(exc)
