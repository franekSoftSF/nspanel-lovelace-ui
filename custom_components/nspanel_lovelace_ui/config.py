"""Reading, validating and importing panels.yaml (blocking: run in the executor)."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any

import yaml

from .backend.config_manager import ConfigError, import_yaml, parse_yaml, validate


class PathOutsideConfigError(ConfigError):
    """The file is not inside the Home Assistant configuration folder."""


class ConfigExistsError(ConfigError):
    """An import would overwrite an existing panels.yaml."""


@dataclass
class ImportResult:
    format: str
    warnings: list[str] = field(default_factory=list)
    panels: list[str] = field(default_factory=list)


def resolve_path(config_dir: str, relative: str) -> Path:
    """Resolve a user-entered path; only files inside the HA config folder are allowed."""
    base = Path(config_dir).resolve()
    path = (base / relative).resolve()
    if path != base and base not in path.parents:
        raise PathOutsideConfigError(relative)
    return path


class _DuplicateKeyLoader(yaml.SafeLoader):
    """PyYAML semantics (the last duplicate wins), but remember every duplicate."""

    def __init__(self, stream: str) -> None:
        super().__init__(stream)
        self.duplicates: list[str] = []

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        self.flatten_mapping(node)
        seen: set[Any] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                self.duplicates.append(f"line {key_node.start_mark.line + 1}: duplicate key '{key}' (the last one is used)")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _parse_lenient(text: str) -> tuple[dict[str, Any], list[str]]:
    """Strict parse (add-on editor rules); duplicate keys only warn, like AppDaemon and the add-on runtime."""
    try:
        return parse_yaml(text), []
    except ConfigError as err:
        if not str(err).startswith("Invalid YAML: Duplicate YAML key"):
            raise
    loader = _DuplicateKeyLoader(text)
    try:
        data = loader.get_single_data()
    except yaml.YAMLError as err:
        raise ConfigError(f"Invalid YAML: {err}") from err
    finally:
        loader.dispose()
    if not isinstance(data, dict):
        raise ConfigError("Configuration must be a YAML mapping.")
    return data, loader.duplicates


def load_config(path: Path) -> tuple[dict[str, Any], list[str]]:
    """Parse and validate panels.yaml; returns the config and non-fatal warnings."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise ConfigError(f"File not found: {path}") from err
    except OSError as err:
        raise ConfigError(f"Cannot read {path}: {err}") from err
    data, warnings = _parse_lenient(text)
    config = validate(data)
    if type(config.get("firmware_download", True)) is not bool:
        raise ConfigError("firmware_download must be true or false")
    for name, panel in config["nspanels"].items():
        font_id = panel.get("largeIconFontId", 7 if panel.get("model", "eu") == "us-p" else 8)
        if type(font_id) is not int or not 0 <= font_id <= 9:
            raise ConfigError(f"{name}.largeIconFontId must be a font ID from 0 to 9 (the HMI reads one digit)")
        if panel.get("weatherIcons", "color") not in ("color", "font"):
            raise ConfigError(f"{name}.weatherIcons must be color or font")
        base = panel.get("weatherPictureBase")
        if base is not None and (type(base) is not int or not 0 <= base <= 1000):
            raise ConfigError(f"{name}.weatherPictureBase must be the picture ID of 00-main-clear-day")
        if "timeTemplate" in panel and not (isinstance(panel["timeTemplate"], str) and panel["timeTemplate"].strip()):
            raise ConfigError(f"{name}.timeTemplate must be a template text")
        if config.get("use_ha_api"):
            continue
        for key in ("panelRecvTopic", "panelSendTopic"):
            topic = panel[key]
            if any(char in topic for char in "+#") or "\x00" in topic:
                raise ConfigError(f"{key} must be a plain MQTT topic without wildcards: {topic}")
    return config, warnings


APPS_FOLDERS = ("appdaemon/apps", "apps")
_APP_CLASS = re.compile(r"^[ \t]+(class:[ \t]*NsPanelLovelaceUIManager|module:[ \t]*nspanel-lovelace-ui)[ \t]*(#.*)?$",
                        re.MULTILINE)
_SECRET = re.compile(r"!secret[ \t]+([A-Za-z0-9_.-]+)")


