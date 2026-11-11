# nspanel-lovelace-ui (fork franekSoftSF) – project instructions

Lovelace UI for the Sonoff NSPanel (Nextion HMI + Tasmota Berry driver or ESPHome). Fork of joBr99/nspanel-lovelace-ui,
named "NSPanel Lovelace UI (by Szymi)" (domain stays `nspanel_lovelace_ui`). GPL-3.0; record notable changes in NOTICE.
Talk to the user in Polish; code, comments and commits in English.

## Layout (protocol: `CustomSend` / `{"CustomRecv": ...}` over MQTT, or ESPHome `use_ha_api`)
- `custom_components/nspanel_lovelace_ui/` – the native HA integration (config flow, `panels.yaml`, import of AppDaemon `apps.yaml`).
  - `runtime.py` – HA MQTT subscribe/publish, event bus, time tracking; one worker thread per panel (`PanelWorker`).
  - `backend/` – panel logic derived from the upstream add-on `mqtt-manager` (commit 9dac8052; the add-on, the AppDaemon
    app, ioBroker etc. were removed from this repository in 5.2.2 – use git history or upstream if needed).
    `backend/libs/home_assistant.py` is the in-process bridge replacing the add-on websocket client (same API).
    Integration-only changes in `panel.py` (no scheduler thread: `on_time_tick`), `ha_cards.py` (no dateutil),
    `libs/localization.py` (cached). Porting an upstream fix: copy the change, keep relative imports.
- `tasmota/` Berry driver, `HMI/` Nextion sources, `examples/panels.yaml`, `scripts/` (firmware package, brand icon).
- Icons/firmware (HMI/FIRMWARE.md): `HMI/code_gen/fonts/` (zi.py .zi reader/writer, build_fonts.py,
  mdi.py pinned MDI + sha256) and `HMI/code_gen/icons/update_mdi.py` generate `HMI/fonts/generated/*.zi` and
  `backend/libs/icon_mapping.py` from the same MDI release - never edit them by hand. `.HMI`/`.tft` change only
  in Nextion Editor (Windows GUI, manual: HMI/BUILD.md; `hmi_info.py` reads font indexes and checks .tft). Weather pictures: `HMI/code_gen/weather/build_pictures.py` (Meteocons, Docker/cairosvg) -> `HMI/pictures/weather`, order = `backend/weather.py` PICTURES. HMI edits for firmware 55: HMI/BUILD-55.md. Integration: `firmware.py` (package), `http.py` (token URL for
  Tasmota, plain HTTP + Range), `update.py` (Display firmware entity).

## Rules
- Panel protocol and `panels.yaml` format stay compatible with the original project (validator: `backend/config_manager.py`).
- The backend runs in worker threads: never block the HA event loop; loop-side code is `@callback`/`async_*` in
  `runtime.py` and the bridge. Threads must stop on unload (tests check no `nspanel-*` threads remain).
- `mqtt.async_publish` always with explicit `qos`/`retain` (None fallbacks removed in HA 2027.6).
- User-facing strings: `strings.json` + `translations/en.json` (copy of strings.json) + `translations/pl.json`, same keys.
- Bump `manifest.json` `version` for every release; `hacs.json` `homeassistant` = minimum HA version.
- Never run `python` from the Microsoft Store stub on the dev PC; the real one is `C:\Program Files\Python314\python.exe` (`py`).

## Verification
```bash
docker build -t nspanel-ha-tests -f tests_ha/Dockerfile .   # once / after requirements_test.txt changes
docker run --rm -v "$PWD:/work" nspanel-ha-tests             # integration tests (pytest-homeassistant-custom-component)
```
Not testable locally: real panel, Tasmota/ESPHome firmware, real MQTT broker, TFT flashing – say what was only
checked statically.
