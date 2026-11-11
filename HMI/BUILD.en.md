# Building the display firmware (.tft) in Nextion Editor – everything in one place

[Polska wersja](BUILD.md) · Background (MDI 7 fonts, release, install): [FIRMWARE.md](FIRMWARE.md)

Everything except the editor work is prepared in the repository: `.zi` fonts, simulator commands, a
script that checks the result, and the package script. In Nextion Editor you open the project,
replace 3 fonts, add 1 font, change the version number, compile and export the `.tft`. Do this for
the 3 variants, about 10 minutes each.

## 1. Tool

| | |
|---|---|
| Program | **Nextion Editor 1.68.2** (Windows), the latest version on the vendor site |
| Download | page: https://nextion.tech/nextion-editor/ · installer: https://nextion.tech/download/nextion-setup-v1-68-2.exe · ZIP (no install, can live next to other versions): https://nextion.tech/download/nextion-setup-v1-68-2.zip |
| Do not use | **TJC USART HMI** (the Chinese editor for TJC models). The projects are saved for the Nextion model **NX4832F035_011** and built in Nextion Editor |
| OS | Windows 10/11 (no Linux/macOS version; a Windows VM works) |

Before you open a project, copy the `.HMI` files (or work from a clean `git status`). The editor
version the projects were last saved with is not stored in a readable way. If 1.68.2 asks to
convert the project, accept: older editors may not open it afterwards, so commit the converted
`.HMI`.

## 2. Variants (read from the `.HMI` files, checked by a test)

| | EU | US portrait | US landscape |
|---|---|---|---|
| Project to open | `HMI/nspanel.HMI` | `HMI/US/portrait/nspanel_US_P.HMI` | `HMI/US/landscape/nspanel_US_L.HMI` |
| Model (Device) | NX4832F035_011 – Nextion Discovery 3.5" | NX4832F035_011 | NX4832F035_011 |
| Resolution | panel 320×480, pages 480×320 (landscape) | pages 320×480 (portrait) | pages 480×320 (landscape) |
| Display direction (stored value) | 3 | 2 | 3 |
| Character encoding | utf-8 | utf-8 | utf-8 |
| Output `.tft` | `HMI/nspanel.tft` | `HMI/US/portrait/nspanel_US_P.tft` | `HMI/US/landscape/nspanel_US_L.tft` |
| `--check` in step 6 | `eu` | `us-p` | `us-l` |
| Index of the new 64 px font | **8** | **7** | **8** |

**Do not change the Device settings** (model, direction, encoding). The editor shows the direction
in degrees. Instead of guessing which value means which angle, compare the result with the script
in step 6: a wrong value shows up as an error.

## 3. Files to import (ready in the repository)

All in `HMI/fonts/generated/`, shared by the 3 variants:

| File | What | Height | Size |
|---|---|---|---|
| `icons-regular-32.zi` | Noto Sans Regular 32 + 7447 MDI 7.4.47 icons | 32 px | 1.10 MiB |
| `icons-regular-48.zi` | Noto Sans Regular 48 + icons | 48 px | 2.01 MiB |
| `icons-bold-80.zi` | Noto Sans Bold 80 + icons | 80 px | 3.58 MiB |
| `icons-64.zi` | **new**: icons only, sharp (2 px grid) | 64 px | 1.94 MiB |
| `simulator-test-eu.txt`, `-us-p.txt`, `-us-l.txt` | simulator commands (step 5) | | |

To regenerate (not needed): `pip install pillow`, then `python HMI/code_gen/fonts/build_fonts.py`.
The output is deterministic (byte-identical).

## 4. Fonts, index by index

The HMI code and the backend select fonts **by index** (clock = font 5, large icon = font 4, grid
override `...¬4`). The other fonts' indexes must not move.

EU (`nspanel.HMI`) and US landscape (`nspanel_US_L.HMI`) – 8 fonts each:

| Index | Now | Action |
|---|---|---|
| 0 | text 24 px (`noto-sans-24-sp5` / `-sp6`) | keep |
| 1 | NotoSans-Regular 32 px with icons | **replace** with `icons-regular-32.zi` |
| 2 | text 32 px (`noto-sans-32-sp5` / `-sp6`) | keep |
| 3 | NotoSans-Regular 48 px with icons | **replace** with `icons-regular-48.zi` |
| 4 | NotoSans-Bold 80 px with icons | **replace** with `icons-bold-80.zi` |
| 5 | clock digits 128 px | **replace** with `clock-bold-128.zi` (adds `°`, BUILD-55.en.md B) |
| 6 | vertical text 16 px | keep |
| 7 | `corners1` 15 px | keep |
| **8** | – | **add** `icons-64.zi` |

US portrait (`nspanel_US_P.HMI`) – 7 fonts: indexes 0–6 as above (0 and 2 are `-sp3`, 6 is the
vertical 16 px text, **no** `corners1`), so the new font is added as **7**.

Replacing a font in the *Fonts* panel (bottom left, tab next to *Pictures*):
1. Select the font with that index and check its height in the preview (32/48/80).
2. Click **Replace** and choose the `.zi` file. The index stays the same.
3. If your version has no *Replace* for fonts: **Insert** (inserts before the selected font),
   then **Delete** the old one. Check the list: indexes 0–7 must match the table.
4. New font: **Add** appends it to the end, so it gets index 8 (US portrait: 7).

If the new font ends up with another index (0–9 allowed), set `largeIconFontId: <index>` for that
panel in `panels.yaml`. The integration defaults to 8, and to 7 for `model: us-p`.

## 5. Steps for each variant

