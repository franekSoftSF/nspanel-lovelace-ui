# NSPanel Lovelace UI – Home Assistant integration

[Polska wersja](INTEGRATION.pl.md)

`custom_components/nspanel_lovelace_ui` is a native Home Assistant integration that replaces both the AppDaemon
app and the add-on (now called an "app" in Home Assistant). It runs inside Home Assistant, so it works on **every
installation type** (OS, Supervised, Container, Core), needs no access token and no second MQTT connection.

| | AppDaemon app (legacy) | Add-on / app `mqtt-manager` | Integration (this) |
|---|---|---|---|
| Runs in | AppDaemon | separate container (HA OS / Supervised only) | Home Assistant itself |
| HA connection | AppDaemon HASS plugin | websocket + token | in-process (`hass`) |
| MQTT | AppDaemon MQTT plugin | own paho client | HA MQTT integration |
| Config | `apps.yaml` | `panels.yaml` + web editor | `panels.yaml` (same format) |
| Install | HACS (blocked since 2026.11) | app repository | Marketplace (custom repository) or manual copy |

The panel protocol (Tasmota Berry driver `CustomSend`/`CustomRecv` over MQTT, or the ESPHome component with
`use_ha_api: true`) is unchanged, so no panel or firmware change is needed.

## Requirements

