"""Write the complete event code to paste into Nextion Editor for firmware 55 (HMI/BUILD-55.md).

    python HMI/code_gen/patches_55.py

Reads the current code from the nextion2text dumps (HMI/n2t-out, HMI/US/*/n2t-out), applies the
firmware 55 changes and writes one file per event to HMI/patches/55/<variant>/: open the
component in Nextion Editor, select the event, Ctrl+A in the code box and paste the file.
Fails if an anchor is missing, so an outdated dump is noticed instead of producing wrong code.
"""
from __future__ import annotations

from pathlib import Path
import sys

HMI = Path(__file__).resolve().parents[1]
OUT = HMI / "patches" / "55"
VARIANTS = {"eu": HMI / "n2t-out", "us-p": HMI / "US" / "portrait" / "n2t-out",
            "us-l": HMI / "US" / "landscape" / "n2t-out"}
PICTURES = ["pMain", "pF1", "pF2", "pF3", "pF4"]
ICONS = ["tMainIcon", "tF1Icon", "tF2Icon", "tF3Icon", "tF4Icon"]
# US portrait pages that do not ask for their content (#1475).
RENDER_REQUEST_PAGES = ["cardEntities", "cardThermo", "cardMedia", "cardAlarm", "cardQR", "cardPower",
                        "cardChart", "cardLChart", "screensaver", "screensaver2", "screensaver3"]


def event_code(page: str, folder: Path, component: str, event: str) -> list[str]:
    """Code of one event from a dump (component header 'Kind name', or 'Page <page>')."""
    lines = (folder / f"{page}.txt").read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.strip() and not line.startswith(" ") and line.split()[-1] == component)
    head = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == event)
    code = []
    for line in lines[head + 1:]:
        if line.strip() and (len(line) - len(line.lstrip())) <= 8:
            break
        code.append(line[12:] if line.startswith(" " * 12) else line.strip())
    while code and not code[-1].strip():
        code.pop()
    return code


