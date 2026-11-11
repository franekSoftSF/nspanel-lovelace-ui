# Przejście ze starej wersji (AppDaemon z HACS) na integrację 5.2

Instrukcja dla paneli, które dotąd działały na aplikacji AppDaemon `nspanel-lovelace-ui` zainstalowanej
przez HACS (sterownik Berry w Tasmocie + firmware ekranu z upstream). Po przejściu panelem steruje
integracja Home Assistant, a firmware ekranu (55) i sterownik Berry (10) aktualizujesz z Home Assistant.

Kolejność kroków jest ważna: na każdym etapie panel nadal działa, a wszystko, co może się nie udać,
da się cofnąć. English: [MIGRATION.md](MIGRATION.md).

## 0. Zanim zaczniesz

| Co | Gdzie |
|---|---|
| Kopia Home Assistant | Ustawienia → System → Kopie zapasowe → *Utwórz kopię* |
| Kopia `apps.yaml` | np. `<config>/appdaemon/apps/apps.yaml` (albo `/addon_configs/a0d7b954_appdaemon/apps/apps.yaml`) |
| Kopia konfiguracji Tasmoty | strona www panelu → *Configuration* → *Backup Configuration* |
| Wersja sterownika Berry | konsola Tasmoty: `GetDriverVersion` → np. `{"nlui_driver_version":"9"}` |
| Wersja firmware ekranu | log AppDaemon przy starcie panelu albo strona startowa panelu (np. 53 lub 54) |
| Adres IP Home Assistant | potrzebny, jeśli HA działa po HTTPS (krok 4) |

Wymagania: Home Assistant 2026.10 lub nowszy, integracja MQTT w HA podłączona do tego samego brokera,
co panele (AppDaemon miał własne połączenie MQTT; integracja używa tego z Home Assistant).

## 1. Stary backend – co zrobi integracja

Panelem może sterować tylko jeden backend. Gdyby oba działały, panel dostawałby sprzeczne polecenia,
a stary backend mógłby sam wgrać na ekran starsze firmware z GitHuba (`updateMode: auto-notify`).

Nie musisz nic robić ręcznie: w kroku 3 kreator integracji (opcja **Wyłącz zaimportowane aplikacje
AppDaemon**, domyślnie włączona) po udanej konfiguracji dopisuje `disable: true` do zaimportowanych
aplikacji w `apps.yaml`. AppDaemon wyładowuje je bez restartu, a inne aplikacje AppDaemon działają dalej.
Oryginał zostaje jako `apps.yaml.nspanel-backup`. Wynik:
```yaml
nspanel-1:
  disable: true
  module: nspanel-lovelace-ui
  class: NsPanelLovelaceUIManager
  config:
    ...
```

Jeśli AppDaemon służył tylko do NSPanel, możesz go też po prostu zatrzymać: Ustawienia → Dodatki
(Aplikacje) → **AppDaemon** → *Zatrzymaj* i wyłącz *Uruchamiaj przy starcie*.

**Nie usuwaj jeszcze** aplikacji z HACS ani wpisu z `apps.yaml` – to Twoja droga powrotu (krok 3, *Coś nie działa?*).

## 2. Zainstaluj integrację

- **Home Assistant 2026.11 i nowszy** (HACS nie działa): Ustawienia → Marketplace → *Dodaj z linku* →
  `franekSoftSF/nspanel-lovelace-ui` → *NSPanel Lovelace UI* → Zainstaluj.
- **Starszy Home Assistant z działającym HACS**: HACS → ⋮ → *Własne repozytoria* →
  `https://github.com/franekSoftSF/nspanel-lovelace-ui`, typ **Integracja** → zainstaluj
  *NSPanel Lovelace UI*. To osobny wpis niż stara aplikacja AppDaemon.
