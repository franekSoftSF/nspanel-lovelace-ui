"""Local display firmware package: <config>/nspanel_lovelace_ui/firmware/firmware.json + files.

firmware.json (written by scripts/make_firmware_package.py):
    {
      "version": 55,                      # HMI version the .tft reports in "event,startup,<v>,<model>"
      "release": "v5.2.0",
      "release_url": "https://github.com/.../releases/tag/v5.2.0",
      "files": {"eu": {"file": "nspanel-eu.tft", "sha256": "...", "size": 123},
                "us-p": {...}, "us-l": {...}},
      "berry": {"file": "autoexec.be", "sha256": "...", "size": 123}
    }
Blocking functions run in the executor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

MANIFEST = "firmware.json"
MODELS = ("eu", "us-p", "us-l")
# First HMI version built with the MDI 7.4.47 icon fonts (HMI/FIRMWARE.md).
DISPLAY_VERSION_MDI7 = 55
_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


class FirmwareError(ValueError):
    """The firmware package is missing or invalid."""


@dataclass(frozen=True)
class FirmwareFile:
    path: Path
    sha256: str
    size: int


@dataclass(frozen=True)
class FirmwarePackage:
    version: int
    release: str
    release_url: str | None
    tft: dict[str, FirmwareFile] = field(default_factory=dict)
    berry: FirmwareFile | None = None

    def files(self) -> dict[str, FirmwareFile]:
        """Served files by name (the only names the HTTP view answers)."""
        result = {item.path.name: item for item in self.tft.values()}
        if self.berry:
            result[self.berry.path.name] = self.berry
        return result


def _file(folder: Path, entry: Any, label: str) -> FirmwareFile:
    if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
        raise FirmwareError(f"{label}: expected {{file, sha256, size}}")
    name = entry["file"]
    if not _FILENAME.match(name) or name == MANIFEST:
        raise FirmwareError(f"{label}: invalid file name {name!r}")
    path = folder / name
    if not path.is_file():
        raise FirmwareError(f"{label}: {name} not found in {folder}")
    size = path.stat().st_size
    if entry.get("size") != size:
        raise FirmwareError(f"{label}: {name} has {size} bytes, manifest says {entry.get('size')}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    if digest.hexdigest() != str(entry.get("sha256", "")).lower():
        raise FirmwareError(f"{label}: {name} does not match its sha256")
    return FirmwareFile(path, digest.hexdigest(), size)


def load_package(folder: Path) -> FirmwarePackage | None:
    """None if there is no package; FirmwareError if it is broken."""
    manifest = folder / MANIFEST
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise FirmwareError(f"{manifest}: {err}") from err
    if not isinstance(data, dict):
        raise FirmwareError(f"{manifest}: expected an object")
    version = data.get("version")
    if type(version) is not int or version < 16:
        raise FirmwareError("version must be an integer of at least 16")
    files = data.get("files")
    if not isinstance(files, dict) or not files or not set(files) <= set(MODELS):
        raise FirmwareError(f"files must map some of {', '.join(MODELS)} to a file")
    tft = {model: _file(folder, entry, model) for model, entry in files.items()}
    berry = _file(folder, data["berry"], "berry") if data.get("berry") else None
    names = [item.path.name for item in tft.values()] + ([berry.path.name] if berry else [])
    if len(names) != len(set(names)):
        raise FirmwareError("each file may be listed only once")
    release_url = data.get("release_url")
    if release_url is not None and (not isinstance(release_url, str) or urlsplit(release_url).scheme != "https"):
        raise FirmwareError("release_url must be an https URL")
    return FirmwarePackage(version, str(data.get("release") or version), release_url, tft, berry)


def validate_base_url(url: str) -> str:
    """The panel downloads over plain HTTP (Berry tcpclient); no path, no credentials."""
    parts = urlsplit(url)
    if (parts.scheme != "http" or not parts.hostname or parts.username or parts.password
            or parts.path not in ("", "/") or parts.query or parts.fragment
            or any(char.isspace() or char == ";" for char in url)):
        raise FirmwareError("firmware_base_url must look like http://192.168.1.10:8123")
    return f"http://{parts.netloc}"
