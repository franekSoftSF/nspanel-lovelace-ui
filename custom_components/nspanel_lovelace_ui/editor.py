"""Card editor: sidebar panel (admins only) and its websocket API.

The editor edits the configuration file this integration reads (panels.yaml): it loads the
file with a revision (SHA-256), validates with the shared schema (editor_schema.py, the same
rules the integration uses when it loads the file), saves atomically with a backup of the
previous file and detects changes on disk since the editor loaded it.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Any

import voluptuous as vol
import yaml

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.template import Template

from . import editor_schema
from .backend import wifi as wifi_qr
from .config import ConfigError, _parse_lenient, read_secrets, resolve_path
from .const import CONF_CONFIG_FILE, DOMAIN

PANEL_URL = "nspanel-lovelace-ui"
PANEL_ELEMENT = "nspanel-card-editor"
STATIC_URL = f"/{DOMAIN}_static"
FRONTEND_DIR = Path(__file__).parent / "frontend"
HEADER = ("# NSPanel Lovelace UI configuration - saved by the card editor of the integration.\n"
          "# The previous version is kept next to this file as {name}.bak\n")
BACKUPS = 5
DATA_EDITOR = f"{DOMAIN}_editor"


def _revision(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _has_comments(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines()]
    return any(line.startswith("#") and "saved by the card editor" not in line
               and "previous version is kept" not in line and "Imported from" not in line
               and "Review the warnings" not in line for line in lines)


def read_file(path: Path) -> dict[str, Any]:
    """Blocking: the file as the editor sees it."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return {"exists": False, "revision": None, "config": {"nspanels": {}}, "yaml": "nspanels: {}\n",
                "has_comments": False, "parse_error": None}
    text = raw.decode("utf-8", errors="replace")
    result = {"exists": True, "revision": _revision(raw), "yaml": text, "has_comments": _has_comments(text),
              "config": None, "parse_error": None}
    try:
        result["config"], _ = _parse_lenient(text)
    except ConfigError as err:
        result["parse_error"] = str(err)
    return result


def dump(config: dict[str, Any], name: str) -> str:
    return HEADER.format(name=name) + yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=120)


def write_file(path: Path, text: str, revision: str | None, force: bool) -> str:
    """Blocking: atomic write with backups; raises editor_schema.ConflictError on a changed file."""
    current = path.read_bytes() if path.exists() else None
    if not force and (None if current is None else _revision(current)) != revision:
        raise editor_schema.ConflictError
    path.parent.mkdir(parents=True, exist_ok=True)
    if current is not None:
        _atomic_write(path.with_name(path.name + ".bak"), current)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backups = path.parent / ".nspanel-backups"
        backups.mkdir(exist_ok=True)
        _atomic_write(backups / f"{path.name}.{stamp}", current)
        for old in sorted(backups.glob(f"{path.name}.*"))[:-BACKUPS]:
            old.unlink(missing_ok=True)
    data = text.encode("utf-8")
    _atomic_write(path, data)
    return _revision(data)


def _atomic_write(path: Path, data: bytes) -> None:
    fd, temporary = tempfile.mkstemp(prefix=".nspanel-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


# --- registration ---------------------------------------------------------------------------

async def async_setup_editor(hass: HomeAssistant) -> None:
    """Static files, websocket commands and the sidebar panel (once per Home Assistant run)."""
    if hass.data.get(DATA_EDITOR):
        return
    hass.data[DATA_EDITOR] = True
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=False)])
    for command in (ws_load, ws_schema, ws_icons, ws_default_icons, ws_validate, ws_save, ws_reload, ws_yaml,
                    ws_wifi):
        websocket_api.async_register_command(hass, command)


async def async_register_panel(hass: HomeAssistant) -> None:
    version = (Path(__file__).parent / "frontend" / "nspanel-editor.js").stat().st_mtime_ns
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title="NSPanel",
        sidebar_icon="mdi:tablet-dashboard",
        module_url=f"{STATIC_URL}/nspanel-editor.js?v={version}",
        require_admin=True,
        config={"domain": DOMAIN},
    )


