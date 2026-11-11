# Budowa firmware ekranu (.tft) w Nextion Editor – wszystko w jednym miejscu

[English version](BUILD.en.md) · Kontekst (fonty MDI 7, wydanie, instalacja): [FIRMWARE.pl.md](FIRMWARE.pl.md)

Wszystko poza pracą w edytorze jest już przygotowane w repo: fonty `.zi`, komendy do symulatora,
skrypt sprawdzający wynik i skrypt pakietu. W Nextion Editor zostaje: otworzyć projekt, podmienić
3 fonty, dodać 1 font, zmienić numer wersji, skompilować i wyeksportować `.tft`. Trzeba to zrobić
dla 3 wariantów, każdy zajmie ok. 10 minut.

## 1. Narzędzie

| | |
|---|---|
| Program | **Nextion Editor 1.68.2** (Windows), najnowsza wersja na stronie producenta |
| Pobieranie | strona: https://nextion.tech/nextion-editor/ · instalator: https://nextion.tech/download/nextion-setup-v1-68-2.exe · wersja ZIP (bez instalacji, można trzymać obok innych wersji): https://nextion.tech/download/nextion-setup-v1-68-2.zip |
| Nie używaj | **TJC USART HMI** (chiński edytor dla modeli TJC). Projekty są zapisane dla modelu Nextion **NX4832F035_011** i budowane w Nextion Editor |
| System | Windows 10/11 (edytor nie działa na Linuksie/macOS; ewentualnie maszyna wirtualna z Windows) |

Zanim otworzysz projekt: zrób kopię plików `.HMI` (albo pracuj na czystym `git status`). Wersja
edytora, w której projekty zapisano ostatnio, nie jest zapisana w pliku w sposób, który dałoby się
odczytać. Jeśli 1.68.2 zapyta o konwersję projektu do nowej wersji, zgódź się. Starsze edytory
mogą potem nie otworzyć pliku, dlatego commitujesz już przekonwertowany `.HMI`.

## 2. Warianty (odczytane z plików `.HMI`, sprawdzane testem)

| | EU | US pionowy | US poziomy |
|---|---|---|---|
| Projekt do otwarcia | `HMI/nspanel.HMI` | `HMI/US/portrait/nspanel_US_P.HMI` | `HMI/US/landscape/nspanel_US_L.HMI` |
| Model (Device) | NX4832F035_011 – Nextion Discovery 3,5" | NX4832F035_011 | NX4832F035_011 |
| Rozdzielczość panelu | 320×480, strony 480×320 (poziomo) | strony 320×480 (pionowo) | strony 480×320 (poziomo) |
| Kierunek ekranu (zapisana wartość) | 3 | 2 | 3 |
| Kodowanie znaków | utf-8 | utf-8 | utf-8 |
| Plik wyjściowy `.tft` | `HMI/nspanel.tft` | `HMI/US/portrait/nspanel_US_P.tft` | `HMI/US/landscape/nspanel_US_L.tft` |
| `--check` w kroku 6 | `eu` | `us-p` | `us-l` |
| Indeks nowego fontu 64 px | **8** | **7** | **8** |

**Nie zmieniaj ustawień Device** (model, kierunek, kodowanie). Kierunek ekranu edytor pokazuje w
stopniach. Zamiast zgadywać, które pole ile oznacza, porównaj wynik skryptem z kroku 6: zła wartość
od razu wyjdzie jako błąd.

## 3. Pliki do wgrania (gotowe w repo)

Wszystkie w `HMI/fonts/generated/`, wspólne dla 3 wariantów:

| Plik | Co to jest | Wysokość | Rozmiar |
|---|---|---|---|
| `icons-regular-32.zi` | Noto Sans Regular 32 + 7447 ikon MDI 7.4.47 | 32 px | 1,10 MiB |
| `icons-regular-48.zi` | Noto Sans Regular 48 + ikony | 48 px | 2,01 MiB |
| `icons-bold-80.zi` | Noto Sans Bold 80 + ikony | 80 px | 3,58 MiB |
| `icons-64.zi` | **nowy**: same ikony, ostre (siatka 2 px) | 64 px | 1,94 MiB |
| `simulator-test-eu.txt`, `-us-p.txt`, `-us-l.txt` | komendy do symulatora (krok 5) | | |

Odtworzenie (niekonieczne): `pip install pillow`, potem `python HMI/code_gen/fonts/build_fonts.py`.
Wynik jest deterministyczny, czyli bajt w bajt taki sam.

## 4. Fonty: indeks po indeksie

Kod HMI i backend wybierają font **po indeksie** (np. godzina = font 5, duża ikona = font 4, wybór
w siatce `...¬4`). Indeksy innych fontów nie mogą się przesunąć.

