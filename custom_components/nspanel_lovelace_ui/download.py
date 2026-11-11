"""Download the display firmware package (nspanel-firmware.zip) from the GitHub release.

The integration version names the release (5.2.1 -> tag v5.2.1). The zip is written next to the
firmware folder, where firmware.install_zip() checks every file (names, sizes, SHA-256 from
firmware.json) before it replaces the package, exactly like a zip the user dropped there.
"""
from __future__ import annotations

import os
from pathlib import Path

import aiohttp
from awesomeversion import AwesomeVersion, AwesomeVersionException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .firmware import ZIP_MAX_BYTES, FirmwareError, FirmwarePackage

RELEASES_URL = "https://github.com/franekSoftSF/nspanel-lovelace-ui/releases/download"
ASSET = "nspanel-firmware.zip"
TIMEOUT = aiohttp.ClientTimeout(total=600, sock_read=60)


def release_tag(integration_version: str) -> str:
    return f"v{integration_version}"


def asset_url(tag: str) -> str:
    return f"{RELEASES_URL}/{tag}/{ASSET}"


def needs_download(package: FirmwarePackage | None, tag: str) -> bool:
    """True if there is no package, or it comes from an older release than the integration."""
    if package is None:
        return True
    try:
        return AwesomeVersion(package.release.lstrip("v")) < AwesomeVersion(tag.lstrip("v"))
    except AwesomeVersionException:
        return False  # a self-built package with its own release name: keep it


async def async_download_package(hass: HomeAssistant, tag: str, base: Path) -> Path:
    """Download the release asset to ``base``/nspanel-firmware.zip; FirmwareError on failure."""
    url = asset_url(tag)
    data = bytearray()
    try:
        async with async_get_clientsession(hass).get(url, timeout=TIMEOUT) as response:
            if response.status != 200:
                raise FirmwareError(f"{url}: HTTP {response.status}")
            if (getattr(response, "content_length", None) or 0) > ZIP_MAX_BYTES:
                raise FirmwareError(f"{url}: too large for a firmware package")
            async for chunk in response.content.iter_chunked(1 << 16):
                data += chunk
                if len(data) > ZIP_MAX_BYTES:
                    raise FirmwareError(f"{url}: too large for a firmware package")
    except (aiohttp.ClientError, TimeoutError) as err:
        raise FirmwareError(f"{url}: {err or type(err).__name__}") from err

    def _write() -> Path:
        base.mkdir(parents=True, exist_ok=True)
        part = base / f"{ASSET}.part"
        part.write_bytes(bytes(data))
        target = base / ASSET
        os.replace(part, target)
        return target

    try:
        return await hass.async_add_executor_job(_write)
    except OSError as err:
        raise FirmwareError(f"{base}: {err}") from err
