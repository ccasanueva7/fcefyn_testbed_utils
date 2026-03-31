"""Textual application: layout, keybindings, modals and refresh timers."""

from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Static

from . import collectors
from .config import CHANNEL_NAMES, FAST_REFRESH_SECONDS, SLOW_REFRESH_SECONDS
from .widgets import (
    CommandLogPanel,
    DutsPanel,
    RelayPanel,
    RelayToggleRequest,
    ServiceActionRequest,
    ServicesPanel,
)

HELP_TEXT = """\
[bold]testbed-status[/] - TUI de estado del lab FCEFyN

[bold]Navegación:[/]
  [cyan]Tab / Shift+Tab[/]  Cambiar de panel
  [cyan]↑ / ↓[/]            Navegar filas
  [cyan]Enter[/]             Ejecutar acción sobre la fila seleccionada

[bold]Acciones por panel:[/]
  [cyan]Relés[/]      Enter → toggle ON/OFF (infraestructura pide confirmación)
  [cyan]Servicios[/]  Enter → start / stop / restart

[bold]Atajos:[/]
  [cyan]r[/]   Refresh inmediato
  [cyan]l[/]   Expandir/colapsar log de comandos
  [cyan]q[/]   Salir
  [cyan]?[/]   Mostrar/ocultar esta ayuda
"""