EU (`nspanel.HMI`) i US poziomy (`nspanel_US_L.HMI`) – po 8 fontów:

| Indeks | Teraz | Działanie |
|---|---|---|
| 0 | tekst 24 px (`noto-sans-24-sp5` / `-sp6`) | bez zmian |
| 1 | NotoSans-Regular 32 px z ikonami | **podmień** na `icons-regular-32.zi` |
| 2 | tekst 32 px (`noto-sans-32-sp5` / `-sp6`) | bez zmian |
| 3 | NotoSans-Regular 48 px z ikonami | **podmień** na `icons-regular-48.zi` |
| 4 | NotoSans-Bold 80 px z ikonami | **podmień** na `icons-bold-80.zi` |
| 5 | cyfry zegara 128 px | **podmień** na `clock-bold-128.zi` (dochodzi `°`, BUILD-55.md B) |
| 6 | tekst pionowy 16 px | bez zmian |
| 7 | `corners1` 15 px | bez zmian |
| **8** | – | **dodaj** `icons-64.zi` |

US pionowy (`nspanel_US_P.HMI`) – 7 fontów: indeksy 0–6 jak wyżej (0 i 2 to `-sp3`, 6 to tekst
pionowy 16 px, **nie ma** `corners1`), więc nowy font dodajesz jako **7**.

Jak podmienić font w panelu *Fonts* (po lewej na dole, zakładka obok *Pictures*):
1. Zaznacz font o danym indeksie i sprawdź na podglądzie wysokość (32/48/80).
2. Kliknij **Replace** i wskaż plik `.zi`. Indeks zostaje ten sam.
3. Jeśli w Twojej wersji nie ma *Replace* dla fontów: **Insert** (wstawia przed zaznaczonym),
   potem **Delete** na starym. Sprawdź listę: indeksy 0–7 muszą wyglądać jak w tabeli.
4. Nowy font: **Add** dodaje go na końcu listy, więc dostanie indeks 8 (US pionowy: 7).

Gdyby indeks nowego fontu wyszedł inny (0–9 dozwolone), ustaw w `panels.yaml` dla tego panelu
`largeIconFontId: <indeks>`. Domyślnie integracja przyjmuje 8, a dla `model: us-p` przyjmuje 7.

## 5. Kroki dla każdego wariantu

1. **Otwórz** projekt z tabeli w kroku 2 (*File → Open*).
2. **Fonty**: podmień indeksy 1, 3, 4 i 5 i dodaj font 64 px (krok 4).
   **Zmiany firmware 55** (kolorowe ikony pogody, poprawki zgłoszeń): [BUILD-55.md](BUILD-55.md), punkty A–F.
3. **Wersja**: strona `pageStartup` (lista *Page* po prawej), komponent tekstowy `tVersion`,
   atrybut `txt`: zmień `54` na **`55`**. To ten numer ekran wysyła przy starcie
   (`event,startup,55,eu`), a integracja porównuje go z pakietem.
4. **Compile** (pasek narzędzi). W oknie *Output* nie może być błędów (`Error`). Zanotuj zajętość
   pamięci i rozmiar. Szacunek: EU ok. 10,9 MiB, US pionowy ok. 11,0 MiB, US poziomy ok. 12,5 MiB,
   limit to 16 MB.
5. **Symulator (Debug)**, zanim cokolwiek wgrasz:
   1. Kliknij **Debug**. Symulator pokaże ekran startowy „Waiting for content…”. Ten ekran co kilka
      sekund włącza tryb ramek `recmod=1`, w którym ignoruje zwykłe komendy, więc trzeba z niego wyjść.
   2. **Kliknij 9 razy w kręcący się spinner.** To ukryte wejście otwiera stronę `pageTest`.
   3. Na `pageTest` kliknij **„disable recmod”** (szary przycisk po prawej, nad „bauds=115200”).
   4. W *Instruction Input Area* zaznacz **String** i *Keyboard Input*, wklej wszystkie linie z
      `HMI/fonts/generated/simulator-test-<wariant>.txt` (otwórz go w Notatniku; ikony wyglądają tam
      jak puste kwadraty albo litery hebrajskie i ormiańskie, i tak ma być), kliknij **Run all commands**.
   5. Oczekiwany wynik na stronie `pageIcons` (3 białe pola po prawej):
      - górne: domek (`home`), wygląda jak wcześniej;
      - środkowe: termometr z sondą (`thermometer-probe`). Jest nowy w MDI 7, więc na starym
        firmware byłoby tu puste pole;
      - dolne: duży, ostry termostat (`thermostat-auto`) z fontu 64 px. Jeśli jest pusty albo mały,
        to font ma inny indeks niż w komendzie `tTmp3.font=`.
