# Moving from the old version (AppDaemon from HACS) to integration 5.2

For panels that so far ran on the AppDaemon app `nspanel-lovelace-ui` installed through HACS (Berry
driver on Tasmota + display firmware from upstream). Afterwards the Home Assistant integration drives the
panel, and you update the display firmware (55) and the Berry driver (10) from Home Assistant.

The order matters: the panel keeps working at every step, and everything that can fail can be undone.
Polski: [MIGRATION.pl.md](MIGRATION.pl.md).

## 0. Before you start

| What | Where |
|---|---|
| Home Assistant backup | Settings → System → Backups → *Create backup* |
| Copy of `apps.yaml` | e.g. `<config>/appdaemon/apps/apps.yaml` (or `/addon_configs/a0d7b954_appdaemon/apps/apps.yaml`) |
| Tasmota configuration backup | panel web page → *Configuration* → *Backup Configuration* |
| Berry driver version | Tasmota console: `GetDriverVersion` → e.g. `{"nlui_driver_version":"9"}` |
| Display firmware version | AppDaemon log when the panel starts, or the panel's startup page (e.g. 53 or 54) |
| Home Assistant IP address | needed if HA runs on HTTPS (step 4) |

Requirements: Home Assistant 2026.10 or newer, the HA MQTT integration connected to the same broker as
the panels (AppDaemon had its own MQTT connection; the integration uses Home Assistant's).

## 1. The old backend – what the integration does

Only one backend may drive a panel. With both running the panel gets conflicting commands, and the old
backend could flash older firmware from GitHub on its own (`updateMode: auto-notify`).

Nothing to do by hand: in step 3 the setup dialog (option **Disable the imported AppDaemon apps**, on by
default) adds `disable: true` to the imported apps in `apps.yaml` once the setup succeeds. AppDaemon
unloads them without a restart; other AppDaemon apps keep running. The original stays as
`apps.yaml.nspanel-backup`. Result:
```yaml
nspanel-1:
  disable: true
  module: nspanel-lovelace-ui
  class: NsPanelLovelaceUIManager
  config:
    ...
```

If AppDaemon only ran the NSPanel, you can also just stop it: Settings → Add-ons (Apps) → **AppDaemon** →
*Stop* and turn off *Start on boot*.

**Do not remove** the HACS app or the `apps.yaml` entry yet – that is your way back (step 3, *Something wrong?*).

## 2. Install the integration

- **Home Assistant 2026.11 and newer** (HACS does not work): Settings → Marketplace → *Add from link* →
  `franekSoftSF/nspanel-lovelace-ui` → *NSPanel Lovelace UI* → Install.
- **Older Home Assistant with a working HACS**: HACS → ⋮ → *Custom repositories* →
  `https://github.com/franekSoftSF/nspanel-lovelace-ui`, type **Integration** → install
  *NSPanel Lovelace UI*. This is a separate entry from the old AppDaemon app.
- **Without a store**: copy `custom_components/nspanel_lovelace_ui` from release
  [v5.2.0](https://github.com/franekSoftSF/nspanel-lovelace-ui/releases/tag/v5.2.0) to
  `<config>/custom_components/`.

Restart Home Assistant.

## 3. Import the configuration

1. Settings → Devices & services → *Add integration* → **NSPanel Lovelace UI**.
2. *Configuration file*: `nspanel_lovelace_ui/panels.yaml`.
3. *Import from*: the dialog fills in `appdaemon/apps/apps.yaml` itself when it finds an NSPanel app
   there. Anywhere else, enter the path relative to the configuration folder. If `apps.yaml` is in
   `/addon_configs/…` (outside the HA configuration folder), copy it into the configuration folder first
   (with `secrets.yaml`) and stop AppDaemon by hand (step 1).
4. *Disable the imported AppDaemon apps*: leave it on (step 1).
5. Read the notification with the import warnings, then check the new `panels.yaml`:
   - `locale` and `timeZone` (the import fills missing values with the defaults `en_US` and `Europe/Berlin`);
   - `dateFormat` (an AppDaemon `%…` format is replaced with `full`);
   - `panelRecvTopic` / `panelSendTopic` – the same as in AppDaemon.
   After changes: action `nspanel_lovelace_ui.reload`.

The import never overwrites an existing `panels.yaml`. `!secret` values in `apps.yaml` are taken from
`secrets.yaml` next to `apps.yaml`, one folder up (AppDaemon) or from Home Assistant's `secrets.yaml`,
and written into `panels.yaml` as plain values.

**Check:** the panel leaves the startup screen and shows the screensaver and cards. On the old firmware
some new icons (MDI 7) may show a wrong glyph – that goes away after step 6.

**Something wrong?** Remove the integration and restore `apps.yaml.nspanel-backup` as `apps.yaml` (or
delete the `disable: true` lines) – you are back where you started.

## 4. Put the firmware package into Home Assistant

1. Download `nspanel-firmware.zip` from release
   [v5.2.0](https://github.com/franekSoftSF/nspanel-lovelace-ui/releases/tag/v5.2.0).
2. Drop the file **without unzipping** into `<config>/nspanel_lovelace_ui/` (Samba, File editor, SSH).
   On reload the integration checks the archive (names, sizes, SHA-256), unpacks it into
   `nspanel_lovelace_ui/firmware/` and renames it to `nspanel-firmware.zip.installed`. A broken archive
   leaves the previous package alone; the error shows in Settings → Repairs.
3. If Home Assistant runs on **HTTPS** or under a name the panel cannot resolve, add a plain HTTP address
   at the top of `panels.yaml` (the Berry driver has no TLS):
   ```yaml
   firmware_base_url: http://192.168.1.10:8123
   ```
4. Action `nspanel_lovelace_ui.reload`.

Each panel now has an update entity **Display firmware** with the installed and the available version (55).

## 5. Update the Berry driver (9 → 10)

Developer tools → Actions → `nspanel_lovelace_ui.update_berry_driver` (optional `panel`) → Perform action.

Tasmota downloads `nsp-lovelace-driver.tapp` from Home Assistant and restarts. If the driver was
installed as `autoexec.be`, the new driver removes it and moves to `.tapp`.

**Check:** Tasmota console → `GetDriverVersion` → `{"nlui_driver_version":"10"}`.
Version 9 also flashes the new firmware, but only 10 reports progress and errors to the update entity.

**Something wrong?** Restore the Tasmota configuration backup, or upload the old file through *Consoles* →
*Manage File system* (`.tapp` / `autoexec.be` from your backup).

## 6. Update the display firmware (→ 55)

1. Entity **Display firmware** → *Install*.
2. Flashing takes several minutes; the entity shows the progress. Do not cut the power or restart Home
   Assistant meanwhile (the panel downloads the file from HA).
3. The display restarts, reports version 55, and the entity finishes the installation.

**Check:** the screensaver shows colour weather pictures, the icons look right.

**Interrupted flash** (blank screen / progress stuck): the Berry driver on the ESP32 keeps running, so
just press *Install* again. The Nextion display accepts a new flash after a failed one.

**Back to the old firmware:** put the old `.tft` at `<config>/www/nspanel-old.tft` and run in the Tasmota
console `FlashNextion http://<home-assistant-ip>:8123/local/nspanel-old.tft`.
The integration also works on the old firmware (without colour pictures and new icons).

## 7. Clean up (after a few days without problems)

- Remove the panel entry from `apps.yaml` and the file `apps.yaml.nspanel-backup`.
- HACS (if present): remove the old AppDaemon app *NSPanel Lovelace UI*.
- AppDaemon without other apps: uninstall the add-on.
- The `mqtt-manager` add-on / app (if used): uninstall it.

## Later updates (5.2.x)

- Integration: Marketplace / HACS shows the update; or copy the folder again. Restart HA.
- Display firmware and driver: drop the new `nspanel-firmware.zip` into `<config>/nspanel_lovelace_ui/`,
  `nspanel_lovelace_ui.reload` (replaces the previous package), then steps 5 and 6 if the version changed.