1. **Open** the project from the table in step 2 (*File → Open*).
2. **Fonts**: replace indexes 1, 3, 4 and 5 and add the 64 px font (step 4).
   **Firmware 55 changes** (colour weather icons, issue fixes): [BUILD-55.en.md](BUILD-55.en.md), sections A–F.
3. **Version**: page `pageStartup` (*Page* list on the right), text component `tVersion`,
   attribute `txt`: change `54` to **`55`**. The display sends this number at startup
   (`event,startup,55,eu`), and the integration compares it with the package.
4. **Compile** (toolbar). The *Output* window must show no `Error`. Note the memory usage and size.
   Estimate: EU about 10.9 MiB, US portrait about 11.0 MiB, US landscape about 12.5 MiB; the limit
   is 16 MB.
5. **Simulator (Debug)**, before flashing anything:
   1. Click **Debug**. The simulator shows the start page "Waiting for content…". Every few seconds
      this page switches on the frame mode `recmod=1`, which ignores plain instructions, so leave it.
   2. **Click the spinning spinner 9 times.** This hidden entry opens the page `pageTest`.
   3. On `pageTest` click **"disable recmod"** (grey button on the right, above "bauds=115200").
   4. In the *Instruction Input Area* select **String** and *Keyboard Input*, paste all lines of
      `HMI/fonts/generated/simulator-test-<variant>.txt` (open it in Notepad; the icons look like empty
      boxes or Hebrew/Armenian letters there, which is expected), click **Run all commands**.
   5. Expected on the page `pageIcons` (3 white fields on the right):
      - top: house (`home`), same as before;
      - middle: thermometer with probe (`thermometer-probe`). It is new in MDI 7, so the old
        firmware would show an empty field here;
      - bottom: a large, sharp thermostat (`thermostat-auto`) from the 64 px font. If it is empty or
        small, the font index differs from the `tTmp3.font=` command.
6. **Export**: *File → TFT file output*, choose the folder and name from the table in step 2
   (overwrite the old file). Then check the result:
   ```bash
   python HMI/code_gen/fonts/hmi_info.py --check eu HMI/nspanel.tft
   python HMI/code_gen/fonts/hmi_info.py --check us-p HMI/US/portrait/nspanel_US_P.tft
   python HMI/code_gen/fonts/hmi_info.py --check us-l HMI/US/landscape/nspanel_US_L.tft
   ```
   The script checks the model, display direction, size against 16 MB and file completeness.
   `python HMI/code_gen/fonts/hmi_info.py <file.HMI>` prints the font table of a saved project.
7. **Save** the project (*File → Save*). Commit `.HMI` + `.tft`; the *nextion2text* workflow updates
   `n2t-out*`.
8. **Package and flash**: [FIRMWARE.md](FIRMWARE.md), steps 3–4 (`make_firmware_package.py` with
   `--version 55`, then the *Display firmware* entity in Home Assistant). Start with one panel.

US landscape also has `nspanel_US_L-I.tft` in the repository (a separate, older variant). It is not
part of this guide, so do not overwrite it with the output of `nspanel_US_L.HMI`.

## 6. Checklist

- [ ] Nextion Editor 1.68.2, not TJC USART HMI
- [ ] Copy of the `.HMI` before opening (or a clean `git status`)
- [ ] Device unchanged: NX4832F035_011, direction as in the table, utf-8
- [ ] Index 1 → `icons-regular-32.zi`, 3 → `icons-regular-48.zi`, 4 → `icons-bold-80.zi`
- [ ] `icons-64.zi` appended: index 8 (EU, US landscape) / 7 (US portrait)
- [ ] Index 5 → `clock-bold-128.zi`
- [ ] BUILD-55.en.md: A (weather pictures), C, D (US portrait only), E, F
- [ ] `pageStartup.tVersion` = 55
- [ ] Compile without errors, size < 16 MB
- [ ] Debug: the 3 icons of the test file are visible
- [ ] `.tft` saved under the right name, `hmi_info.py --check <variant>` = OK
- [ ] Project saved, `.HMI` + `.tft` committed
- [ ] Package with `--version 55`, test on one panel first

## 7. Common errors

| Symptom | Cause | Fix |
|---|---|---|
| Compile/export: out of space, `.tft` > 16 MB, `--check`: "do not fit" | fonts too large (e.g. a font added twice) | remove duplicates; do not add icon sizes other than in the table |
| `--check`: "wrong display model" | another model selected in *Device* (e.g. TJC4832T035, NX4832T035) or TJC USART HMI used | revert the project changes and reopen it in Nextion Editor |
| `--check`: "wrong display direction" | direction changed, or the wrong project exported under this name | export from the right `.HMI` (table in step 2) |
| The panel rejects the file / flashing stops at the start | wrong model, damaged file, or not plain HTTP | `--check`, package from the script, `firmware_base_url` over plain HTTP |
| Boxes or garbage instead of letters | a text font replaced instead of an icon font, or the encoding changed | keep indexes 0/2, Device: utf-8 |
| Clock or icons in the wrong size, layout shifted | indexes moved (*Delete* before *Add*/*Insert*) | restore the `.HMI`, redo steps 4.1–4.4 |
| Large grid icons empty or small | the 64 px font has another index | `largeIconFontId` in `panels.yaml`, or fix the order |
| New icons (e.g. `thermometer-probe`) empty on the panel | the panel still runs firmware 54 | flash 55; the *Display firmware* entity shows the version |
| The integration offers no update | `tVersion` not changed, or the package `--version` ≠ 55 | fix `tVersion`, rebuild the package |
| The editor asks to convert the project | the project was saved with an older editor | accept (on a copy) and commit the converted file |
