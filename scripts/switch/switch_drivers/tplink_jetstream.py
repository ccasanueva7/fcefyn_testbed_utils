"""
TP-Link JetStream driver - CLI command builders for TP-Link JetStream switches.

Builds command lists for VLAN presets, hybrid VLAN assignment, PoE control,
and dynamic VLAN creation. Commands are specific to the TP-Link JetStream CLI
(tested on SG2016P) but executed by switch_client.py via Netmiko.

Netmiko device_type: "tplink_jetstream"
"""

from __future__ import annotations

DEVICE_TYPE = "tplink_jetstream"

PRESET_ISOLATED = [
    (1, ["no switchport general allowed vlan 200", "switchport general allowed vlan 104 untagged", "switchport pvid 104"]),
    (2, ["no switchport general allowed vlan 200", "switchport general allowed vlan 105 untagged", "switchport pvid 105"]),
    (3, ["no switchport general allowed vlan 200", "switchport general allowed vlan 106 untagged", "switchport pvid 106"]),
    (4, ["no switchport general allowed vlan 200"]),
    (5, ["no switchport general allowed vlan 200"]),
    (6, ["no switchport general allowed vlan 200"]),
    (7, ["no switchport general allowed vlan 200"]),
    (8, ["no switchport general allowed vlan 200"]),
    (9, ["no switchport general allowed vlan 200", "switchport general allowed vlan 100-106 tagged"]),
    (10, ["no switchport general allowed vlan 200", "switchport general allowed vlan 100-106 tagged"]),
    (11, ["no switchport general allowed vlan 200", "switchport general allowed vlan 100 untagged", "switchport pvid 100"]),
    (12, ["no switchport general allowed vlan 200", "switchport general allowed vlan 101 untagged", "switchport pvid 101"]),
    (13, ["no switchport general allowed vlan 200", "switchport general allowed vlan 102 untagged", "switchport pvid 102"]),
    (14, ["no switchport general allowed vlan 200", "switchport general allowed vlan 103 untagged", "switchport pvid 103"]),
    (15, ["no switchport general allowed vlan 200", "switchport general allowed vlan 105 untagged", "switchport pvid 105"]),
    (16, ["no switchport general allowed vlan 200", "switchport general allowed vlan 104 untagged", "switchport pvid 104"]),
]

