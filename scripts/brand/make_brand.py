"""Render the integration's brand images (Home Assistant 2026.3+ reads custom_components/<domain>/brand/).

    docker run --rm -v "$PWD:/work" -w /work python:3.14-slim sh -c \
      "apt-get update -qq && apt-get install -y -qq libcairo2 >/dev/null && \
       pip install -q cairosvg && python scripts/brand/make_brand.py"
"""
from __future__ import annotations

from pathlib import Path

import cairosvg

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name("icon.svg")
TARGET = ROOT / "custom_components" / "nspanel_lovelace_ui" / "brand"


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    svg = SOURCE.read_bytes()
    for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
        cairosvg.svg2png(bytestring=svg, write_to=str(TARGET / name), output_width=size, output_height=size)
        print(f"wrote {TARGET / name}")


if __name__ == "__main__":
    main()