- Home Assistant **2026.10 or newer** (tested against 2026.10.4 with `pytest-homeassistant-custom-component`; written for 2026.11).
- Tasmota firmware: the [MQTT integration](https://www.home-assistant.io/integrations/mqtt/) must be set up
  (same broker as the panels). ESPHome firmware: the ESPHome integration with the NSPanel component.
- Only one backend may control a panel: **stop the AppDaemon app and the add-on/app** before you enable the integration.

## Installation

HACS cannot be installed on Home Assistant 2026.11 or newer. It was replaced by the built-in **Marketplace**
(Settings → Marketplace), which reads the same `hacs.json`. Use one of these ways:

### A) Marketplace (custom repository)

1. Settings → Marketplace → connect GitHub (needed for custom repositories).
2. **Add from link** → `franekSoftSF/nspanel-lovelace-ui` (the repository must be public; it contains `hacs.json`).
3. Install *NSPanel Lovelace UI*, restart Home Assistant if asked.

If you used the AppDaemon variant through HACS: after the migration to Marketplace, AppDaemon apps keep working
but are no longer updated. Switch to this integration step by step: [MIGRATION.md](MIGRATION.md).

### B) Manual copy (always works, no GitHub connection)

1. Copy `custom_components/nspanel_lovelace_ui` into `<config>/custom_components/nspanel_lovelace_ui`
   (Samba / SSH / File editor / `scp`). On Container installs `<config>` is the folder mounted as `/config`.
2. Restart Home Assistant.

Updates: copy the folder again and restart.

## Configuration

1. Create `<config>/nspanel_lovelace_ui/panels.yaml` – the same format as the add-on
   ([example](examples/panels.yaml)). MQTT server/credentials and
   `home_assistant_*` keys are ignored: the integration uses Home Assistant's own connections.
2. Settings → Devices & services → Add integration → **NSPanel Lovelace UI**.
3. *Configuration file*: `nspanel_lovelace_ui/panels.yaml` (relative to the config folder).

### Importing an existing configuration

In the same dialog, enter *Import from*:

- AppDaemon: e.g. `appdaemon/apps/apps.yaml` – entries with `module: nspanel-lovelace-ui` or
  `class: NsPanelLovelaceUIManager` are converted (same converter as the add-on editor: `timezone` → `timeZone`,
  screensaver weather → explicit entities, etc.), other apps are skipped.
- Add-on: `/addon_configs/<slug>/panels.yaml` is outside the HA config folder – copy it into the config folder first.

The import writes the configuration file and **never overwrites** an existing one. Warnings are shown as a
notification – review them.

### Changing the configuration

Edit `panels.yaml`, then call the action `nspanel_lovelace_ui.reload` (or reload the integration).
To use another file: integration menu → *Reconfigure*.

## Entities and notifications

Each panel is a device with these entities:

| Entity | What it does |
|---|---|
| **Notification** (`notify`) | `notify.send_message`: on the screensaver the text replaces the weather until a touch; on a card it opens a notification page |
| **Wake up screen** (`button`) | like a touch on the screensaver |
| **Page** (`sensor`) | `screensaver` or the title of the card on the screen (attributes `card_type`, `card_key`) |
| **Card** (`select`) | shows a card, e.g. a camera card when the doorbell rings; the back button returns to the previous card |
| **Display firmware** (`update`) | display firmware update with progress |

More options with the action `nspanel_lovelace_ui.notify`:

```yaml
action: nspanel_lovelace_ui.notify
data:
  panel: nspanel-1        # optional, empty = all panels
  title: Washing
  message: The washing machine has finished
  mode: popup             # auto | screensaver | popup | clear (closes the screensaver notification)
  timeout: 60             # notification page only, seconds; 0 = until closed
  buzzer: true            # Tasmota: Buzzer 2,2,2
```

Diagnostics for a bug report: Settings → Devices & services → NSPanel Lovelace UI → ⋮ → *Download diagnostics*.

## Known differences from the add-on

- No web editor (edit `panels.yaml` directly; the add-on's editor can still be used to produce the file).
- One integration entry controls all panels (`single_config_entry`).
- `timeZone` defaults to Home Assistant's time zone instead of `Europe/Berlin`.

## Development

```bash
docker build -t nspanel-ha-tests -f tests_ha/Dockerfile .
docker run --rm -v "$PWD:/work" nspanel-ha-tests
```

Tests use `pytest-homeassistant-custom-component` (Python 3.14). Home Assistant does not run on Windows, so use
Docker (or WSL / Linux / macOS with a Python 3.14 venv: `pip install -r requirements_test.txt && pytest`).

### Screensaver options (firmware 55)

| Option (panel level) | Default | Meaning |
|---|---|---|
| `weatherIcons` | `color` | `color`: colour weather pictures (Meteocons) on firmware 55+ with the default black screensaver background; `font`: always the single-colour MDI icons |
| `weatherPictureBase` | 26 (EU), 24 (US) | ID of the first weather picture, if you imported them at another position (HMI/BUILD-55.md) |
| `timeTemplate` | – | template shown instead of the clock, e.g. `"{{ states('sensor.nspanel_temp') }}°"` (`°` needs firmware 55) |
| `largeIconFontId` | 8 (US portrait: 7) | font index of the 64 px icons for `font: large-icon` |

Forecast icons now use the condition and colour of their own day, partly cloudy nights show the moon,
and grids switch between 3×2 and 4×2 by the number of *visible* items.

## Display firmware

The integration can serve the display firmware (.tft) and the Tasmota Berry driver from Home Assistant
and flash it with the **Display firmware** update entity of each panel. Building the firmware with the
MDI 7 icon fonts, publishing it and installing the package: [HMI/FIRMWARE.md](HMI/FIRMWARE.md).

## Changelog

### 5.2.4
- **Wake up screen** works like a touch on the screensaver (the panel shows its card at normal
  brightness); the HMI command `wake` it sent before did not brighten a real panel.

### 5.2.3
- Entities per panel: **Notification** (`notify.send_message`), **Wake up screen** button, **Page** sensor,
  **Card** select; action `nspanel_lovelace_ui.notify` (screensaver text or notification page, timeout,
  buzzer, close); diagnostics download.

### 5.2.2
Found while migrating a real panel (HMI 53 from 2023, AppDaemon from HACS) to firmware 55:
- Displays that do not ask for the screensaver content (older HMI 53 builds) get it right after the page
  switch, like AppDaemon did – the weather no longer stays empty before the firmware update.
- A display update prompt that is not on the screen (covered by another backend) no longer blocks the
  panel: the next touch dismisses it.
- Import: a panel without cards gets a sample card instead of failing; a missing `timeZone` takes Home
  Assistant's time zone; the setup dialog also finds the AppDaemon apps file in subfolders of
  `appdaemon/apps`; the add-on-only connection hint is gone.
- Integration icon (Home Assistant 2026.3+ reads it from `brand/`); README: remote updates.
- The repository contains only the integration now: the AppDaemon app, the add-on, ioBroker, IP-Symcon,
  Node-RED, the mkdocs documentation and their workflows were removed (the git history and the original
  project keep them). Example configuration: [examples/panels.yaml](examples/panels.yaml).

### 5.2.1
- The display firmware package is downloaded automatically from the GitHub release with the integration's
  version when it is missing or older (SHA-256 checked, then a reload). Action
  `nspanel_lovelace_ui.download_firmware`; turn it off with `firmware_download: false` in `panels.yaml`.
  A failed download shows in Repairs.

### 5.2.0
- Weather: each forecast day has its own icon and colour (it used the current weather's colour),
  night variants, Home Assistant colours, `windy-variant` colour fixed, `exceptional` icon.
- Colour weather pictures (Meteocons) with firmware 55 (`weatherIcons`), `timeTemplate` instead of the
  clock (upstream #1405), grid layout by visible items (upstream #1190).
- Display update progress and errors in the update entity (Berry driver 10 reports them, upstream #995).
- Icons: Material Design Icons 7.4.47 (7447 icons, aliases of renamed icons work). New icons need display
  firmware 55; see HMI/FIRMWARE.md.
- Update entity "Display firmware" per panel and action `nspanel_lovelace_ui.update_berry_driver`: the .tft
  and the Berry driver are served locally by Home Assistant from `<config>/nspanel_lovelace_ui/firmware/`.
- New grid font `font: large-icon` (64 px icon font of firmware 55, `largeIconFontId`, default 8).
- Optional `firmware_base_url` in panels.yaml (plain HTTP address the panels download from).
- Migration: an `nspanel-firmware.zip` dropped into `<config>/nspanel_lovelace_ui/` is checked and unpacked on
  reload; the `apps.yaml` import resolves `!secret`, the setup dialog finds `appdaemon/apps/apps.yaml` and
  disables the imported AppDaemon apps (`disable: true`, copy `apps.yaml.nspanel-backup`).
  Step-by-step move from the AppDaemon/HACS version: [MIGRATION.md](MIGRATION.md).

### 5.1.0
- Duplicate keys in `panels.yaml` no longer stop the integration: the last value is used (as with AppDaemon) and
  a warning with the line number appears under Settings → Repairs (upstream #1480).
- Only state changes of entities used in `panels.yaml` (plus `sun.sun`) wake the panels; templates still follow
  every entity they use (upstream #1465).
- `navItem1` / `navItem2` with an `entity` replace the left / right navigation button on every card, including
  hidden cards – e.g. `navItem1: {entity: navigate.home}` instead of the up arrow (upstream #1470, AppDaemon behaviour).
- Unloading the integration while a panel is starting no longer leaves its thread running for 5 seconds.