6. **Eksport**: *File → TFT file output*, wybierz katalog i nazwę z tabeli w kroku 2 (nadpisz stary
   plik). Potem sprawdź wynik:
   ```bash
   python HMI/code_gen/fonts/hmi_info.py --check eu HMI/nspanel.tft
   python HMI/code_gen/fonts/hmi_info.py --check us-p HMI/US/portrait/nspanel_US_P.tft
   python HMI/code_gen/fonts/hmi_info.py --check us-l HMI/US/landscape/nspanel_US_L.tft
   ```
   Skrypt sprawdza model, kierunek ekranu, rozmiar względem 16 MB i kompletność pliku.
   `python HMI/code_gen/fonts/hmi_info.py <plik.HMI>` pokazuje tabelę fontów zapisanego projektu.
7. **Zapisz** projekt (*File → Save*). Commituj `.HMI` + `.tft`; workflow *nextion2text*
   zaktualizuje `n2t-out*`.
8. **Pakiet i flashowanie**: [FIRMWARE.pl.md](FIRMWARE.pl.md), kroki 3–4 (`make_firmware_package.py`
   z `--version 55`, potem encja *Firmware ekranu* w Home Assistant). Najpierw jeden panel.

US poziomy ma w repo też `nspanel_US_L-I.tft` (osobny, wcześniejszy wariant). Nie jest częścią tej
instrukcji, więc nie nadpisuj go plikiem z `nspanel_US_L.HMI`.

## 6. Checklista

- [ ] Nextion Editor 1.68.2, nie TJC USART HMI
- [ ] Kopia `.HMI` przed otwarciem (albo czyste `git status`)
- [ ] Device bez zmian: NX4832F035_011, kierunek jak w tabeli, utf-8
- [ ] Indeks 1 → `icons-regular-32.zi`, 3 → `icons-regular-48.zi`, 4 → `icons-bold-80.zi`
- [ ] `icons-64.zi` na końcu: indeks 8 (EU, US poziomy) / 7 (US pionowy)
- [ ] Indeks 5 → `clock-bold-128.zi`
- [ ] BUILD-55.md: A (obrazki pogody), C, D (tylko US pionowy), E, F
- [ ] `pageStartup.tVersion` = 55
- [ ] Compile bez błędów, rozmiar < 16 MB
- [ ] Debug: 3 ikony z pliku testowego widoczne
- [ ] `.tft` zapisany pod właściwą nazwą, `hmi_info.py --check <wariant>` = OK
- [ ] Projekt zapisany, `.HMI` + `.tft` w commicie
- [ ] Pakiet z `--version 55`, najpierw test na jednym panelu

## 7. Typowe błędy

| Objaw | Przyczyna | Co zrobić |
|---|---|---|
| Compile/eksport: brak miejsca, `.tft` > 16 MB, `--check`: „do not fit” | za duże fonty (np. font dodany dwa razy) | usuń duplikaty; nie dodawaj innych rozmiarów ikon niż w tabeli |
| `--check`: „wrong display model” | w *Device* wybrano inny model (np. TJC4832T035, NX4832T035) albo użyto TJC USART HMI | cofnij zmiany w projekcie i otwórz go ponownie w Nextion Editor |
| `--check`: „wrong display direction” | zmieniony kierunek ekranu albo wyeksportowano zły projekt pod tą nazwą | eksportuj z właściwego `.HMI` (tabela w kroku 2) |
| Panel nie przyjmuje pliku / flashowanie przerwane na początku | zły model, uszkodzony plik albo nie po HTTP | `--check`, pakiet ze skryptu, `firmware_base_url` po zwykłym HTTP |
| Zamiast liter kwadraty albo krzaki | font tekstowy podmieniony zamiast ikonowego albo zmienione kodowanie | indeksy 0/2 bez zmian, Device: utf-8 |
| Godzina albo ikony w złym rozmiarze, przesunięty układ | przesunięte indeksy (*Delete* przed *Add*/*Insert*) | przywróć `.HMI`, zrób kroki 4.1–4.4 jeszcze raz |
| Duże ikony w siatce puste lub małe | font 64 px ma inny indeks | `largeIconFontId` w `panels.yaml` albo popraw kolejność |
| Nowe ikony (np. `thermometer-probe`) puste na panelu | panel ma stare firmware (54) | wgraj 55; encja *Firmware ekranu* pokazuje wersję |
| Integracja nie proponuje aktualizacji | `tVersion` nie zmieniony albo `--version` w pakiecie ≠ 55 | popraw `tVersion`, zbuduj pakiet ponownie |
| Edytor pyta o konwersję projektu | projekt zapisany starszą wersją edytora | zgódź się (na kopii) i commituj przekonwertowany plik |
