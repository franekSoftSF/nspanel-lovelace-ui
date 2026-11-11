"""In-process Home Assistant bridge for the panel backend.

Replaces the add-on's websocket client (same module API: get_entity_data, call_service,
get_template, get_forecast, sensor_display_precision, ...). The panel code runs in one
worker thread per panel; every function here is called from those threads and hands work
to the event loop thread-safely. Functions prefixed with ``async_`` run on the loop.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime
import logging
import threading
import time
from typing import Any

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    TrackTemplate,
    TrackTemplateResult,
    TrackTemplateResultInfo,
    async_track_template_result,
)
from homeassistant.helpers.template import Template

_LOGGER = logging.getLogger(__name__)

FORECAST_CACHE_SECONDS = 300
FORECAST_RETRY_SECONDS = 30
FORECAST_TIMEOUT_SECONDS = 8

hass: HomeAssistant | None = None
on_ha_update: Callable[[str], None] | None = None
ws_connected = False  # kept for API compatibility: True while the bridge is active

request_lock = threading.RLock()
known_templates: dict[str, set[str]] = {}  # expression -> displayed entity IDs
template_cache: dict[str, dict[str, Any]] = {}
_template_trackers: dict[str, TrackTemplateResultInfo] = {}
sensor_display_precision: dict[str, int] = {}
forecast_lock = threading.RLock()
forecast_cache: dict[tuple[str, str], dict[str, Any]] = {}
_unsubs: list[Callable[[], None]] = []
# Entity IDs whose state changes reach the panels; None = all (add-on behaviour).
relevant_entities: frozenset[str] | None = None


class _StateView:
    """Read-only view of hass.states, shaped like the add-on's state cache."""

    def __len__(self) -> int:
        return 0 if hass is None else len(hass.states.async_entity_ids())

    def __contains__(self, entity_id: object) -> bool:
        return hass is not None and isinstance(entity_id, str) and hass.states.get(entity_id) is not None

    def __getitem__(self, entity_id: str) -> dict[str, Any]:
        data = get_entity_data(entity_id)
        if data is None:
            raise KeyError(entity_id)
        return data


home_assistant_entity_state_cache = _StateView()


def state_to_dict(state: State) -> dict[str, Any]:
    """Websocket-compatible state dict: plain containers and ISO timestamps."""
    return {
        "entity_id": state.entity_id,
        "state": state.state,
        "attributes": _plain(state.attributes),
        "last_changed": state.last_changed.isoformat(),
        "last_updated": state.last_updated.isoformat(),
    }


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


# --- lifecycle (event loop) -------------------------------------------------------------

@callback
def async_init(hass_: HomeAssistant, on_update: Callable[[str], None],
               entities: frozenset[str] | None = None) -> None:
    """Bind the bridge to Home Assistant and start listening for state changes.

    ``entities`` limits state_changed forwarding to the configured entities (issue #1465:
    the add-on forwarded every state change of the whole installation to every panel).
    Template results are tracked separately and always forwarded.
    """
    global hass, on_ha_update, ws_connected, relevant_entities
    async_shutdown()
    hass = hass_
    on_ha_update = on_update
    ws_connected = True
    relevant_entities = entities

    @callback
    def _state_changed(event: Event) -> None:
        entity_id = event.data.get("entity_id")
        if entity_id and (relevant_entities is None or entity_id in relevant_entities):
            send_entity_update(entity_id)

    @callback
    def _registry_updated(event: Event) -> None:
        _async_refresh_display_precision()

    _unsubs.append(hass.bus.async_listen(EVENT_STATE_CHANGED, _state_changed))
    _unsubs.append(hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, _registry_updated))
    _async_refresh_display_precision()


@callback
def async_shutdown() -> None:
    global hass, on_ha_update, ws_connected, relevant_entities
    while _unsubs:
        _unsubs.pop()()
    with request_lock:
        for tracker in _template_trackers.values():
            tracker.async_remove()
        _template_trackers.clear()
        template_cache.clear()
        known_templates.clear()
    with forecast_lock:
        forecast_cache.clear()
    sensor_display_precision.clear()
    hass = None
    on_ha_update = None
    ws_connected = False
    relevant_entities = None


