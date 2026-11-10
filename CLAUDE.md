# nspanel-lovelace-ui (fork franekSoftSF) – project instructions

Lovelace UI for the Sonoff NSPanel (Nextion HMI + Tasmota Berry driver or ESPHome). Fork of joBr99/nspanel-lovelace-ui.
Talk to the user in Polish; code, comments and commits in English.

## Backends (protocol is shared: `CustomSend` / `{"CustomRecv": ...}` over MQTT, or ESPHome `use_ha_api`)
- `custom_components/nspanel_lovelace_ui/` – **primary**: native HA integration (config flow, `panels.yaml`, AppDaemon import).
  - `runtime.py` – HA MQTT subscribe/publish, event bus, time tracking; one worker thread per panel (`PanelWorker`).
  - `backend/` – panel logic copied from the add-on `mqtt-manager` (commit 9dac8052) with package-relative imports.
    `backend/libs/home_assistant.py` is the in-process bridge replacing the add-on websocket client (same API).
    Integration-only changes in `panel.py` (no scheduler thread: `on_time_tick`), `ha_cards.py` (no dateutil),
    `libs/localization.py` (cached). Porting a fix from the add-on: copy the change, keep relative imports.
- `nspanel-lovelace-ui/` – HA add-on ("app") `mqtt-manager` + web editor (upstream; HA OS/Supervised only).
- `apps/nspanel-lovelace-ui/` – legacy AppDaemon backend (no longer updated by HA Marketplace).
- `tasmota/` Berry driver, `HMI/` Nextion sources, `ioBroker/`, `nodered/` – other systems.

## Rules
- Panel protocol and `panels.yaml` format must stay compatible with the add-on (same validator: `backend/config_manager.py`).
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
python -m unittest discover -s tests                         # add-on tests (upstream)
```
Not testable locally: real panel, Tasmota/ESPHome firmware, real MQTT broker, TFT flashing – say what was only
checked statically.