def indent_of(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def insert_after(code: list[str], anchor: str, block: list[str], occurrence: int = 1, extra: str = "") -> None:
    hits = [i for i, line in enumerate(code) if line.strip() == anchor]
    if len(hits) < occurrence:
        raise ValueError(f"anchor not found: {anchor}")
    i = hits[occurrence - 1]
    pad = indent_of(code[i]) + extra
    code[i + 1:i + 1] = [pad + line if line else line for line in block]


def insert_before(code: list[str], anchor: str, block: list[str]) -> None:
    i = next((i for i, line in enumerate(code) if line.strip() == anchor), None)
    if i is None:
        raise ValueError(f"anchor not found: {anchor}")
    pad = indent_of(code[i])
    code[i:i] = [pad + line if line else line for line in block]


def block_end(code: list[str], header: str) -> int:
    """Index of the closing brace of the block that starts with header."""
    i = next(i for i, line in enumerate(code) if line.strip() == header)
    pad = indent_of(code[i])
    return next(j for j in range(i + 2, len(code)) if code[j] == pad + "}")


HIDE = [f"vis {p},0" for p in PICTURES]
WEATHER_PICS = ['// firmware 55: colour weather pictures (weatherPics~main~f1~f2~f3~f4, empty = font icon)',
                'if(tInstruction.txt=="weatherPics"&&tNotifyHead.txt==""&&tNotifyText.txt=="")', "{"]
for field, pic in enumerate(PICTURES, 1):
    WEATHER_PICS += [f'  spstr strCommand.txt,tTmp.txt,"~",{field}', '  if(tTmp.txt=="")', "  {",
                     f"    vis {pic},0", "  }else", "  {", "    covx tTmp.txt,sys0,0,0",
                     f"    {pic}.pic=sys0", f"    vis {pic},1", "  }"]
WEATHER_PICS += ["}"]
TIME_ALIGN = ["// firmware 55 (#1485): with AM/PM the time is left-aligned so it does not run under AM/PM",
              "if(p0.w!=320)", "{", '  if(tAMPM.txt=="")', "  {", "    tTime.xcen=1", "  }else", "  {",
              "    tTime.xcen=0", "  }", "}"]
DATE_FONT = ["// firmware 55 (#1485): long dates get the 24 px font on the narrow US portrait screen",
             "if(p0.w==320)", "{", "  strlen tDate.txt,sys0", "  if(sys0>22)", "  {", "    tDate.font=0",
             "  }else", "  {", "    tDate.font=2", "  }", "}"]
RENDER_REQUEST = ['tSend.txt="event,renderCurrentPage"', "//send calc crc", "btlen tSend.txt,sys0",
                  "crcrest 1,0xffff // reset CRC", "crcputh 55 bb", "crcputs sys0,2", "crcputs tSend.txt,0",
                  "//send cmd", "printh 55 bb", "prints sys0,2", "prints tSend.txt,0", "prints crcval,2"]


# Notifications come from automations (CustomSend), not from the backend, and weatherUpdate /
# weatherPics are ignored while one is shown. When it closes, ask the backend for the whole
# screensaver again (it then resends weather, pictures and colours from scratch).
RESTORE = ["// firmware 55: notification closed - ask the backend to send the screensaver again"] + RENDER_REQUEST


def screensaver_files(folder: Path, variant: str) -> dict[str, list[str]]:
    files = {}
    pre = event_code("screensaver", folder, "screensaver", "Preinitialize Event")
    if variant == "us-p":
        pre = RENDER_REQUEST + pre  # D (#1475)
    files["01-screensaver-strona-Preinitialize.txt"] = pre + ["// firmware 55: weather pictures stay hidden until weatherPics"] + HIDE

    serial = event_code("screensaver", folder, "tmSerial", "Timer Event")
    if variant != "us-p":  # US portrait shows AM/PM below the time
        insert_before(serial, 'spstr strCommand.txt,tTimeAdd.txt,"~",2', TIME_ALIGN)
    insert_after(serial, "tDate.txt=pageIcons.vaDate.txt", DATE_FONT)
    insert_before(serial, 'if(tInstruction.txt=="color"&&tNotifyHead.txt==""&&tNotifyText.txt=="")', WEATHER_PICS)
    end = block_end(serial, 'if(tInstruction.txt=="color"&&tNotifyHead.txt==""&&tNotifyText.txt=="")')
    pad = indent_of(serial[end]) + "  "
    serial[end:end] = [pad + "// firmware 55 (#1026): redraw the status icons after a colour change",
                       pad + "ref tIcon1", pad + "ref tIcon2"]
    notify = next(i for i, line in enumerate(serial) if line.strip() == 'if(tInstruction.txt=="notify")')
    show = next(i for i in range(notify, len(serial)) if serial[i].strip() == "vis tNotifyText,1")
    serial[show + 1:show + 1] = [indent_of(serial[show]) + line for line in
                                 ["// firmware 55: the weather pictures would cover the notification"] + HIDE]
    hide = next(i for i in range(notify, len(serial)) if serial[i].strip() == "vis tNotifyText,0")
    serial[hide + 1:hide + 1] = [indent_of(serial[hide]) + line for line in RESTORE]
    files["02-screensaver-tmSerial-TimerEvent.txt"] = serial

    touch = event_code("screensaver", folder, "tc0", "Touch Press Event")
    insert_after(touch, "vis tNotifyText,0", RESTORE)
    files["03-screensaver-tc0-TouchPressEvent.txt"] = touch
    return files


PICTURE_BASE = {"eu": 26, "us-p": 24, "us-l": 24}  # = backend/weather.py PICTURE_BASE


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def frame(text: str) -> str:
    """The 55 BB frame the Berry driver sends for a CustomSend payload (hex, for the simulator)."""
    payload = text.encode("utf-8")
    body = bytes([0x55, 0xBB]) + len(payload).to_bytes(2, "little") + payload
    return (body + crc16_modbus(body).to_bytes(2, "little")).hex(" ").upper()


def test_frames(variant: str) -> list[str]:
    base = PICTURE_BASE[variant]
    # main: partly-cloudy-night (4); forecast: clear-day, rain, thunderstorms-rain, snow (15 + 0/6/8/9)
    pics = [base + 4] + [base + 15 + index for index in (0, 6, 8, 9)]
    lines = ["Debug > Instruction Input Area > Hex; on the screensaver page send one line at a time:", ""]
    for text, what in [
        ("weatherPics~" + "~".join(map(str, pics)), "colour pictures: moon+cloud, sun, rain, storm, snow"),
        ("time~21:47~", "time"),
        ("date~Środa, 11 listopada 2026", "date (UTF-8)"),
        ("notify~Test~Hello NSPanel", "notification: hides the pictures (touch the screen to close it)"),
        ("weatherPics~~~~~", "hide the pictures (font icons)"),
    ]:
        lines += [f"# {text}  ({what})", frame(text), ""]
    return lines


def main() -> int:
    for variant, folder in VARIANTS.items():
        files = screensaver_files(folder, variant)
        if variant == "us-p":
            for number, page in enumerate(p for p in RENDER_REQUEST_PAGES if not p.startswith("screensaver")):
                code = event_code(page, folder, page, "Preinitialize Event")
                files[f"{number + 10:02d}-{page}-strona-Preinitialize.txt"] = RENDER_REQUEST + code
            for page in ("screensaver2", "screensaver3"):
                code = event_code(page, folder, page, "Preinitialize Event")
                files[f"{len(files) + 10:02d}-{page}-strona-Preinitialize.txt"] = RENDER_REQUEST + code
        files["99-ramki-testowe-symulator.txt"] = test_frames(variant)
        target = OUT / variant
        target.mkdir(parents=True, exist_ok=True)
        for old in target.glob("*.txt"):
            old.unlink()
        for name, code in files.items():
            (target / name).write_text("\r\n".join(code) + "\r\n", encoding="utf-8", newline="")
        print(f"{variant}: {len(files)} files in {target.relative_to(HMI.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
