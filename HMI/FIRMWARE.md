# Display firmware (.tft): MDI 7 icon fonts, build, release, install

[Polska wersja](FIRMWARE.pl.md)

The display shows icons as characters of its fonts: the Material Design Icons are merged into the
Noto Sans fonts (32 px regular, 48 px regular, 80 px bold) in the code points U+E000..U+FD16. The
backend sends the character for an icon name (`backend/libs/icon_mapping.py`). Font and mapping
must come from the same MDI release, so both are generated from one pinned MDI version.

| | before | now |
|---|---|---|
| MDI | ~6.x, 6896 icons | 7.4.47, 7447 icons (+551), 13 659 names incl. aliases |
| Icon fonts | 32 / 48 / 80 px | 32 / 48 / 80 px (same size and position) + **64 px** (sharp, 48 px icons on a 2 px/unit grid) |
| Anti-aliasing | Nextion Editor | 4x4 supersampling, exact coverage, 8 alpha levels (the most a .zi font supports) |
| HMI version | 54 | **55** |

## 1. Generate fonts and mapping (any OS, Python 3.12+)

```bash
pip install pillow
python HMI/code_gen/icons/update_mdi.py     # icons.json + integration icon_mapping.py
python HMI/code_gen/fonts/build_fonts.py    # HMI/fonts/generated/*.zi + report.json
```

Both download the pinned MDI release (`HMI/code_gen/fonts/mdi.py`, checked with SHA-256) into
`HMI/fonts/.mdi-cache/` (not committed). The text glyphs (U+0020..U+00FF) are not re-rendered:
they come from `HMI/fonts/base/`, extracted from the current HMI with `extract_base.py`.
The .zi writer reproduces Nextion Editor's output byte for byte (checked on the existing icon
fonts), and the output is deterministic. `tests_ha/test_icons.py` checks that every mapped name
has a glyph in every icon font and that the flash budget holds.

Flash budget (NX4832F035 display: 16 MB for the whole .tft, `report.json`):

| Variant | current .tft (54) | estimated with new fonts |
|---|---|---|
| EU | 8.15 MiB | 10.88 MiB |
| US portrait | 8.24 MiB | 10.97 MiB |
| US landscape | 9.73 MiB | 12.46 MiB |

The estimate assumes the editor stores fonts uncompressed (as the HMI does). Check the real size
after compiling (step 2).

Compatibility of the new mapping: no old name disappears except 11 names that MDI removed without
an alias (`android-messages`, `book-variant-multiple`, `calendar-week-end(-outline)`,
`desktop-mac(-dashboard)`, `discord`, `google-controller(-off)`, `google-home`, `tablet-android`):
they show `alert-circle-outline`, because MDI 7 reuses their code points for other icons. 11
renamed names show the current MDI design (as in the Home Assistant frontend), e.g. `cloud-check`.

## 2. Nextion Editor (manual, Windows only)

Nextion Editor has no command line, so this step cannot run in CI. Do it for each project:
`HMI/nspanel.HMI` (EU), `HMI/US/portrait/nspanel_US_P.HMI`, `HMI/US/landscape/nspanel_US_L.HMI`.

1. Open the project in Nextion Editor (the version the project was last saved with or newer;
   a newer editor may ask to convert the project - keep a copy).
2. **Replace** the three icon fonts in the *Fonts* panel, keeping their IDs (HMI code and the
   backend address fonts by ID):
   - NotoSans-Regular 32 → `HMI/fonts/generated/icons-regular-32.zi`
   - NotoSans-Regular 48 → `icons-regular-48.zi`
   - NotoSans-Bold 80 → `icons-bold-80.zi`

   Select the font, *Replace*, choose the file, compare the height afterwards. If your editor version
   has no *Replace* for fonts, *Insert* the new font at the same position and *Delete* the old one,
   then check that the IDs of all other fonts are unchanged.
3. **Add** `icons-64.zi` as the last font. Note its ID. The HMI reads the font override as one digit
   (`...¬8`), so the ID must be 0–9. The backend assumes 8; if it differs, set
   `largeIconFontId: <id>` for the panels with this variant in `panels.yaml`.
4. Page `pageStartup`, text component `tVersion`: change `54` to `55`.
5. *Compile*. The output window shows the flash usage; it must stay below 16 MB (see the table).
6. *File → TFT file output* (or *Upload → TFT*): save as `nspanel.tft`, `nspanel_US_P.tft`,
   `nspanel_US_L.tft` next to the project (replace the old file; US landscape has an extra
   `nspanel_US_L-I.tft` - build it the same way from its project if you use it).
7. Save the project (`.HMI`) and commit HMI + TFT. The *nextion2text* workflow updates `n2t-out`.
8. Flash one panel and check: icons on the screensaver, cards, grid (`font: large-icon`), popups.

## 3. Release

```bash
python scripts/make_firmware_package.py --version 55 --release v5.2.0 \
  --eu HMI/nspanel.tft --us-p HMI/US/portrait/nspanel_US_P.tft \
  --us-l HMI/US/landscape/nspanel_US_L.tft --berry tasmota/autoexec.be \
  --out dist/nspanel-firmware --zip
gh release upload v5.2.0 dist/nspanel-firmware.zip --repo franekSoftSF/nspanel-lovelace-ui
```

The package is `firmware.json` (version, SHA-256 and size of every file) plus the files.
`--version` must equal the `tVersion` of the compiled HMI.

## 4. Install (Home Assistant integration)

1. Unzip the release asset so that `<config>/nspanel_lovelace_ui/firmware/firmware.json` exists.
2. Reload the integration (or call `nspanel_lovelace_ui.reload`).
3. Each panel has an update entity **Display firmware**. When the display reports an older version
   at startup, *Install* sends `FlashNextion http://<home-assistant>/api/nspanel_lovelace_ui/firmware/<token>/<file>`
   to Tasmota (`cmnd/<topic>/FlashNextion`; ESPHome: the api call with command 255). The panel downloads
   the .tft from Home Assistant, flashes it (several minutes) and restarts; the entity finishes when the
   display reports the new version.
4. Berry driver: action `nspanel_lovelace_ui.update_berry_driver` (optional `panel`) sends
   `UpdateDriverVersion <url>/autoexec.be`; Tasmota restarts afterwards.
5. With `updateMode: auto-notify` (default) the panel itself asks to update; with the package
   installed this also uses the local file.

Requirements:
- The panel must reach Home Assistant over **plain HTTP** (the Berry driver has no TLS). The
  integration uses Home Assistant's internal URL; if that is HTTPS or a name the panel cannot resolve,
  set `firmware_base_url: http://192.168.1.10:8123` at the top of `panels.yaml`.
- The download URL contains a random token that changes on every Home Assistant start; it serves only
  the files listed in `firmware.json`, without authentication (Tasmota cannot authenticate).
- Use the large icons: `font: large-icon` on `cardGrid` entities (firmware 55 or newer).

## What has been verified

- Automatically (tests, Docker): .zi reader/writer (byte-identical with Nextion Editor's icon fonts),
  generated fonts ↔ mapping, flash budget estimate, firmware package validation, HTTP serving with
  Range/Content-Length as the Berry driver requests it, update entity (version from the startup event,
  FlashNextion command, progress until the new version is reported), Berry driver action.
- Only statically / not at all: compiling in Nextion Editor, the real .tft size, how the icons look on
  the display, flashing a real panel through Tasmota or ESPHome, font IDs in the three projects.
