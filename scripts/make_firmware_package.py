"""Create the display firmware package served by the Home Assistant integration.

    python scripts/make_firmware_package.py --version 55 --release v5.2.0 \
        --eu HMI/nspanel.tft --us-p HMI/US/portrait/nspanel_US_P.tft \
        --us-l HMI/US/landscape/nspanel_US_L.tft --berry tasmota/autoexec.be \
        --out dist/nspanel-firmware

The output folder (firmware.json + files) is attached to a GitHub release as a zip and copied
to <config>/nspanel_lovelace_ui/firmware/ on the Home Assistant host. --version must be the
number the .tft reports at startup (Text tVersion on pageStartup in the HMI).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

FLASH_BYTES = 16 * 1024 * 1024  # NX4832F035 display flash
REPO_URL = "https://github.com/franekSoftSF/nspanel-lovelace-ui"


def describe(path: Path, target: Path, name: str) -> dict:
    shutil.copyfile(path, target / name)
    data = (target / name).read_bytes()
    return {"file": name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", type=int, required=True, help="HMI version reported at startup")
    parser.add_argument("--release", required=True, help="release tag, e.g. v5.2.0")
    parser.add_argument("--eu", type=Path)
    parser.add_argument("--us-p", dest="us_p", type=Path)
    parser.add_argument("--us-l", dest="us_l", type=Path)
    parser.add_argument("--berry", type=Path, help="tasmota/autoexec.be")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--zip", action="store_true", help="also write <out>.zip for the release")
    args = parser.parse_args()

    models = {"eu": args.eu, "us-p": args.us_p, "us-l": args.us_l}
    models = {model: path for model, path in models.items() if path}
    if not models:
        parser.error("give at least one of --eu, --us-p, --us-l")
    if args.version < 16:
        parser.error("--version must be at least 16")
    if args.out.exists() and any(args.out.iterdir()):
        parser.error(f"{args.out} is not empty")
    args.out.mkdir(parents=True, exist_ok=True)

    files = {}
    for model, path in models.items():
        size = path.stat().st_size
        if size > FLASH_BYTES:
            print(f"{path}: {size} bytes does not fit the 16 MB display flash", file=sys.stderr)
            return 1
        files[model] = describe(path, args.out, f"nspanel-{model}-{args.release}.tft")
        print(f"{model}: {size / 1048576:.2f} MiB ({FLASH_BYTES - size} bytes of flash left)")
    manifest = {
        "version": args.version,
        "release": args.release,
        "release_url": f"{REPO_URL}/releases/tag/{args.release}",
        "files": files,
    }
    if args.berry:
        manifest["berry"] = describe(args.berry, args.out, "autoexec.be")
    (args.out / "firmware.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8",
                                            newline="\n")
    if args.zip:
        archive = args.out.with_suffix(".zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as zf:
            for item in sorted(args.out.iterdir()):
                zf.write(item, f"firmware/{item.name}")
        print(f"wrote {archive}")
    print(f"wrote {args.out / 'firmware.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