@callback
def async_remove_panel(hass: HomeAssistant) -> None:
    frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)


# --- websocket API (admin only) ---------------------------------------------------------------

def _entry(hass: HomeAssistant):
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise editor_schema.EditorError("not_configured")
    return entries[0]


def _path(hass: HomeAssistant) -> Path:
    return resolve_path(hass.config.config_dir, _entry(hass).data[CONF_CONFIG_FILE])


def _entity_ids(hass: HomeAssistant) -> set[str]:
    return set(hass.states.async_entity_ids())


async def _secrets(hass: HomeAssistant) -> dict[str, Any]:
    """secrets.yaml values; only their names leave the server (and a Wi-Fi QR preview for admins)."""
    try:
        path = _path(hass)
    except (editor_schema.EditorError, ConfigError):
        return {}
    return await hass.async_add_executor_job(read_secrets, path, hass.config.config_dir)


async def _issues(hass: HomeAssistant, config: Any) -> list:
    return editor_schema.collect_issues(config, _entity_ids(hass), set(await _secrets(hass)))


def _send_error(connection, msg_id: int, err: Exception) -> None:
    code = getattr(err, "code", "error")
    connection.send_error(msg_id, code, str(err))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/editor/load"})
@websocket_api.async_response
async def ws_load(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    try:
        path = _path(hass)
    except (editor_schema.EditorError, ConfigError) as err:
        _send_error(connection, msg["id"], err)
        return
    data = await hass.async_add_executor_job(read_file, path)
    data["path"] = _entry(hass).data[CONF_CONFIG_FILE]
    issues = []
    if data["config"] is not None:
        issues = await _issues(hass, data["config"])
    data["issues"] = [issue.as_dict() for issue in issues]
    data["secrets"] = sorted(await _secrets(hass))  # names only
    connection.send_result(msg["id"], data)


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/editor/schema"})
@callback
def ws_schema(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    connection.send_result(msg["id"], editor_schema.schema_json())


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/editor/icons"})
@websocket_api.async_response
async def ws_icons(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Icon picker data: every icon of the panel font with aliases and categories."""
    connection.send_result(msg["id"], await hass.async_add_executor_job(editor_schema.icon_picker))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/editor/default_icons",
                                  vol.Required("entities"): [str]})
@callback
def ws_default_icons(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Icon the panel shows for each entity when the row sets none (current state and device class)."""
    icons = {entity_id: editor_schema.default_icon(entity_id, hass.states.get(entity_id))
             for entity_id in msg["entities"][:500]}
    connection.send_result(msg["id"], {"icons": icons})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/editor/validate",
                                  vol.Required("config"): dict})
@websocket_api.async_response
async def ws_validate(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    issues = await _issues(hass, msg["config"])
    connection.send_result(msg["id"], {"issues": [issue.as_dict() for issue in issues]})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/editor/yaml",
                                  vol.Optional("config"): dict, vol.Optional("yaml"): str})
@websocket_api.async_response
async def ws_yaml(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """config -> YAML text (preview), or YAML text -> config (raw YAML mode)."""
    if "yaml" in msg:
        try:
            config, warnings = _parse_lenient(msg["yaml"])
        except ConfigError as err:
            connection.send_error(msg["id"], "invalid_yaml", str(err))
            return
        connection.send_result(msg["id"], {"config": config, "warnings": warnings})
        return
    name = Path(_entry(hass).data[CONF_CONFIG_FILE]).name
    connection.send_result(msg["id"], {"yaml": dump(msg.get("config") or {}, name)})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/editor/save",
                                  vol.Required("config"): dict,
                                  vol.Required("revision"): vol.Any(str, None),
                                  vol.Optional("force", default=False): bool})
