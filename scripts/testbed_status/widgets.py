"""Custom Textual widgets for each dashboard panel."""

from __future__ import annotations

from typing import Dict, List, Optional

from textual.message import Message
from textual.widgets import DataTable, Static

from .collectors import DutStatus, ModeInfo, RelayState, ServiceState
from .config import CHANNEL_NAMES, CHANNEL_PINS, INFRA_CHANNELS, LOG_MAX_LINES, RELAY_CHANNEL_COUNT


# ---------------------------------------------------------------------------
# Custom messages posted by panels so the App can handle actions
# ---------------------------------------------------------------------------
class RelayToggleRequest(Message):
    def __init__(self, channel: int, current_state: Optional[bool], is_infra: bool) -> None:
        super().__init__()
        self.channel = channel
        self.current_state = current_state
        self.is_infra = is_infra


class ServiceActionRequest(Message):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name


class PoolMoveRequest(Message):
    def __init__(self, dut_name: str, current_pool: str) -> None:
        super().__init__()
        self.dut_name = dut_name
        self.current_pool = current_pool


class ModeChangeRequest(Message):
    def __init__(self, current_mode: str) -> None:
        super().__init__()
        self.current_mode = current_mode


# ---------------------------------------------------------------------------
# Mode header
# ---------------------------------------------------------------------------
class ModeHeader(Static):
    """Top bar showing current testbed mode. Click or press Enter to change mode."""

    can_focus = True
    _current_mode: str = "unknown"

    DEFAULT_CSS = """
    ModeHeader:focus {
        background: $accent;
    }
    """

    def update_mode(self, info: ModeInfo) -> None:
        self._current_mode = info.mode
        mode_upper = info.mode.upper()
        style_map = {
            "LIBREMESH": "[bold green]",
            "OPENWRT": "[bold cyan]",
            "HYBRID": "[bold yellow]",
        }
        color = style_map.get(mode_upper, "[bold red]")
        text = f" Modo: {color}{mode_upper}[/]  ({info.detail})  [dim][Enter para cambiar][/]"
        self.update(text)

    def on_click(self) -> None:
        self.post_message(ModeChangeRequest(current_mode=self._current_mode))

    def on_key(self, event) -> None:
        if event.key == "enter":
            event.stop()
            self.post_message(ModeChangeRequest(current_mode=self._current_mode))


# ---------------------------------------------------------------------------
# Relay panel
# ---------------------------------------------------------------------------
class RelayPanel(DataTable):
    """Table of relay channel states with row navigation and toggle on Enter."""

    # Map row_key → channel index so we can look it up on selection
    _row_key_to_channel: Dict[str, int]

    def on_mount(self) -> None:
        self._row_key_to_channel = {}
        self.add_columns("Canal", "Pin", "Dispositivo", "Estado")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_relays(self, state: RelayState) -> None:
        saved_row = self.cursor_row
        self.clear()
        self._row_key_to_channel = {}

        if state.error:
            self.add_row("--", "--", f"[red]{state.error}[/]", "--")
            return

        for ch in range(RELAY_CHANNEL_COUNT):
            name = CHANNEL_NAMES.get(ch, f"Canal {ch}")
            pin = CHANNEL_PINS.get(ch, "?")
            is_on = state.channels.get(ch)
            if is_on is None:
                status_str = "[dim]?[/]"
            elif is_on:
                status_str = "[bold green]ON[/]"
            else:
                status_str = "[red]OFF[/]"
            row_key = self.add_row(str(ch), pin, name, status_str, key=str(ch))
            self._row_key_to_channel[str(row_key)] = ch

        # Restore cursor position after refresh
        if saved_row < self.row_count:
            self.move_cursor(row=saved_row)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        row_key = str(event.row_key)
        channel = self._row_key_to_channel.get(row_key)
        if channel is None:
            return
        # Determine current state from the table cell text (strip markup)
        cell_text = str(self.get_cell_at((event.cursor_row, 3)))
        is_on: Optional[bool] = None
        if "ON" in cell_text:
            is_on = True
        elif "OFF" in cell_text:
            is_on = False
        self.post_message(RelayToggleRequest(
            channel=channel,
            current_state=is_on,
            is_infra=channel in INFRA_CHANNELS,
        ))


# ---------------------------------------------------------------------------
# Services panel
# ---------------------------------------------------------------------------
class ServicesPanel(DataTable):
    """Table of systemd service states with row navigation and action on Enter."""

    _row_key_to_service: Dict[str, str]

    def on_mount(self) -> None:
        self._row_key_to_service = {}
        self.add_columns("Servicio", "Estado")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_services(self, services: List[ServiceState]) -> None:
        saved_row = self.cursor_row
        self.clear()
        self._row_key_to_service = {}

        for svc in services:
            status = svc.status
            if status == "active":
                styled = "[bold green]active[/]"
            elif status == "inactive":
                styled = "[dim]inactive[/]"
            elif status == "failed":
                styled = "[bold red]failed[/]"
            else:
                styled = f"[yellow]{status}[/]"
            row_key = self.add_row(svc.name, styled, key=svc.name)
            self._row_key_to_service[str(row_key)] = svc.name

        if saved_row < self.row_count:
            self.move_cursor(row=saved_row)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        service_name = self._row_key_to_service.get(str(event.row_key))
        if service_name:
            self.post_message(ServiceActionRequest(service_name=service_name))


