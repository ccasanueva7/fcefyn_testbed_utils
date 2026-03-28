"""Paths, constants and channel-to-name mappings for the testbed TUI."""

import os
from pathlib import Path

VLAN_MODE_FILE = Path.home() / ".config" / "labgrid-vlan-mode"
SWITCH_STATE_FILE = Path.home() / ".config" / "labgrid-switch-state.yaml"

POOL_CONFIG_PATH = Path(
    os.environ.get(
        "TESTBED_POOL_CONFIG",
        "/etc/testbed/pool-config.yaml",
    )
)

ARDUINO_DAEMON_SOCKET = "/tmp/arduino-relay.sock"

RELAY_CHANNEL_COUNT = 11

CHANNEL_NAMES = {
    0: "Belkin RT3200 #1",
    1: "Belkin RT3200 #2",
    2: "Belkin RT3200 #3",
    3: "Banana Pi R4",
    4: "(sin asignar)",
    5: "(sin asignar)",
    6: "(sin asignar)",
    7: "(sin asignar)",
    8: "(sin asignar)",
    9: "Cooler",
    10: "Fuente",
}

CHANNEL_PINS = {
    0: "D2", 1: "D3", 2: "D4", 3: "D5",
    4: "D6", 5: "D7", 6: "D8", 7: "D9",
    8: "D10", 9: "D11", 10: "D12",
}

INFRA_CHANNELS = {8, 9, 10}

SYSTEMD_SERVICES = [
    "labgrid-exporter",
    "labgrid-exporter-openwrt",
    "labgrid-exporter-libremesh",
    "labgrid-coordinator",
    "pdudaemon",
    "dnsmasq",
    "arduino-relay-daemon",
]

RUNNER_SERVICE_GLOB = "actions.runner.*"

FAST_REFRESH_SECONDS = 5
SLOW_REFRESH_SECONDS = 30
SSH_CONNECT_TIMEOUT = 3

LOG_MAX_LINES = 50
