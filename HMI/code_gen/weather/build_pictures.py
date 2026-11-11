"""Colour weather pictures for the screensaver (firmware 55+) from Meteocons (Bas Milius, MIT).

    docker run --rm -v "$PWD:/work" -w /work python:3.14-slim sh -c \
      "apt-get update -qq && apt-get install -y -qq libcairo2 >/dev/null && \
       pip install -q cairosvg pillow && python HMI/code_gen/weather/build_pictures.py"

(cairosvg needs the Cairo library, which Windows does not ship; any Linux/macOS Python works too.)

Writes HMI/pictures/weather/NN-<size>-<name>.png. Import them into Nextion Editor in file-name
order (HMI/BUILD.md): picture ID = first new ID + NN, matching backend/weather.py PICTURES
(main pictures 00-14, forecast pictures 15-29). The pictures are drawn on black, the default
screensaver background; the backend keeps the font icons for any other background.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "HMI" / "pictures" / "weather"
CACHE = ROOT / "HMI" / "fonts" / ".mdi-cache" / "meteocons-2.0.0"
URL = "https://cdn.jsdelivr.net/npm/@bybas/weather-icons@2.0.0/design/fill/export/wi_{}.svg"
# Same order as custom_components/nspanel_lovelace_ui/backend/weather.py PICTURES.
SVGS = {
    "clear-day": "d5ba34f4a314483e29ae579a31b513032b9327926474e896d7657e3438b62657",
    "clear-night": "79cf68a3ad2d34255387cb827b2b77862832d57bbc5a1f2440c93b211ee393bd",
    "cloudy": "431fd1da3dd2a1b2da7ececeadf9f3708a197b1851e3f0555c928d8a04094c37",
    "partly-cloudy-day": "7f98404f0d103d8c84639dcfc7e5e5602782bb18ab719bc697d654b667da9d1a",
    "partly-cloudy-night": "def6861552c19684f376ebda3b3ca3a23a6fa191fc9c8a75101a0c8650e9a87f",
    "drizzle": "e90ae4e34c24850d077b44dafa32715cfccf000e3a60a9f2ad7666144fe95ba8",
    "rain": "60cfe370a816c435646823cb410b6c359aba3339f679a38776095f36c1106d6a",
    "thunderstorms": "c928f3882fe449289a3f88e00326aad364f08362de33ee558e62610e13e4d320",
    "thunderstorms-rain": "41746bf4e9d670164e8c22d44e16358dbd80fa9a9fa816deb1911adddbf5eac3",
    "snow": "1af9ffb2cb53389c18173f3df9c10d9d15238fc93a7e970e15d871387635d6ee",
    "sleet": "063bd0ee0160b508fbabfae15955e8cb791a88fc68caef8a89c8c6a010f5e5ce",
    "hail": "b4f4032f9240fb1790424d4d1b3bb7a66d2408ee11cc2a637f08e46187c6b92b",
    "fog": "8bd67a20a4b0304dc91b024146445b94722c0b59711c4931be8f8c523295adae",
    "wind": "5cafda7b9479c0543bc14d94879ed502a429ef233a1dcdc1bcd1ecfa2a13ddaa",
    "tornado": "8d6a70a5d68e0892bbe7619fe7a054e4ae64909b88aceee9f8c33b40b86e42e0",
}
# (label, width, height): the screensaver's tMainIcon area and the gap between forecast day and value.
SIZES = [("main", 70, 66), ("forecast", 40, 40)]
BACKGROUND = (0, 0, 0)
RENDER = 512  # render large, crop to the drawing, then scale down with a box filter


def fetch(name: str) -> bytes:
    path = CACHE / f"{name}.svg"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(URL.format(name), timeout=60) as response:  # noqa: S310 - pinned URL
            path.write_bytes(response.read())
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != SVGS[name]:
        raise RuntimeError(f"{path} does not match the pinned checksum")
    return data


def render(svg: bytes, width: int, height: int):
    import cairosvg
    from PIL import Image

    image = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg, output_width=RENDER, output_height=RENDER)))
    image = image.convert("RGBA")
    image = image.crop(image.getchannel("A").getbbox())  # Meteocons leave a wide margin
    scale = min((width - 2) / image.width, (height - 2) / image.height)
    image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.BOX)
    canvas = Image.new("RGBA", (width, height), BACKGROUND + (255,))
    canvas.alpha_composite(image, ((width - image.width) // 2, (height - image.height) // 2))
    return canvas.convert("RGB")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    index = 0
    for label, width, height in SIZES:
        for name in SVGS:
            render(fetch(name), width, height).save(OUT / f"{index:02d}-{label}-{name}.png", optimize=True)
            index += 1
    print(f"{index} pictures in {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
