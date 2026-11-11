"""Extract the text part (U+0020..U+00FF) of the icon fonts embedded in an .HMI project.

The icon fonts are Noto Sans text fonts with the Material Design Icons merged into the private
use area. build_fonts.py keeps their text glyphs unchanged and renders the icons again, so the
text glyphs are stored once in HMI/fonts/base/ (small, committed).

    python HMI/code_gen/fonts/extract_base.py HMI/nspanel.HMI

Only needed again when the text glyphs should change.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from zi import HEADER_SIZE, ZiFont  # noqa: E402

TEXT_LAST = 0xFF
# (font name in the HMI, height) -> base file
WANTED = {
    ("NotoSans-Regular", 32): "text-regular-32.zi",
    ("NotoSans-Regular", 48): "text-regular-48.zi",
    ("NotoSans-Bold", 80): "text-bold-80.zi",
}


def embedded_fonts(raw: bytes):
    """Yield (offset, ZiFont) for every .zi found in an HMI file (last copy wins later)."""
    pos = 0
    while (pos := raw.find(b"\x04\xff\x00\x0a", pos)) >= 0:
        if struct.unpack_from("<I", raw, pos + 0x18)[0] == HEADER_SIZE:
            size = struct.unpack_from("<I", raw, pos + 0x14)[0]
            try:
                yield pos, ZiFont.from_bytes(raw[pos:pos + HEADER_SIZE + size])
            except (ValueError, struct.error):
                pass
        pos += 4


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("hmi", type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[2] / "fonts" / "base")
    args = parser.parse_args()
    raw = args.hmi.read_bytes()
    found = {}
    for _, font in embedded_fonts(raw):
        key = (font.name, font.height)
        if key not in WANTED:
            continue
        text = {cp: g for cp, g in font.glyphs.items() if cp <= TEXT_LAST}
        try:
            for glyph in text.values():
                glyph.pixels(font.height)  # the HMI may split big files: verify every glyph
        except ValueError:
            continue
        found[key] = ZiFont(font.name, font.height, text)
    args.out.mkdir(parents=True, exist_ok=True)
    for key, filename in WANTED.items():
        if key not in found:
            print(f"missing or damaged in {args.hmi}: {key}", file=sys.stderr)
            return 1
        size = found[key].save(args.out / filename)
        print(f"{filename}: {len(found[key].glyphs)} glyphs, {size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