# ---------------------------------------------------------------------------
# Modal: confirm action (yes / no)
# ---------------------------------------------------------------------------
class ConfirmScreen(ModalScreen[bool]):
    """Generic yes/no confirmation dialog."""

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    #confirm-dialog {
        width: 60;
        height: auto;
        max-height: 12;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    #confirm-buttons {
        margin-top: 1;
        height: 3;
        align: center middle;
    }
    #confirm-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self._prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(self._prompt)
            with Horizontal(id="confirm-buttons"):
                yield Button("Sí", variant="success", id="btn-yes")
                yield Button("No", variant="error", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")


# ---------------------------------------------------------------------------
# Modal: service action (start / stop / restart)
# ---------------------------------------------------------------------------
class ServiceActionScreen(ModalScreen[str]):
    """Choose an action to run on a systemd service."""

    DEFAULT_CSS = """
    ServiceActionScreen {
        align: center middle;
    }
    #svc-dialog {
        width: 50;
        height: auto;
        max-height: 14;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    #svc-buttons {
        margin-top: 1;
        height: 3;
        align: center middle;
    }
    #svc-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service_name = service_name

    def compose(self) -> ComposeResult:
        with Vertical(id="svc-dialog"):
            yield Static(
                f"[bold]Servicio:[/] {self._service_name}\n\nSeleccionar acción:"
            )
            with Horizontal(id="svc-buttons"):
                yield Button("Start", variant="success", id="start")
                yield Button("Stop", variant="error", id="stop")
                yield Button("Restart", variant="warning", id="restart")
                yield Button("Cancelar", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss("")
        else:
            self.dismiss(event.button.id or "")


# ---------------------------------------------------------------------------
# Help overlay
# ---------------------------------------------------------------------------
class HelpOverlay(Static):
    """Modal help text toggled with '?'."""

    DEFAULT_CSS = """
    HelpOverlay {
        display: none;
        layer: overlay;
        dock: bottom;
        width: 100%;
        max-height: 16;
        background: $surface;
        border-top: solid $accent;
        padding: 1 2;
    }
    """


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class TestbedStatusApp(App):
    """Interactive TUI dashboard for the FCEFyN HIL testbed."""

    TITLE = "Testbed FCEFyN"
    CSS = """
    #top-row {
        height: 1fr;
    }
    #bottom-row {
        height: 1fr;
    }
    #relay-container, #services-container, #duts-container {
        border: solid $primary;
        padding: 0 1;
    }
    #relay-container { width: 1fr; }
    #services-container { width: 1fr; }
    #duts-container { width: 2fr; }
    """

    BINDINGS = [
        Binding("q", "quit", "Salir"),
        Binding("r", "refresh_all", "Refresh"),
        Binding("l", "toggle_log", "Log"),
        Binding("question_mark", "toggle_help", "Ayuda"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with Horizontal(id="top-row"):
                with Container(id="relay-container"):
                    yield Static("[bold]Relés Arduino[/]")
                    yield RelayPanel()
                with Container(id="services-container"):
                    yield Static("[bold]Servicios[/]")
                    yield ServicesPanel()
            with Horizontal(id="bottom-row"):
                with Container(id="duts-container"):
                    yield Static("[bold]DUTs[/]")
                    yield DutsPanel()
        yield CommandLogPanel(id="cmd-log")
        yield HelpOverlay(HELP_TEXT, id="help-overlay")
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one(CommandLogPanel)._refresh_log_display()
        await self._refresh_fast()
        await self._refresh_slow()
        self.set_interval(FAST_REFRESH_SECONDS, self._refresh_fast)
        self.set_interval(SLOW_REFRESH_SECONDS, self._refresh_slow)

    def _log(self, msg: str) -> None:
        """Add a message to the command log panel."""
        self.query_one(CommandLogPanel).add_log(msg)

    # -- Fast refresh: relays, services --------------------------------
    async def _refresh_fast(self) -> None:
        relay_state = await collectors.get_relay_status()
        self.query_one(RelayPanel).update_relays(relay_state)

        services = await collectors.get_services_status()
        self.query_one(ServicesPanel).update_services(services)

    # -- Slow refresh: DUTs, SSH, places --------------------------------
    async def _refresh_slow(self) -> None:
        dut_cfg = await collectors.get_dut_config()

        relay_state = await collectors.get_relay_status()
        ssh_results = await collectors.check_all_duts_ssh(dut_cfg.duts)
        places = await collectors.get_labgrid_places()

        dut_statuses = collectors.build_dut_statuses(
            dut_cfg, relay_state, ssh_results, places,
        )
        self.query_one(DutsPanel).update_duts(dut_statuses)

    # -- Relay toggle handler ------------------------------------------
    async def on_relay_toggle_request(self, message: RelayToggleRequest) -> None:
        channel = message.channel
        ch_name = CHANNEL_NAMES.get(channel, f"Canal {channel}")

        if message.is_infra:
            state_label = "ON" if message.current_state else "OFF"
            prompt = (
                f"[bold yellow]Canal de infraestructura[/]\n\n"
                f"¿Toggle [bold]{ch_name}[/] (canal {channel})?\n"
                f"Estado actual: [bold]{state_label}[/]"
            )

            def _on_confirm(confirmed: bool) -> None:
                if confirmed:
                    asyncio.ensure_future(self._do_relay_toggle(channel))

            self.push_screen(ConfirmScreen(prompt), callback=_on_confirm)
        else:
            await self._do_relay_toggle(channel)

    async def _do_relay_toggle(self, channel: int) -> None:
        ch_name = CHANNEL_NAMES.get(channel, f"Canal {channel}")
        self._log(f"[cyan]RELAY[/] TOGGLE {channel} ({ch_name})")
        success = await collectors.relay_toggle_channel(channel)
        if success:
            self._log("  → [green]OK[/]")
        else:
            self._log("  → [red]ERROR[/]")
            self.notify(f"Error al toggle canal {channel}", severity="error")
        await self._refresh_fast()

    # -- Service action handler ----------------------------------------
    async def on_service_action_request(self, message: ServiceActionRequest) -> None:
        svc_name = message.service_name

        def _on_action(action: str) -> None:
            if action:
                asyncio.ensure_future(self._do_service_action(svc_name, action))

        self.push_screen(ServiceActionScreen(svc_name), callback=_on_action)

    async def _do_service_action(self, name: str, action: str) -> None:
        self._log(f"[yellow]SYSTEMCTL[/] sudo systemctl {action} {name}")
        success, output = await collectors.service_action(name, action)
        if success:
            self._log("  → [green]OK[/]")
            self.notify(f"{action} {name}: OK", severity="information")
        else:
            self._log(f"  → [red]ERROR[/]: {output[:60]}")
            self.notify(f"{action} {name}: {output}", severity="error")
        await self._refresh_fast()

    # -- Global actions ------------------------------------------------
    async def action_refresh_all(self) -> None:
        await self._refresh_fast()
        await self._refresh_slow()

    def action_toggle_help(self) -> None:
        overlay = self.query_one("#help-overlay", HelpOverlay)
        overlay.display = not overlay.display

    def action_toggle_log(self) -> None:
        self.query_one(CommandLogPanel).toggle()
