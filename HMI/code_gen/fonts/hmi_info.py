"""Show and check what Nextion Editor needs: model, orientation, encoding and font indexes.

    python HMI/code_gen/fonts/hmi_info.py HMI/nspanel.HMI            # project: fonts by index
    python HMI/code_gen/fonts/hmi_info.py --check eu HMI/nspanel.tft  # exported .tft before flashing

.HMI container (reverse-engineered, same as Nextion2Text): u32 entry count, then 28-byte entries
(name[16], start u32, size u32, flags u32). Fonts are stored as "<n>.zi"; their *index* in the
editor is their position in the list inside main.HMI (verified: screensaver tTime uses font 5 =
the 128 px digits, tMainIcon font 4 = 80 px icons). main.HMI: model CRC at +16, orientation at
+12, encoding at +13. .tft header: width/height at 0x0C, orientation at 0x14, model CRC at 0x2E,
file size at 0x3C.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from zi import HEADER_SIZE  # noqa: E402

MODELS = {0x1CE47603: "NX4832F035_011 (Nextion Discovery 3.5\" 320x480)"}
ENCODINGS = {0x18: "utf-8"}
FLASH_BYTES = 16 * 1024 * 1024
# Values of the current (version 54) projects; a correct build keeps them.
VARIANTS = {
    "eu": {"hmi": "HMI/nspanel.HMI", "tft": "nspanel.tft", "orientation": 3, "page_width": 480},
    "us-p": {"hmi": "HMI/US/portrait/nspanel_US_P.HMI", "tft": "nspanel_US_P.tft", "orientation": 2, "page_width": 320},
    "us-l": {"hmi": "HMI/US/landscape/nspanel_US_L.HMI", "tft": "nspanel_US_L.tft", "orientation": 3, "page_width": 480},
}
MODEL_CRC = 0x1CE47603


def toc(raw: bytes) -> dict[str, tuple[int, int]]:
    count = struct.unpack_from("<I", raw, 0)[0]
    entries = {}
    for i in range(count):
        pos = 4 + 28 * i
        name = raw[pos:pos + 16].split(b"\0")[0].decode("latin1")
        start, size, _ = struct.unpack_from("<III", raw, pos + 16)
        if name:
            entries[name] = (start, size)
    return entries


def hmi_info(path: Path) -> dict:
    raw = path.read_bytes()
    entries = toc(raw)
    start, size = entries["main.HMI"]
    main = raw[start:start + size]
    fonts = []
    for index, name in enumerate(m.decode() for m in re.findall(rb"\d+\.zi", main)):
        fstart, fsize = entries[name]
        head = raw[fstart:fstart + HEADER_SIZE]
        name_len = head[0x11]
        fonts.append({
            "index": index, "file": name, "height": head[7],
            "glyphs": struct.unpack_from("<I", head, 0x0C)[0], "bytes": fsize,
            "name": raw[fstart + HEADER_SIZE:fstart + HEADER_SIZE + name_len].decode("latin1"),
        })
    return {
        "model_crc": struct.unpack_from("<I", main, 16)[0],
        "orientation": main[12],
        "encoding": main[13],
        "fonts": fonts,
    }


def tft_info(path: Path) -> dict:
    raw = path.read_bytes()
    width, height = struct.unpack_from("<HH", raw, 0x0C)
    return {
        "size": len(raw),
        "declared_size": struct.unpack_from("<I", raw, 0x3C)[0],
        "resolution": (width, height),
        "orientation": raw[0x14],
        "model_crc": struct.unpack_from("<I", raw, 0x2E)[0],
    }


def check_tft(variant: str, path: Path) -> list[str]:
    expected = VARIANTS[variant]
    info = tft_info(path)
    problems = []
    if info["model_crc"] != MODEL_CRC:
        problems.append(f"wrong display model (CRC {info['model_crc']:#x}); select NX4832F035_011 in Device")
    if info["orientation"] != expected["orientation"]:
        problems.append(f"wrong display direction {info['orientation']} (expected {expected['orientation']}); "
                        "do not change Device > Display Direction")
    if info["size"] > FLASH_BYTES:
        problems.append(f"{info['size']} bytes do not fit the 16 MB display flash")
    if info["declared_size"] != info["size"]:
        problems.append("file is truncated or not a Nextion .tft")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--check", choices=sorted(VARIANTS), help="check an exported .tft for this variant")
    args = parser.parse_args()
    status = 0
    for path in args.files:
        if args.check:
            info = tft_info(path)
            problems = check_tft(args.check, path)
            print(f"{path}: {info['size'] / 1048576:.2f} MiB, model {MODELS.get(info['model_crc'], hex(info['model_crc']))}, "
                  f"direction {info['orientation']}")
            for problem in problems:
                print(f"  ERROR: {problem}")
            if not problems:
                print(f"  OK for {args.check} ({(FLASH_BYTES - info['size']) / 1048576:.2f} MiB flash left)")
            status |= bool(problems)
            continue
        info = hmi_info(path)
        print(f"{path}")
        print(f"  model:       {MODELS.get(info['model_crc'], hex(info['model_crc']))}")
        print(f"  direction:   {info['orientation']} (stored value)")
        print(f"  encoding:    {ENCODINGS.get(info['encoding'], hex(info['encoding']))}")
        print("  fonts (index: height, glyphs, size, name):")
        for font in info["fonts"]:
            print(f"    {font['index']}: {font['height']:3} px {font['glyphs']:5} glyphs "
                  f"{font['bytes'] / 1048576:6.2f} MiB  {font['name']}")
    return status


if __name__ == "__main__":
    sys.exit(main())