- **Bez sklepu**: skopiuj `custom_components/nspanel_lovelace_ui` z wydania
  [v5.2.0](https://github.com/franekSoftSF/nspanel-lovelace-ui/releases/tag/v5.2.0) do
  `<config>/custom_components/`.

Zrestartuj Home Assistant.

## 3. Zaimportuj konfigurację

1. Ustawienia → Urządzenia i usługi → *Dodaj integrację* → **NSPanel Lovelace UI**.
2. *Plik konfiguracji*: `nspanel_lovelace_ui/panels.yaml`.
3. *Importuj z*: kreator sam wpisuje `appdaemon/apps/apps.yaml`, jeśli znajdzie tam aplikację NSPanel.
   W innym miejscu podaj ścieżkę względem folderu konfiguracji. Jeśli `apps.yaml` leży w
   `/addon_configs/…` (poza folderem konfiguracji HA), najpierw skopiuj go do folderu konfiguracji
   (razem z `secrets.yaml`) i ręcznie zatrzymaj AppDaemon (krok 1).
4. *Wyłącz zaimportowane aplikacje AppDaemon*: zostaw zaznaczone (krok 1).
5. Przeczytaj powiadomienie z ostrzeżeniami importu, a potem sprawdź w nowym `panels.yaml`:
   - `locale: pl_PL` i `timeZone: Europe/Warsaw` (import uzupełnia brakujące wartości domyślnymi
     `en_US` i `Europe/Berlin`);
   - `dateFormat` (format `%…` z AppDaemon zamieniany jest na `full`);
   - tematy `panelRecvTopic` / `panelSendTopic` – takie same jak w AppDaemon.
   Po zmianach: akcja `nspanel_lovelace_ui.reload`.

Import nigdy nie nadpisuje istniejącego `panels.yaml`. Wartości `!secret` z `apps.yaml` są brane z
`secrets.yaml` obok `apps.yaml`, folder wyżej (AppDaemon) albo z `secrets.yaml` Home Assistant i wpisywane
wprost do `panels.yaml`.

**Sprawdzenie:** panel wychodzi z ekranu startowego i pokazuje wygaszacz i karty. Na starym firmware
część nowych ikon (MDI 7) może być pokazana błędnym znakiem – znikną po kroku 6.

**Coś nie działa?** Usuń integrację i przywróć `apps.yaml.nspanel-backup` jako `apps.yaml` (albo usuń
linie `disable: true`) – wracasz do stanu sprzed migracji.

## 4. Wgraj pakiet firmware do Home Assistant

1. Pobierz `nspanel-firmware.zip` z wydania
   [v5.2.0](https://github.com/franekSoftSF/nspanel-lovelace-ui/releases/tag/v5.2.0).
2. Wrzuć plik **bez rozpakowywania** do `<config>/nspanel_lovelace_ui/` (Samba, File editor, SSH).
   Przy przeładowaniu integracja sprawdza archiwum (nazwy, rozmiary, SHA-256), rozpakowuje je do
   `nspanel_lovelace_ui/firmware/` i zmienia jego nazwę na `nspanel-firmware.zip.installed`.
   Uszkodzone archiwum nie rusza poprzedniego pakietu; błąd pojawia się w Ustawienia → Naprawy.
3. Jeśli Home Assistant działa po **HTTPS** albo pod nazwą, której panel nie rozwiąże, dopisz na początku
   `panels.yaml` adres po zwykłym HTTP (sterownik Berry nie obsługuje TLS):
   ```yaml
   firmware_base_url: http://192.168.1.10:8123
   ```
4. Akcja `nspanel_lovelace_ui.reload`.

Każdy panel ma teraz encję aktualizacji **Firmware ekranu** z wersją zainstalowaną i dostępną (55).

## 5. Zaktualizuj sterownik Berry (9 → 10)

Narzędzia deweloperskie → Akcje → `nspanel_lovelace_ui.update_berry_driver` (opcjonalnie `panel`) → Wykonaj.

Tasmota pobiera `nsp-lovelace-driver.tapp` z Home Assistant i się restartuje. Jeśli sterownik był
zainstalowany jako `autoexec.be`, nowy sterownik sam go usuwa i przechodzi na `.tapp`.

**Sprawdzenie:** konsola Tasmoty → `GetDriverVersion` → `{"nlui_driver_version":"10"}`.
Wersja 9 też wgra nowe firmware, ale dopiero 10 raportuje postęp i błędy do encji aktualizacji.

**Coś nie działa?** Przywróć kopię konfiguracji Tasmoty albo wgraj stary plik przez *Consoles* →
*Manage File system* (pliki `.tapp` / `autoexec.be` z kopii).

## 6. Zaktualizuj firmware ekranu (→ 55)

1. Encja **Firmware ekranu** → *Zainstaluj*.
2. Wgrywanie trwa kilka minut; encja pokazuje postęp. Nie wyłączaj zasilania i nie restartuj Home Assistant
   w tym czasie (panel pobiera plik z HA).
3. Panel restartuje ekran, zgłasza wersję 55, encja kończy instalację.

**Sprawdzenie:** wygaszacz pokazuje kolorowe obrazki pogody, ikony wyglądają poprawnie.

**Przerwane wgrywanie** (pusty ekran / pasek postępu stoi): sterownik Berry na ESP32 nadal działa,
więc po prostu kliknij *Zainstaluj* jeszcze raz. Ekran Nextion przyjmuje nowe wgranie także po nieudanym.

**Powrót do starego firmware:** połóż stary plik `.tft` w `<config>/www/nspanel-old.tft` i w konsoli
Tasmoty wpisz `FlashNextion http://<ip-home-assistant>:8123/local/nspanel-old.tft`.
Integracja działa też na starym firmware (bez kolorowych obrazków i nowych ikon).

## 7. Sprzątanie (po kilku dniach bez problemów)

- Usuń wpis panelu z `apps.yaml` i plik `apps.yaml.nspanel-backup`.
- HACS (jeśli jest): usuń starą aplikację AppDaemon *NSPanel Lovelace UI*.
- AppDaemon bez innych aplikacji: odinstaluj dodatek.
- Dodatek / aplikacja `mqtt-manager` (jeśli była): odinstaluj.

## Kolejne aktualizacje (5.2.x)

- Integracja: Marketplace / HACS pokaże aktualizację; albo skopiuj folder ponownie. Restart HA.
- Firmware ekranu i sterownik: wrzuć nowy `nspanel-firmware.zip` do `<config>/nspanel_lovelace_ui/`,
  `nspanel_lovelace_ui.reload` (zastępuje poprzedni pakiet), potem kroki 5 i 6, jeśli wersja się zmieniła.
