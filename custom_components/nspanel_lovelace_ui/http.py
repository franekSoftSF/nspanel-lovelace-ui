"""Serve the local firmware package to the panels (Tasmota FlashNextion / UpdateDriverVersion).

Tasmota cannot authenticate, so the view is public but only answers under a random token that
changes on every Home Assistant start, and only for the files listed in firmware.json. The Berry
driver needs plain HTTP, Range requests (resume) and a Content-Length header: aiohttp's
FileResponse provides all three.
"""
from __future__ import annotations

from http import HTTPStatus
import secrets

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .firmware import FirmwarePackage

URL_PREFIX = f"/api/{DOMAIN}/firmware"
DATA_HTTP = f"{DOMAIN}_http"


class FirmwareView(HomeAssistantView):
    """GET /api/nspanel_lovelace_ui/firmware/{token}/{filename}."""

    url = URL_PREFIX + "/{token}/{filename}"
    name = f"api:{DOMAIN}:firmware"
    requires_auth = False

    def __init__(self, state: "FirmwareHttpState") -> None:
        self._state = state

    async def get(self, request: web.Request, token: str, filename: str) -> web.StreamResponse:
        package = self._state.package
        if package is None or not secrets.compare_digest(token, self._state.token):
            return web.Response(status=HTTPStatus.NOT_FOUND)
        item = package.files().get(filename)
        if item is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        content_type = "text/plain" if filename.endswith(".be") else "application/octet-stream"
        return web.FileResponse(item.path, headers={"Content-Type": content_type, "Cache-Control": "no-store"})


class FirmwareHttpState:
    """Shared between the (permanently registered) view and the config entry."""

    def __init__(self) -> None:
        self.token = secrets.token_urlsafe(16)
        self.package: FirmwarePackage | None = None

    def path(self, filename: str) -> str:
        return f"{URL_PREFIX}/{self.token}/{filename}"


def async_get_http_state(hass: HomeAssistant) -> FirmwareHttpState:
    """Register the view once per Home Assistant run (views cannot be removed)."""
    state = hass.data.get(DATA_HTTP)
    if state is None:
        state = hass.data[DATA_HTTP] = FirmwareHttpState()
        hass.http.register_view(FirmwareView(state))
    return state