def find_appdaemon_apps(config_dir: str) -> str | None:
    """Relative path of the AppDaemon apps file with an NSPanel app (the import default).

    AppDaemon reads every .yaml below its apps folder: the top-level apps.yaml comes first, then
    the other files (subfolders too). Only a file that defines the app (class/module line) counts.
    """
    base = Path(config_dir)
    for folder in APPS_FOLDERS:
        root = base / folder
        if not root.is_dir():
            continue
        files = sorted(root.rglob("*.y*ml"), key=lambda p: (p.name != "apps.yaml", len(p.parts), str(p)))
        for path in files[:200]:
            if path.suffix not in (".yaml", ".yml") or not path.is_file():
                continue
            try:
                if _APP_CLASS.search(path.read_text(encoding="utf-8")):
                    return path.relative_to(base).as_posix()
            except (OSError, UnicodeDecodeError):
                continue
    return None


def _resolve_secrets(text: str, source: Path, config_dir: Path | None) -> str:
    """Replace ``!secret name`` with the value from the nearest secrets.yaml (AppDaemon or HA)."""
    names = set(_SECRET.findall(text))
    if not names:
        return text
    folders = [source.parent, source.parent.parent] + ([config_dir] if config_dir else [])
    secrets: dict[str, Any] = {}
    for folder in reversed(folders):  # the nearest file wins
        path = folder / "secrets.yaml"
        if path.is_file():
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as err:
                raise ConfigError(f"Cannot read {path}: {err}") from err
            if isinstance(data, dict):
                secrets.update(data)
    missing = sorted(name for name in names if name not in secrets)
    if missing:
        raise ConfigError(f"Secrets not found in secrets.yaml: {', '.join(missing)}")
    return _SECRET.sub(lambda match: json.dumps(secrets[match.group(1)], ensure_ascii=False), text)


def disable_appdaemon_apps(source: Path, names: list[str]) -> Path:
    """Add ``disable: true`` to the given apps in apps.yaml (text edit, comments kept).

    A copy of the original is written first (apps.yaml.nspanel-backup, never overwritten).
    Returns the backup path.
    """
    raw = source.read_bytes().decode("utf-8")
    lines = raw.splitlines(keepends=True)
    newline = "\r\n" if "\r\n" in raw else "\n"
    for name in names:
        header = re.compile(rf"^{re.escape(name)}[ \t]*:[ \t]*(#.*)?$")
        start = next((i for i, line in enumerate(lines) if header.match(line.rstrip("\r\n"))), None)
        if start is None:
            raise ConfigError(f"App {name} not found at the top level of {source.name}")
        end = next((i for i in range(start + 1, len(lines))
                    if lines[i].strip() and not lines[i].startswith((" ", "\t", "#"))), len(lines))
        block = range(start + 1, end)
        existing = next((i for i in block if re.match(r"^[ \t]+disable[ \t]*:", lines[i])), None)
        if existing is not None:
            indent = lines[existing][:len(lines[existing]) - len(lines[existing].lstrip())]
            lines[existing] = f"{indent}disable: true{newline}"
            continue
        child = next((lines[i] for i in block if lines[i].strip() and not lines[i].lstrip().startswith("#")), None)
        if child is None:
            raise ConfigError(f"App {name} in {source.name} has no settings")
        indent = child[:len(child) - len(child.lstrip())]
        if not lines[start].endswith(("\n", "\r")):
            lines[start] += newline
        lines.insert(start + 1, f"{indent}disable: true{newline}")
    backup = source.with_name(source.name + ".nspanel-backup")
    if not backup.exists():
        shutil.copy2(source, backup)
    tmp = source.with_name(source.name + ".tmp")
    tmp.write_bytes("".join(lines).encode("utf-8"))
    os.replace(tmp, source)
    return backup


def import_config(source: Path, target: Path, config_dir: Path | None = None,
                  time_zone: str | None = None) -> ImportResult:
    """Convert an AppDaemon apps.yaml (or an add-on panels.yaml) into ``target``.

    Never overwrites: an existing target raises ConfigExistsError. ``!secret`` values are
    taken from secrets.yaml next to apps.yaml, one folder up, or in ``config_dir``.
    """
    if target.exists():
        raise ConfigExistsError(str(target))
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as err:
        raise ConfigError(f"Cannot read {source}: {err}") from err
    result = import_yaml(_resolve_secrets(text, source, config_dir),
                         time_zone=time_zone or "Europe/Berlin", integration=True)
    if result["errors"]:
        raise ConfigError("; ".join(result["errors"]))
    target.parent.mkdir(parents=True, exist_ok=True)
    header = (f"# Imported from {source.name} ({result['format']} format) by the NSPanel Lovelace UI integration.\n"
              "# Review the warnings in the Home Assistant log / notification.\n")
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(header + yaml.safe_dump(result["config"], allow_unicode=True, sort_keys=False),
                   encoding="utf-8")
    os.replace(tmp, target)
    return ImportResult(result["format"], list(result["warnings"]), list(result["config"]["nspanels"]))