PRESET_MESH = [
    (1, ["no switchport general allowed vlan 104", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (2, ["no switchport general allowed vlan 105", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (3, ["no switchport general allowed vlan 106", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (4, ["no switchport general allowed vlan 1", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (5, ["no switchport general allowed vlan 1", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (6, ["no switchport general allowed vlan 1", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (7, ["no switchport general allowed vlan 1", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (8, ["no switchport general allowed vlan 1", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (9, ["switchport general allowed vlan 100-106,200 tagged"]),
    (10, ["switchport general allowed vlan 100-106,200 tagged"]),
    (11, ["no switchport general allowed vlan 100", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (12, ["no switchport general allowed vlan 101", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (13, ["no switchport general allowed vlan 102", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (14, ["no switchport general allowed vlan 103", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (15, ["no switchport general allowed vlan 105", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
    (16, ["no switchport general allowed vlan 104", "switchport general allowed vlan 200 untagged", "switchport pvid 200"]),
]

PRESETS = {
    "isolated": (PRESET_ISOLATED, False),
    "mesh": (PRESET_MESH, True),
}


def build_preset_commands(preset_name: str) -> list[str]:
    """Build CLI commands for a full VLAN preset (isolated or mesh).

    Raises ValueError if preset_name is not recognized.
    """
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset '{preset_name}'. Valid: {list(PRESETS.keys())}")

    preset, create_vlan_200 = PRESETS[preset_name]
    cmds: list[str] = []

    if create_vlan_200:
        cmds.extend(["vlan 200", 'name "mesh"', "exit"])

    for port, iface_cmds in preset:
        cmds.append(f"interface gigabitEthernet 1/0/{port}")
        cmds.extend(iface_cmds)
        cmds.append("exit")

    return cmds


def build_poe_commands(port: int, action: str) -> list[str]:
    """Build CLI commands to enable/disable PoE on a port.

    Raises ValueError if action is not 'on' or 'off'.
    """
    if action not in ("on", "off"):
        raise ValueError(f"Invalid PoE action '{action}'. Valid: on, off")

    poe_cmd = "enable" if action == "on" else "disable"
    return [
        f"interface gigabitEthernet 1/0/{port}",
        f"power inline supply {poe_cmd}",
        "exit",
    ]


def build_hybrid_commands(
    port_assignments: list[tuple[int, str, int]],
    active_isolated_vlans: set[int],
    has_libremesh_duts: bool,
    uplink_ports: list[int],
    vlan_mesh: int = 200,
    ports_to_include: set[int] | None = None,
    include_uplinks: bool = True,
) -> list[str]:
    """Build CLI commands for hybrid VLAN assignment.

    Each DUT port is configured independently based on its pool.
    Uplink ports are tagged for all active VLANs.

    Args:
        port_assignments: list of (port, pool, isolated_vlan) tuples.
        active_isolated_vlans: set of VLAN IDs used by openwrt-pool DUTs.
        has_libremesh_duts: whether any DUT is in the libremesh pool.
        uplink_ports: ports that carry tagged traffic to the host.
        vlan_mesh: VLAN ID for the mesh network.
        ports_to_include: if set, only these ports are configured (differential apply).
        include_uplinks: if False, uplink port config is skipped.
    """
    cmds: list[str] = []

    if has_libremesh_duts:
        cmds.extend(["vlan 200", 'name "mesh"', "exit"])

    for port, pool, isolated_vlan in port_assignments:
        if ports_to_include is not None and port not in ports_to_include:
            continue
        cmds.append(f"interface gigabitEthernet 1/0/{port}")
        if pool == "isolated":
            cmds.append(f"no switchport general allowed vlan {vlan_mesh}")
            cmds.append(f"switchport general allowed vlan {isolated_vlan} untagged")
            cmds.append(f"switchport pvid {isolated_vlan}")
        else:
            cmds.append(f"no switchport general allowed vlan {isolated_vlan}")
            cmds.append(f"switchport general allowed vlan {vlan_mesh} untagged")
            cmds.append(f"switchport pvid {vlan_mesh}")
        cmds.append("exit")

    if include_uplinks and uplink_ports:
        all_vlans = sorted(active_isolated_vlans)
        if has_libremesh_duts:
            all_vlans.append(vlan_mesh)
        all_vlans = sorted(set(all_vlans))
        if all_vlans:
            vlan_str = ",".join(str(v) for v in all_vlans)
            for uplink_port in uplink_ports:
                cmds.append(f"interface gigabitEthernet 1/0/{uplink_port}")
                cmds.append(f"switchport general allowed vlan {vlan_str} tagged")
                cmds.append("exit")

    return cmds


def ensure_vlan_commands(vlan_id: int, name: str | None = None) -> list[str]:
    """Build CLI commands to create a VLAN if it does not exist.

    The TP-Link CLI is idempotent for 'vlan <id>': it enters VLAN config
    mode whether the VLAN already exists or not.
    """
    cmds = [f"vlan {vlan_id}"]
    if name:
        cmds.append(f'name "{name}"')
    cmds.append("exit")
    return cmds


def assign_port_vlan_commands(
    port: int,
    vlan_id: int,
    mode: str = "untagged",
    remove_vlans: list[int] | None = None,
) -> list[str]:
    """Build CLI commands to assign a port to a VLAN.

    Args:
        port: switch port number.
        vlan_id: VLAN to assign.
        mode: 'untagged' or 'tagged'.
        remove_vlans: VLANs to remove from the port before assigning.
    """
    cmds = [f"interface gigabitEthernet 1/0/{port}"]
    for vlan in remove_vlans or []:
        cmds.append(f"no switchport general allowed vlan {vlan}")
    cmds.append(f"switchport general allowed vlan {vlan_id} {mode}")
    if mode == "untagged":
        cmds.append(f"switchport pvid {vlan_id}")
    cmds.append("exit")
    return cmds