@websocket_api.async_response
async def ws_save(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Server-side validation, then an atomic write; errors block the save, warnings do not."""
    try:
        entry = _entry(hass)
        path = _path(hass)
    except (editor_schema.EditorError, ConfigError) as err:
        _send_error(connection, msg["id"], err)
        return
    issues = await _issues(hass, msg["config"])
    if any(issue.severity == "error" for issue in issues):
        connection.send_result(msg["id"], {"saved": False, "reason": "invalid",
                                           "issues": [issue.as_dict() for issue in issues]})
        return
    text = dump(msg["config"], path.name)
    try:
        revision = await hass.async_add_executor_job(write_file, path, text, msg["revision"], msg["force"])
    except editor_schema.ConflictError:
        connection.send_result(msg["id"], {"saved": False, "reason": "conflict"})
        return
    except OSError as err:
        connection.send_error(msg["id"], "write_failed", str(err))
        return
    connection.send_result(msg["id"], {"saved": True, "revision": revision, "yaml": text,
                                       "issues": [issue.as_dict() for issue in issues],
                                       "backup": f"{entry.data[CONF_CONFIG_FILE]}.bak"})


def _qr_svg(text: str) -> str:
    import segno  # noqa: PLC0415 - only the editor preview needs it

    return segno.make(text, error="m").svg_inline(scale=5, border=2, dark="#000", light="#fff")


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/editor/wifi",
                                  vol.Optional("parse"): str, vol.Optional("wifi"): dict,
                                  vol.Optional("text"): str})
@websocket_api.async_response
async def ws_wifi(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """QR card helper of the editor.

    parse: WIFI: text -> wifi fields; text: plain qrCode -> QR preview (SVG);
    wifi: fields -> QR preview with the real password, from the same source the panel uses (text,
    template, entity or secret). Only the picture goes back, never the password, and nothing is logged.
    """
    if "parse" in msg:
        connection.send_result(msg["id"], {"wifi": wifi_qr.parse(msg["parse"])})
        return
    if "text" in msg:
        try:
            svg = await hass.async_add_executor_job(_qr_svg, msg["text"][:2000])
        except Exception:  # noqa: BLE001
            svg = None
        connection.send_result(msg["id"], {"svg": svg})
        return
    wifi = msg.get("wifi") or {}
    security = wifi.get("security", "WPA")
    password, source = "", None
    if security != "nopass":
        if wifi.get("password") not in (None, ""):
            password, source = str(wifi["password"]), "password"
            if password.startswith("ha:"):
                try:
                    password = str(Template(password[3:], hass).async_render(parse_result=False))
                except TemplateError:
                    password = ""
        elif wifi.get("passwordEntity"):
            state = hass.states.get(str(wifi["passwordEntity"]))
            source = "passwordEntity"
            password = state.state if state and state.state not in ("unknown", "unavailable") else ""
        elif wifi.get("passwordSecret"):
            source = "passwordSecret"
            password = str((await _secrets(hass)).get(str(wifi["passwordSecret"]), ""))
    text = wifi_qr.build(str(wifi.get("ssid", "")), security, password, wifi.get("hidden") is True)
    try:
        svg = await hass.async_add_executor_job(_qr_svg, text)
    except Exception:  # noqa: BLE001 - e.g. segno missing or text too long
        svg = None
    connection.send_result(msg["id"], {"svg": svg, "source": source, "password": bool(password),
                                       "length": len(text)})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/editor/reload"})
@websocket_api.async_response
async def ws_reload(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Reload the integration: the panels start again with the saved file (no restart of HA)."""
    try:
        entry = _entry(hass)
    except editor_schema.EditorError as err:
        _send_error(connection, msg["id"], err)
        return
    ok = await hass.config_entries.async_reload(entry.entry_id)
    connection.send_result(msg["id"], {"reloaded": bool(ok), "state": entry.state.value,
                                       "reason": entry.reason})
