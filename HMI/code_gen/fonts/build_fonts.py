"""Build the Nextion icon fonts (.zi) from the pinned Material Design Icons release.

    pip install pillow
    python HMI/code_gen/fonts/build_fonts.py            # writes HMI/fonts/generated/
    python HMI/code_gen/fonts/build_fonts.py --preview  # plus preview PNGs (old vs new)

Each font = text glyphs from HMI/fonts/base (unchanged Nextion Editor output) + every MDI icon,
rendered with 4x4 supersampling and quantised to Nextion's 8 alpha levels. Existing sizes keep
the old icon size and position (no layout change); the new 64 px font uses a 2 px/unit grid
(48 px icons) for sharp large tiles. The .zi files are imported in Nextion Editor (see
HMI/FIRMWARE.md). report.json lists sizes and the flash budget.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mdi  # noqa: E402
from zi import Glyph, ZiFont, encode  # noqa: E402

HMI = HERE.parents[1]
BASE = HMI / "fonts" / "base"
OUT = HMI / "fonts" / "generated"
SUPERSAMPLE = 4
FLASH_BYTES = 16 * 1024 * 1024  # NX4832F035 (NSPanel display): 16 MB flash for the whole .tft

# file, Nextion font name, cell height, icon em size, icon top offset, base text font
FONTS = [
    ("icons-regular-32.zi", "NotoSans-Regular-mdi", 32, 27, 4, "text-regular-32.zi"),
    ("icons-regular-48.zi", "NotoSans-Regular-mdi", 48, 43, 4, "text-regular-48.zi"),
    ("icons-bold-80.zi", "NotoSans-Bold-mdi", 80, 66, 0, "text-bold-80.zi"),
    ("icons-64.zi", "mdi-icons", 64, 48, 8, None),  # new: large tiles, icons only
]
# Fonts the current .tft already contains and the new ones replace (bytes, for the budget).
REPLACED_BYTES = {"icons-regular-32.zi": 1024414, "icons-regular-48.zi": 1833715, "icons-bold-80.zi": 3324837}
# Current .tft sizes (HMI/nspanel.tft, HMI/US/portrait, HMI/US/landscape), version 54.
CURRENT_TFT_BYTES = {"eu": 8549736, "us-p": 8643104, "us-l": 10200864}


def render_icons(ttf: Path, icons: list[dict], em: int, height: int, top: int) -> dict[int, Glyph]:
    from PIL import Image, ImageDraw, ImageFont

    size = em * SUPERSAMPLE
    font = ImageFont.truetype(str(ttf), size)
    ascent, descent = font.getmetrics()
    glyphs: dict[int, Glyph] = {}
    for icon in icons:
        canvas = Image.new("L", (size, size), 0)
        # MDI's em square spans ascent+descent; scale so it maps onto the canvas exactly.
        ImageDraw.Draw(canvas).text((0, size - ascent - descent), chr(icon["codepoint"]), font=font, fill=255)
        small = canvas.reduce(SUPERSAMPLE)  # box filter = exact pixel coverage
        cell = Image.new("L", (em, height), 0)
        cell.paste(small, (0, top))
        px = [min(7, (value * 7 + 127) // 255) for value in cell.tobytes()]
        glyphs[icon["nextion"]] = Glyph(icon["nextion"], em, encode(px))
    return glyphs


def build(out: Path = OUT, only: set[str] | None = None) -> dict:
    icons = mdi.load_meta()
    ttf = mdi.fetch("materialdesignicons-webfont.ttf")
    out.mkdir(parents=True, exist_ok=True)
    report = {"mdi_version": mdi.MDI_VERSION, "icons": len(icons), "fonts": {}}
    for filename, name, height, em, top, base in FONTS:
        if only and filename not in only:
            continue
        font = ZiFont(f"{name}-{height}", height)
        if base:
            text = ZiFont.load(BASE / base)
            if text.height != height:
                raise ValueError(f"{base}: height {text.height} != {height}")
            font.glyphs.update(text.glyphs)
        font.glyphs.update(render_icons(ttf, icons, em, height, top))
        size = font.save(out / filename)
        report["fonts"][filename] = {"height": height, "icon_em": em, "glyphs": len(font.glyphs), "bytes": size}
        print(f"{filename}: {len(font.glyphs)} glyphs, {size / 1048576:.2f} MiB")
    added = sum(f["bytes"] - REPLACED_BYTES.get(n, 0) for n, f in report["fonts"].items())
    report["budget"] = {"flash_bytes": FLASH_BYTES, "added_bytes": added, "variants": {}}
    for variant, current in CURRENT_TFT_BYTES.items():
        estimate = current + added
        report["budget"]["variants"][variant] = {"current_tft": current, "estimated_tft": estimate,
                                                 "free_bytes": FLASH_BYTES - estimate}
        print(f"estimated {variant} .tft: {estimate / 1048576:.2f} MiB of {FLASH_BYTES / 1048576:.0f} MiB "
              f"({(FLASH_BYTES - estimate) / 1048576:.2f} MiB free)")
    report["budget"]["free_bytes"] = min(v["free_bytes"] for v in report["budget"]["variants"].values())
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def preview(old_font: Path, new_font: Path, names: list[str], target: Path) -> None:
    """Side-by-side PNG (old | new) of some icons, enlarged 4x, for review."""
    from PIL import Image

    icons = {icon["name"]: icon for icon in mdi.load_meta()}
    old, new = ZiFont.load(old_font), ZiFont.load(new_font)
    scale, gap = 4, 8
    tiles = []
    for name in names:
        cp = icons[name]["nextion"]
        row = []
        for font in (old, new):
            glyph = font.glyphs.get(cp)
            img = Image.new("L", (new.glyphs[cp].width, font.height), 0)
            if glyph:
                img.putdata([v * 255 // 7 for v in glyph.pixels(font.height)])
                img = img.crop((0, 0, glyph.width, font.height))
            row.append(img.resize((img.width * scale, img.height * scale), Image.NEAREST))
        tiles.append(row)
    width = max(r[0].width for r in tiles) + max(r[1].width for r in tiles) + 3 * gap
    height = sum(max(r[0].height, r[1].height) + gap for r in tiles) + gap
    sheet = Image.new("L", (width, height), 40)
    y = gap
    for left, right in tiles:
        sheet.paste(left, (gap, y))
        sheet.paste(right, (2 * gap + left.width, y))
        y += max(left.height, right.height) + gap
    sheet.save(target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Nextion icon fonts from MDI")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--only", nargs="*", help="font file names to build")
    parser.add_argument("--preview", type=Path, help="old 32 px .zi to compare against")
    args = parser.parse_args()
    report = build(args.out, set(args.only) if args.only else None)
    if args.preview:
        preview(args.preview, args.out / "icons-regular-32.zi",
                ["lightbulb-outline", "home", "thermometer", "weather-partly-cloudy", "window-shutter", "fan"],
                args.out / "preview-32.png")
    return 0 if report["budget"]["free_bytes"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
