# Firmware ekranu (.tft): fonty ikon MDI 7, budowa, wydanie, instalacja

[English version](FIRMWARE.md)

Ekran wyświetla ikony jako znaki swoich fontów. Ikony Material Design są wtopione w fonty Noto Sans
(32 px regular, 48 px regular, 80 px bold) pod kodami U+E000..U+FD16. Backend wysyła znak dla nazwy
ikony (`backend/libs/icon_mapping.py`). Font i mapowanie muszą pochodzić z tego samego wydania MDI,
dlatego oba są generowane z jednej przypiętej wersji MDI.

| | wcześniej | teraz |
|---|---|---|
| MDI | ~6.x, 6896 ikon | 7.4.47, 7447 ikon (+551), 13 659 nazw razem z aliasami |
| Fonty ikon | 32 / 48 / 80 px | 32 / 48 / 80 px (ten sam rozmiar i położenie) + **64 px** (ostre ikony 48 px na siatce 2 px/jednostkę) |
| Antyaliasing | Nextion Editor | nadpróbkowanie 4x4, dokładne pokrycie, 8 poziomów alfa (maksimum formatu .zi) |
| Wersja HMI | 54 | **55** |

## 1. Generowanie fontów i mapowania (dowolny system, Python 3.12+)

```bash
pip install pillow
python HMI/code_gen/icons/update_mdi.py     # icons.json + icon_mapping.py integracji
python HMI/code_gen/fonts/build_fonts.py    # HMI/fonts/generated/*.zi + report.json
```

Oba skrypty pobierają przypięte wydanie MDI (`HMI/code_gen/fonts/mdi.py`, sprawdzane SHA-256) do
`HMI/fonts/.mdi-cache/` (poza repo). Litery (U+0020..U+00FF) nie są renderowane od nowa: pochodzą z
`HMI/fonts/base/`, wyciągniętych z obecnego HMI skryptem `extract_base.py`. Zapis .zi odtwarza wynik
Nextion Editora bajt w bajt (sprawdzone na istniejących fontach ikon), a wynik jest deterministyczny.
`tests_ha/test_icons.py` sprawdza, że każda nazwa z mapowania ma glif w każdym foncie ikon i że
mieści się budżet flash.

Budżet flash (ekran NX4832F035: 16 MB na cały plik .tft, `report.json`):

| Wariant | obecny .tft (54) | szacunek z nowymi fontami |
|---|---|---|
| EU | 8,15 MiB | 10,88 MiB |
| US pionowy | 8,24 MiB | 10,97 MiB |
| US poziomy | 9,73 MiB | 12,46 MiB |

Szacunek zakłada, że edytor przechowuje fonty bez kompresji (tak jak HMI). Prawdziwy rozmiar sprawdź
po kompilacji (krok 2).

Zgodność nowego mapowania: żadna stara nazwa nie znika, poza 11 nazwami, które MDI usunął bez aliasu
(`android-messages`, `book-variant-multiple`, `calendar-week-end(-outline)`, `desktop-mac(-dashboard)`,
`discord`, `google-controller(-off)`, `google-home`, `tablet-android`). Pokazują one
`alert-circle-outline`, bo MDI 7 użył ich kodów dla innych ikon. 11 przemianowanych nazw pokazuje
obecny wygląd z MDI (tak jak frontend Home Assistant), np. `cloud-check`.

## 2. Nextion Editor (ręcznie, tylko Windows)

Nextion Editor nie ma wiersza poleceń, więc tego kroku nie da się zrobić w CI. Wykonaj go dla każdego
projektu: `HMI/nspanel.HMI` (EU), `HMI/US/portrait/nspanel_US_P.HMI`, `HMI/US/landscape/nspanel_US_L.HMI`.

1. Otwórz projekt w Nextion Editor (w wersji, w której projekt ostatnio zapisano, albo nowszej; nowszy
   edytor może poprosić o konwersję projektu, więc zachowaj kopię).
2. **Podmień** 3 fonty ikon w panelu *Fonts*, zachowując ich ID (kod HMI i backend odwołują się do
   fontów po ID):
   - NotoSans-Regular 32 → `HMI/fonts/generated/icons-regular-32.zi`
   - NotoSans-Regular 48 → `icons-regular-48.zi`
   - NotoSans-Bold 80 → `icons-bold-80.zi`

   Zaznacz font, *Replace*, wybierz plik, a potem porównaj wysokość. Jeśli Twoja wersja edytora nie ma
   *Replace* dla fontów, wstaw nowy font (*Insert*) w tym samym miejscu i usuń stary (*Delete*), a potem
   sprawdź, że ID pozostałych fontów się nie zmieniły.