@callback
def _async_refresh_display_precision() -> None:
    """Same resolution as the frontend's display registry: user option, then suggested."""
    global sensor_display_precision
    if hass is None:
        return
    current: dict[str, int] = {}
    for entry in er.async_get(hass).entities.values():
        if entry.domain != "sensor":
            continue
        options = entry.options.get("sensor") or {}
        precision = options.get("display_precision")
        if precision is None:
            precision = options.get("suggested_display_precision")
        if type(precision) is int and 0 <= precision <= 100:
            current[entry.entity_id] = precision
    previous = sensor_display_precision
    sensor_display_precision = current
    for entity_id in previous.keys() | current.keys():
        if previous.get(entity_id) != current.get(entity_id):
            send_entity_update(entity_id)


# --- helpers ----------------------------------------------------------------------------

def _in_loop() -> bool:
    if hass is None:
        return False
    try:
        return asyncio.get_running_loop() is hass.loop
    except RuntimeError:
        return False


def _call_soon(func: Callable[..., Any], *args: Any) -> bool:
    if hass is None:
        return False
    if _in_loop():
        func(*args)
    else:
        hass.loop.call_soon_threadsafe(func, *args)
    return True


def send_entity_update(entity_id: str) -> None:
    if on_ha_update is not None:
        on_ha_update(entity_id)


# --- states -----------------------------------------------------------------------------

def get_entity_data(entity_id: str) -> dict[str, Any] | None:
    if hass is None or not isinstance(entity_id, str):
        return None
    state = hass.states.get(entity_id)
    return None if state is None else state_to_dict(state)


def is_existent(entity_id: str) -> bool:
    return entity_id in home_assistant_entity_state_cache


# --- actions ----------------------------------------------------------------------------

def _log_failure(description: str) -> Callable[[asyncio.Future], None]:
    def _done(future: asyncio.Future) -> None:
        if not future.cancelled() and future.exception() is not None:
            _LOGGER.error("%s failed: %s", description, future.exception())
    return _done


def call_service(entity_name: str | None, domain: str, service: str, service_data: dict) -> bool:
    """Fire-and-forget service call (the add-on did not wait for the result either)."""
    if hass is None:
        return False
    if not hass.services.has_service(domain, service):
        _LOGGER.error("Unknown Home Assistant action %s.%s", domain, service)
        return False
    target = {"entity_id": entity_name} if entity_name else None
    coro = hass.services.async_call(domain, service, dict(service_data or {}), blocking=True, target=target)
    if _in_loop():
        hass.async_create_task(coro).add_done_callback(_log_failure(f"{domain}.{service}"))
    else:
        asyncio.run_coroutine_threadsafe(coro, hass.loop).add_done_callback(_log_failure(f"{domain}.{service}"))
    return True


def send_msg_to_panel(service: str, service_data: dict) -> bool:
    """ESPHome firmware variant (use_ha_api): esphome.<device>_nspanelui_api_call."""
    return call_service(None, "esphome", service, service_data)


def execute_script(entity_name: str, domain: str, service: str, service_data: dict, timeout: float = 0.4) -> dict:
    """Call an action that returns a response; blocks the calling worker thread up to timeout."""
    if hass is None or _in_loop():
        return {}
    coro = hass.services.async_call(domain, service, dict(service_data or {}), blocking=True,
                                    target={"entity_id": [entity_name]}, return_response=True)
    future = asyncio.run_coroutine_threadsafe(coro, hass.loop)
    try:
        response = future.result(timeout)
    except FutureTimeout:
        future.cancel()
        _LOGGER.warning("Timed out waiting for %s.%s", domain, service)
        return {}
    except Exception as err:  # noqa: BLE001 - any action failure means "no data"
        _LOGGER.debug("%s.%s failed: %s", domain, service, err)
        return {}
    return response if isinstance(response, dict) else {}


