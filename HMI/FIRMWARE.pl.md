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

Nextion Editor nie ma wiersza poleceń, więc tego kroku nie da się zrobić w CI. Instrukcja krok po
kroku z wersją edytora i linkiem do pobrania, tabelą indeksów fontów każdego wariantu, testem w
symulatorze, eksportem, kontrolą przed flashowaniem, checklistą i typowymi błędami:
**[BUILD.md](BUILD.md)**. W skrócie: podmień fonty 1, 3, 4 na wygenerowane, dodaj na końcu
`icons-64.zi` (indeks 8; US pionowy 7), ustaw `pageStartup.tVersion` na 55, skompiluj, wyeksportuj,
`hmi_info.py --check`.

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
  ekranie, wgrywanie na prawdziwy panel przez Tasmotę albo ESPHome. Indeksy fontów są odczytane z projektów i sprawdzane testem.
