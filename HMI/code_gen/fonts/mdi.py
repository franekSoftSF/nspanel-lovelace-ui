"""Pinned Material Design Icons release: download with checksum, code point mapping.

Nextion fonts only address 16-bit code points, so MDI's U+F0001.. are shifted down:
    nextion = mdi - 0xF0001 + 0xE000      (the scheme this project has always used)
MDI 7.4.47 ends at U+F1D17 -> U+FD16, still below the specials at U+FE00.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request

MDI_VERSION = "7.4.47"
FILES = {
    # name: (url, sha256)
    "meta.json": (f"https://cdn.jsdelivr.net/npm/@mdi/svg@{MDI_VERSION}/meta.json",
                  "ed9d7c7a5ca3ce7dee023fb6c1d62715dbec5b27503d268cbc10b9c8894ef3e8"),
    "materialdesignicons-webfont.ttf": (
        f"https://cdn.jsdelivr.net/npm/@mdi/font@{MDI_VERSION}/fonts/materialdesignicons-webfont.ttf",
        "61e8aba5a4e981fe22cf7c8e8bcdbea00476e75c62c37f01bf7ee33361d68428"),
    # Noto Sans Bold (OFL): degree sign for the 128 px clock font (timeTemplate, issue #1405).
    "NotoSans-Bold.ttf": (
        "https://cdn.jsdelivr.net/gh/notofonts/notofonts.github.io@main/fonts/NotoSans/hinted/ttf/NotoSans-Bold.ttf",
        "1df075a380fc7cb898acf64c1f7b3b4dd780de3caa860178bf929de35817a913"),
}
CACHE = Path(__file__).resolve().parents[2] / "fonts" / ".mdi-cache" / MDI_VERSION
MDI_FIRST = 0xF0001
NEXTION_FIRST = 0xE000
NEXTION_LAST = 0xFDFF  # keep clear of U+FE00.. (variation selectors, specials)


def to_nextion(mdi_codepoint: int) -> int:
    cp = mdi_codepoint - MDI_FIRST + NEXTION_FIRST
    if not NEXTION_FIRST <= cp <= NEXTION_LAST:
        raise ValueError(f"MDI code point {mdi_codepoint:#x} does not fit the Nextion range")
    return cp


def fetch(name: str, cache: Path = CACHE) -> Path:
    """Return the cached file, downloading and verifying it first if needed."""
    url, digest = FILES[name]
    path = cache / name
    if not path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - pinned https URL
            data = response.read()
        if hashlib.sha256(data).hexdigest() != digest:
            raise RuntimeError(f"checksum mismatch for {url}")
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f"cached {path} does not match the pinned checksum; delete it")
    return path


def load_meta(cache: Path = CACHE) -> list[dict]:
    """MDI metadata sorted by name: name, codepoint (MDI), nextion, aliases, deprecated."""
    meta = json.loads(fetch("meta.json", cache).read_text(encoding="utf-8"))
    icons = []
    for item in meta:
        mdi_cp = int(item["codepoint"], 16)
        icons.append({
            "name": item["name"],
            "codepoint": mdi_cp,
            "nextion": to_nextion(mdi_cp),
            "aliases": sorted(item.get("aliases") or []),
            "deprecated": bool(item.get("deprecated")),
        })
    return sorted(icons, key=lambda icon: icon["name"])