3. **Dodaj** `icons-64.zi` jako ostatni font i zanotuj jego ID. HMI czyta wybór fontu jako jedną cyfrę
   (`...¬8`), więc ID musi mieścić się w 0–9. Backend zakłada 8. Jeśli jest inne, ustaw
   `largeIconFontId: <id>` dla paneli z tym wariantem w `panels.yaml`.
4. Strona `pageStartup`, komponent tekstowy `tVersion`: zmień `54` na `55`.
5. *Compile*. Okno wyników pokazuje zajętość flash; musi zostać poniżej 16 MB (zobacz tabelę).
6. *File → TFT file output* (albo *Upload → TFT*): zapisz jako `nspanel.tft`, `nspanel_US_P.tft`,
   `nspanel_US_L.tft` obok projektu (zastąp stary plik). US poziomy ma dodatkowy `nspanel_US_L-I.tft`;
   jeśli go używasz, zbuduj go tak samo z jego projektu.
7. Zapisz projekt (`.HMI`) i zacommituj HMI + TFT. Workflow *nextion2text* zaktualizuje `n2t-out`.
8. Wgraj na jeden panel i sprawdź: ikony na wygaszaczu, kartach, siatce (`font: large-icon`) i w popupach.

## 3. Wydanie

```bash
python scripts/make_firmware_package.py --version 55 --release v5.2.0 \
  --eu HMI/nspanel.tft --us-p HMI/US/portrait/nspanel_US_P.tft \
  --us-l HMI/US/landscape/nspanel_US_L.tft --berry tasmota/autoexec.be \
  --out dist/nspanel-firmware --zip
gh release upload v5.2.0 dist/nspanel-firmware.zip --repo franekSoftSF/nspanel-lovelace-ui
```

Pakiet to `firmware.json` (wersja, SHA-256 i rozmiar każdego pliku) plus same pliki.
`--version` musi być równe `tVersion` skompilowanego HMI.

## 4. Instalacja (integracja Home Assistant)

1. Rozpakuj plik z wydania tak, żeby istniał `<config>/nspanel_lovelace_ui/firmware/firmware.json`.
2. Przeładuj integrację (albo wywołaj `nspanel_lovelace_ui.reload`).
3. Każdy panel ma encję aktualizacji **Firmware ekranu**. Gdy ekran przy starcie zgłosi starszą wersję,
   *Zainstaluj* wysyła do Tasmoty `FlashNextion http://<home-assistant>/api/nspanel_lovelace_ui/firmware/<token>/<plik>`
   (`cmnd/<temat>/FlashNextion`; ESPHome: wywołanie API z komendą 255). Panel pobiera .tft z Home Assistant,
   wgrywa go (kilka minut) i się restartuje. Encja kończy instalację, gdy ekran zgłosi nową wersję.
4. Sterownik Berry: akcja `nspanel_lovelace_ui.update_berry_driver` (opcjonalnie `panel`) wysyła
   `UpdateDriverVersion <url>/autoexec.be`. Tasmota potem się restartuje.
5. Przy `updateMode: auto-notify` (domyślnie) panel sam pyta o aktualizację. Gdy pakiet jest
   zainstalowany, również wtedy używany jest lokalny plik.

Wymagania:
- Panel musi łączyć się z Home Assistant po **zwykłym HTTP** (sterownik Berry nie obsługuje TLS).
  Integracja używa wewnętrznego adresu Home Assistant. Jeśli jest to HTTPS albo nazwa, której panel nie
  rozwiąże, ustaw `firmware_base_url: http://192.168.1.10:8123` na początku `panels.yaml`.
- Adres pobierania zawiera losowy token, zmieniany przy każdym starcie Home Assistant. Serwowane są
  tylko pliki z `firmware.json`, bez logowania (Tasmota nie umie się uwierzytelnić).
- Duże ikony: `font: large-icon` w encjach `cardGrid` (firmware 55 lub nowszy).

## Co zostało sprawdzone

- Automatycznie (testy w Dockerze): odczyt i zapis .zi (bajt w bajt zgodny z fontami ikon z Nextion
  Editora), wygenerowane fonty ↔ mapowanie, szacunek budżetu flash, walidacja pakietu firmware,
  serwowanie HTTP z Range/Content-Length tak, jak pyta sterownik Berry, encja aktualizacji (wersja ze
  zdarzenia startup, komenda FlashNextion, postęp do zgłoszenia nowej wersji), akcja sterownika Berry.
- Tylko statycznie albo wcale: kompilacja w Nextion Editor, prawdziwy rozmiar .tft, wygląd ikon na
  ekranie, wgrywanie na prawdziwy panel przez Tasmotę albo ESPHome, ID fontów w 3 projektach.