# ---------------------------------------------------------------------------
# Pools panel
# ---------------------------------------------------------------------------
class PoolsPanel(DataTable):
    """Navigable table showing DUT → Pool assignment."""

    _row_key_to_dut: Dict[str, str]
    _dut_to_pool: Dict[str, str]

    def on_mount(self) -> None:
        self._row_key_to_dut = {}
        self._dut_to_pool = {}
        self.add_columns("DUT", "Pool")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_pools(
        self, pools: Dict[str, List[str]], error: str = ""
    ) -> None:
        saved_row = self.cursor_row
        self.clear()
        self._row_key_to_dut = {}
        self._dut_to_pool = {}

        if error:
            self.add_row("[red]error[/]", f"[red]{error}[/]")
            return

        for pool_name in ("libremesh", "openwrt"):
            duts = pools.get(pool_name, [])
            color = "green" if pool_name == "libremesh" else "cyan"
            pool_styled = f"[bold {color}]{pool_name}[/]"
            for dut in duts:
                row_key = self.add_row(dut, pool_styled, key=dut)
                self._row_key_to_dut[str(row_key)] = dut
                self._dut_to_pool[dut] = pool_name

        if saved_row < self.row_count:
            self.move_cursor(row=saved_row)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        dut_name = self._row_key_to_dut.get(str(event.row_key))
        if not dut_name:
            return
        current_pool = self._dut_to_pool.get(dut_name, "")
        self.post_message(PoolMoveRequest(dut_name=dut_name, current_pool=current_pool))


# ---------------------------------------------------------------------------
# DUTs panel
# ---------------------------------------------------------------------------
class DutsPanel(DataTable):
    """Table with combined DUT status."""

    def on_mount(self) -> None:
        self.add_columns("DUT", "Pool", "Puerto", "Power", "Relé", "SSH", "Place")
        self.cursor_type = "none"
        self.zebra_stripes = True

    def update_duts(self, duts: List[DutStatus]) -> None:
        saved_row = self.cursor_row
        self.clear()
        for d in duts:
            is_poe = "poe" in d.pdu_name.lower()
            power = "PoE" if is_poe else "Relé"

            if d.relay_on is None:
                relay_str = "[dim]-[/]" if is_poe else "[dim]?[/]"
            elif d.relay_on:
                relay_str = "[bold green]ON[/]"
            else:
                relay_str = "[red]OFF[/]"

            if d.ssh_ok is None:
                ssh_str = "[dim]…[/]"
            elif d.ssh_ok:
                ssh_str = "[bold green]OK[/]"
            else:
                ssh_str = "[bold red]FAIL[/]"

            place_str = d.place_status or "[dim]-[/]"
            if "acquired" in place_str:
                place_str = f"[yellow]{place_str}[/]"
            elif place_str == "free":
                place_str = f"[green]{place_str}[/]"

            pool_color = {"libremesh": "green", "openwrt": "cyan"}.get(d.pool, "dim")
            pool_str = f"[{pool_color}]{d.pool}[/]"

            self.add_row(
                d.name,
                pool_str,
                str(d.switch_port),
                power,
                relay_str,
                ssh_str,
                place_str,
            )

        if saved_row < self.row_count:
            self.move_cursor(row=saved_row)


# ---------------------------------------------------------------------------
# Command log panel
# ---------------------------------------------------------------------------
class CommandLogPanel(Static):
    """Collapsible panel showing executed commands."""

    _expanded: bool = False
    _lines: List[str]

    DEFAULT_CSS = """
    CommandLogPanel {
        height: 1;
        background: $surface;
        border-top: solid $primary;
        padding: 0 1;
    }
    CommandLogPanel.expanded {
        height: 12;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._lines = []

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self.set_class(self._expanded, "expanded")
        self._refresh_log_display()

    def add_log(self, line: str) -> None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._lines.append(f"[dim]{timestamp}[/] {line}")
        if len(self._lines) > LOG_MAX_LINES:
            self._lines = self._lines[-LOG_MAX_LINES:]
        self._refresh_log_display()

    def _refresh_log_display(self) -> None:
        if not self._expanded:
            count = len(self._lines)
            hint = f" ({count} entries)" if count else ""
            self.update(f"[dim]Log{hint} — [l] para expandir[/]")
        else:
            if self._lines:
                self.update("\n".join(self._lines[-11:]))
            else:
                self.update("[dim]No hay comandos ejecutados aún[/]")