def get_forecast(entity_id: str, forecast_type: str) -> dict:
    """Serve the last good forecast while one background request refreshes it."""
    key = (entity_id, forecast_type)
    with forecast_lock:
        entry = forecast_cache.setdefault(key, {"response": {}, "expires": 0, "pending": False})
        if not entry["pending"] and time.monotonic() >= entry["expires"]:
            entry["pending"] = True
            threading.Thread(target=_refresh_forecast, args=(key, entry), daemon=True,
                             name="nspanel-forecast").start()
        return entry["response"]


def _refresh_forecast(key: tuple[str, str], entry: dict[str, Any]) -> None:
    entity_id, forecast_type = key
    changed = False
    try:
        response = execute_script(entity_id, "weather", "get_forecasts", {"type": forecast_type},
                                  timeout=FORECAST_TIMEOUT_SECONDS)
        response = _plain(response)
        data = response.get(entity_id)
        forecast = data.get("forecast") if isinstance(data, dict) else None
        valid = isinstance(forecast, list) and bool(forecast) and all(
            isinstance(item, dict) and isinstance(item.get("datetime"), str) for item in forecast)
        if valid:
            try:
                for item in forecast:
                    datetime.fromisoformat(item["datetime"])
            except ValueError:
                valid = False
        with forecast_lock:
            if valid:
                changed = entry["response"] != response
                entry["response"] = response
            entry["expires"] = time.monotonic() + (FORECAST_CACHE_SECONDS if valid else FORECAST_RETRY_SECONDS)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Failed to refresh forecast for %s", entity_id)
        with forecast_lock:
            entry["expires"] = time.monotonic() + FORECAST_RETRY_SECONDS
    finally:
        with forecast_lock:
            entry["pending"] = False
    if changed:
        send_entity_update(entity_id)


# --- templates --------------------------------------------------------------------------

def _template_key(template: str) -> str:
    return template[3:] if template.startswith("ha:") else template


def cache_template(template: str, displayed_entity_id: str | None = None) -> bool:
    """Subscribe to a template; the first render arrives asynchronously, like the add-on."""
    if not isinstance(template, str) or not template:
        raise ValueError("Invalid template")
    template = _template_key(template)
    with request_lock:
        targets = known_templates.setdefault(template, set())
        if displayed_entity_id is not None:
            targets.add(displayed_entity_id)
        if template in _template_trackers or template in template_cache:
            return True
        # Mark as pending so concurrent callers do not subscribe twice.
        template_cache[template] = {"result": None, "listener-entities": [], "pending": True}
    return _call_soon(_async_track_template, template)


@callback
def _async_track_template(template: str) -> None:
    if hass is None:
        return

    @callback
    def _result(event: Event | None, updates: list[TrackTemplateResult]) -> None:
        result = updates.pop().result
        if isinstance(result, TemplateError):
            _LOGGER.warning("Template error in %r: %s", template, result)
            result = None
        listeners = tracker.listeners.get("entities", []) if tracker is not None else []
        with request_lock:
            previous = template_cache.get(template)
            template_cache[template] = {"result": result, "listener-entities": sorted(listeners)}
            changed = previous is None or previous.get("pending") or previous.get("result") != result
            targets = tuple(known_templates.get(template, ())) if changed else ()
        for entity_id in targets:
            send_entity_update(entity_id)

    tracker = None
    try:
        tracker = async_track_template_result(
            hass, [TrackTemplate(Template(template, hass), None)], _result, strict=False)
    except TemplateError as err:
        _LOGGER.error("Invalid template %r: %s", template, err)
        with request_lock:
            template_cache[template] = {"result": None, "listener-entities": []}
        return
    with request_lock:
        _template_trackers[template] = tracker
    tracker.async_refresh()


def get_template(template: str, displayed_entity_id: str | None = None) -> Any:
    cache_template(template, displayed_entity_id)
    with request_lock:
        return template_cache.get(_template_key(template), {}).get("result")


def get_template_listener_entities(template: str) -> list[str]:
    with request_lock:
        return list(template_cache.get(_template_key(template), {}).get("listener-entities", []))
