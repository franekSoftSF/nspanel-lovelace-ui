"""Runtime: wires the panel backend to Home Assistant's MQTT, event bus and time tracking."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
import json
import logging
import queue
import re
import threading
from typing import Any

from homeassistant.components import mqtt
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval

from .backend.libs import home_assistant as bridge
from .const import ESPHOME_EVENT

_LOGGER = logging.getLogger(__name__)

_STOP = object()


def panel_settings(settings: dict[str, Any], default_time_zone: str) -> dict[str, dict[str, Any]]:
    """Per-panel settings with the same inheritance as the add-on (main.setup_panels)."""
    panels = {}
    for name, panel in settings["nspanels"].items():
        panel = dict(panel)
        panel.setdefault("timeZone", settings.get("timeZone", default_time_zone))
        panel.setdefault("locale", settings.get("locale", "en_US"))
        panel.setdefault("hiddenCards", settings.get("hiddenCards", []))
        panel.setdefault("timeFormat", settings.get("timeFormat", "%H:%M"))
        panel.setdefault("dateFormat", settings.get("dateFormat", "full"))
        panels[name] = panel
    return panels


_ENTITY_ID = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
# Not Home Assistant entities: panel-internal pseudo domains.
_PSEUDO_DOMAINS = {"navigate", "iText", "delete", "service"}
# Read by the backend without being configured (brightness schedules use sunrise/sunset).
_ALWAYS_RELEVANT = {"sun.sun"}


def referenced_entities(settings: Any) -> frozenset[str]:
    """Every string in the configuration that looks like an entity ID."""
    found: set[str] = set(_ALWAYS_RELEVANT)
    pending = [settings]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, str) and _ENTITY_ID.match(value) and value.split(".", 1)[0] not in _PSEUDO_DOMAINS:
            found.add(value)
    return frozenset(found)


class OutQueue:
    """``queue.put`` used by the backend; forwards messages to the loop in order."""

    def __init__(self, hass: HomeAssistant, sink: asyncio.Queue) -> None:
        self._hass = hass
        self._sink = sink

    def put(self, msg: tuple, block: bool = True, timeout: float | None = None) -> None:  # noqa: ARG002
        self._hass.loop.call_soon_threadsafe(self._sink.put_nowait, msg)


class PanelWorker:
    """One thread per panel, like the add-on: the panel code is synchronous."""

    def __init__(self, name: str, settings: dict[str, Any], out: OutQueue, use_ha_api: bool) -> None:
        self.name = name
        self.settings = settings
        self.recv_topic = settings["panelRecvTopic"]
        self.inbox: queue.Queue = queue.Queue()
        self.panel = None
        self._out = out
        self._use_ha_api = use_ha_api
        self._thread = threading.Thread(target=self._run, name=f"nspanel-{name}", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self.inbox.put(_STOP)

    def join(self, timeout: float) -> None:
        self._thread.join(timeout)

    def _run(self) -> None:
        from .backend.panel import LovelaceUIPanel  # imported here: loads Babel/translations off the loop

        try:
            self.panel = LovelaceUIPanel(self.name, self.settings, self._out, use_ha_api=self._use_ha_api)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Failed to initialize panel '%s'", self.name)
            return
        while True:
            msg = self.inbox.get()
            if msg is _STOP:
                return
            try:
                kind, value = msg
                if kind == "MQTT:":
                    self.panel.customrecv_event_callback(value)
                elif kind == "HA:":
                    self.panel.ha_event_callback(value)
                elif kind == "TIME:":
                    self.panel.on_time_tick(value)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Panel '%s' failed while handling %s", self.name, msg)


class NSPanelRuntime:
    """Everything one config entry runs; created and stopped on the event loop."""

    def __init__(self, hass: HomeAssistant, settings: dict[str, Any]) -> None:
        self.hass = hass
        self.settings = settings
        self.use_ha_api = bool(settings.get("use_ha_api"))
        self.workers: dict[str, PanelWorker] = {}
        self._outbox: asyncio.Queue = asyncio.Queue()
        self._unsubs: list[Callable[[], None]] = []
        self._sender: asyncio.Task | None = None

    async def async_start(self) -> None:
        hass = self.hass
        bridge.async_init(hass, self._on_ha_update, referenced_entities(self.settings))
        out = OutQueue(hass, self._outbox)
        for name, panel in panel_settings(self.settings, hass.config.time_zone).items():
            self.workers[panel["panelRecvTopic"]] = PanelWorker(name, panel, out, self.use_ha_api)
        self._sender = hass.async_create_background_task(self._async_send_loop(), "nspanel_lovelace_ui sender")

        if self.use_ha_api:
            self._unsubs.append(hass.bus.async_listen(ESPHOME_EVENT, self._on_esphome_event))
        else:
            for topic in self.workers:
                self._unsubs.append(await mqtt.async_subscribe(hass, topic, self._on_mqtt_message, qos=0))
            self._unsubs.append(mqtt.async_subscribe_connection_status(hass, self._on_mqtt_connection))

        self._unsubs.append(async_track_time_change(hass, self._on_minute, second=0))
        if any(self._has_schedule(worker.settings) for worker in self.workers.values()):
            self._unsubs.append(async_track_time_interval(hass, self._on_second, timedelta(seconds=1)))

        for worker in self.workers.values():
            worker.start()
            # The add-on asked for a redraw after subscribing; the panel ignores it until a page is set.
            worker.inbox.put(("MQTT:", "event,renderCurrentPage"))

    async def async_stop(self) -> None:
        while self._unsubs:
            self._unsubs.pop()()
        for worker in self.workers.values():
            worker.stop()
        await self.hass.async_add_executor_job(self._join_workers)
        if self._sender is not None:
            self._sender.cancel()
        bridge.async_shutdown()

    def _join_workers(self) -> None:
        for worker in self.workers.values():
            worker.join(5)

    @staticmethod
    def _has_schedule(settings: dict[str, Any]) -> bool:
        return any(isinstance(settings.get(key), list) for key in ("sleepBrightness", "screenBrightness"))

    # --- inbound ------------------------------------------------------------------------

    def _broadcast(self, msg: tuple[str, str]) -> None:
        for worker in self.workers.values():
            worker.inbox.put(msg)

    @callback
    def _on_ha_update(self, entity_id: str) -> None:
        self._broadcast(("HA:", entity_id))

    @callback
    def _on_mqtt_message(self, msg: mqtt.ReceiveMessage) -> None:
        worker = self.workers.get(msg.topic)
        if worker is None:
            return
        payload = msg.payload
        if isinstance(payload, bytes):
            try:
                payload = payload.decode("utf-8")
            except UnicodeDecodeError:
                _LOGGER.warning("Ignoring non UTF-8 payload on %s", msg.topic)
                return
        if not payload:
            return
        try:
            data = json.loads(payload)
        except ValueError:
            _LOGGER.debug("Ignoring non-JSON payload on %s: %s", msg.topic, payload)
            return
        if isinstance(data, dict) and "CustomRecv" in data:
            worker.inbox.put(("MQTT:", data["CustomRecv"]))

    @callback
    def _on_esphome_event(self, event: Event) -> None:
        worker = self.workers.get(event.data.get("device_id"))
        if worker is not None and isinstance(event.data.get("CustomRecv"), str):
            worker.inbox.put(("MQTT:", event.data["CustomRecv"]))

    @callback
    def _on_mqtt_connection(self, connected: bool) -> None:
        if connected:
            self._broadcast(("MQTT:", "event,renderCurrentPage"))

    @callback
    def _on_minute(self, now: datetime) -> None:
        self._broadcast(("TIME:", "minute"))
        if now.minute == 0:
            self._broadcast(("TIME:", "hour"))

    @callback
    def _on_second(self, now: datetime) -> None:  # noqa: ARG002
        for worker in self.workers.values():
            if self._has_schedule(worker.settings):
                worker.inbox.put(("TIME:", "second"))

    # --- outbound -----------------------------------------------------------------------

    async def _async_send_loop(self) -> None:
        while True:
            msg = await self._outbox.get()
            try:
                await self._async_send(msg)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Failed to send %s", msg)

    async def _async_send(self, msg: tuple) -> None:
        if self.use_ha_api:
            service = f"{msg[0]}_nspanelui_api_call"
            data = {"data": msg[1], "command": msg[2] if len(msg) > 2 else 2}
            if not self.hass.services.has_service("esphome", service):
                _LOGGER.error("ESPHome action esphome.%s not found", service)
                return
            await self.hass.services.async_call("esphome", service, data, blocking=False)
            return
        topic, payload = msg[0], msg[1]
        await mqtt.async_publish(self.hass, topic, payload, qos=0, retain=False)
