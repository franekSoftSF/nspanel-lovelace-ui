# NSPanel Lovelace UI – integracja Home Assistant

[English version](INTEGRATION.md)

`custom_components/nspanel_lovelace_ui` to natywna integracja Home Assistant. Zastępuje aplikację AppDaemon
i dodatek (w Home Assistant nazywany teraz „aplikacją”). Działa wewnątrz Home Assistant, więc działa na **każdym typie
instalacji** (OS, Supervised, Container, Core). Nie potrzebuje tokenu dostępu ani drugiego połączenia MQTT.

| | Aplikacja AppDaemon (stara) | Dodatek / aplikacja `mqtt-manager` | Integracja (ta) |
|---|---|---|---|
| Gdzie działa | AppDaemon | osobny kontener (tylko HA OS / Supervised) | w samym Home Assistant |
| Połączenie z HA | wtyczka HASS w AppDaemon | websocket + token | w procesie (`hass`) |
| MQTT | wtyczka MQTT w AppDaemon | własny klient paho | integracja MQTT w HA |
| Konfiguracja | `apps.yaml` | `panels.yaml` + edytor www | `panels.yaml` (ten sam format) |
| Instalacja | HACS (zablokowany od 2026.11) | repozytorium aplikacji | Marketplace (własne repozytorium) albo ręczne kopiowanie |

Protokół panelu się nie zmienia: sterownik Berry w Tasmocie (`CustomSend`/`CustomRecv` przez MQTT) albo komponent
ESPHome z `use_ha_api: true`. Panelu ani firmware nie trzeba zmieniać.

## Wymagania

- Home Assistant **2026.10 lub nowszy** (testy z 2026.10.4 przez `pytest-homeassistant-custom-component`; pisane pod 2026.11).
- Firmware Tasmota: skonfigurowana [integracja MQTT](https://www.home-assistant.io/integrations/mqtt/) (ten sam broker
  co panele). Firmware ESPHome: integracja ESPHome z komponentem NSPanel.
- Panelem może sterować tylko jeden backend: **zatrzymaj aplikację AppDaemon i dodatek/aplikację**, zanim włączysz integrację.

## Instalacja

Na Home Assistant 2026.11 i nowszym nie da się zainstalować HACS. Zastąpił go wbudowany **Marketplace**
(Ustawienia → Marketplace), który czyta ten sam plik `hacs.json`. Wybierz jedną z dróg:

### A) Marketplace (własne repozytorium)

1. Ustawienia → Marketplace → połącz z GitHubem (wymagane dla własnych repozytoriów).
2. **Dodaj z linku** → `franekSoftSF/nspanel-lovelace-ui` (repozytorium musi być publiczne; zawiera `hacs.json`).
3. Zainstaluj *NSPanel Lovelace UI* i zrestartuj Home Assistant, jeśli pojawi się taka prośba.

Jeśli używałeś wersji AppDaemon z HACS: po migracji do Marketplace aplikacje AppDaemon nadal działają, ale nie
dostają już aktualizacji. Przejdź na tę integrację krok po kroku: [MIGRATION.pl.md](MIGRATION.pl.md).

### B) Ręczne kopiowanie (działa zawsze, bez połączenia z GitHubem)

1. Skopiuj `custom_components/nspanel_lovelace_ui` do `<config>/custom_components/nspanel_lovelace_ui`
   (Samba / SSH / File editor / `scp`). W instalacji Container `<config>` to folder zamontowany jako `/config`.
2. Zrestartuj Home Assistant.

Aktualizacja: skopiuj folder ponownie i zrestartuj.

## Konfiguracja

1. Utwórz `<config>/nspanel_lovelace_ui/panels.yaml` w tym samym formacie co dla dodatku
   ([przykład](examples/panels.yaml)). Klucze serwera i haseł MQTT oraz
   `home_assistant_*` są ignorowane, bo integracja używa połączeń samego Home Assistant.
2. Ustawienia → Urządzenia i usługi → Dodaj integrację → **NSPanel Lovelace UI**.
3. *Plik konfiguracji*: `nspanel_lovelace_ui/panels.yaml` (ścieżka względem folderu konfiguracji).

### Import istniejącej konfiguracji

W tym samym oknie podaj *Importuj z*:

- AppDaemon: np. `appdaemon/apps/apps.yaml`. Wpisy z `module: nspanel-lovelace-ui` albo
  `class: NsPanelLovelaceUIManager` zostaną przekonwertowane tym samym konwerterem co w edytorze dodatku
  (`timezone` → `timeZone`, pogoda wygaszacza → jawne encje itd.). Pozostałe aplikacje są pomijane.
- Dodatek: `/addon_configs/<slug>/panels.yaml` leży poza folderem konfiguracji HA, więc najpierw skopiuj go do folderu konfiguracji.

Import zapisuje plik konfiguracji i **nigdy nie nadpisuje** istniejącego. Ostrzeżenia pojawiają się jako
powiadomienie – przejrzyj je.

### Zmiana konfiguracji

Użyj **edytora kart** (niżej) albo edytuj `panels.yaml` i wywołaj akcję `nspanel_lovelace_ui.reload`
(albo przeładuj integrację). Inny plik: menu integracji → *Skonfiguruj ponownie*.

## Edytor kart

Menu boczne → **NSPanel** (tylko administratorzy). Edytor pracuje bezpośrednio na pliku, który czyta
integracja (`nspanel_lovelace_ui/panels.yaml` albo plik wybrany przy konfiguracji) – otwiera się też,
gdy plik jest błędny, żeby można go było w nim poprawić.

- **Panele i sekcje:** karty, ukryte karty, wygaszacz, ustawienia panelu, opcje globalne i cały plik jako
  YAML. Formularze dla każdego typu karty, który integracja potrafi pokazać: encje, siatka, kod QR,
  przepływ energii, odtwarzacz, termostat, alarm i odblokowanie (PIN).
- **Karty:** dodawanie (wybór typu), duplikowanie, usuwanie (z potwierdzeniem), zmiana kolejności
  przeciąganiem albo strzałkami (klawiatura: Alt+↑ / Alt+↓). Encje karty tak samo; pola encji podpowiadają
  encje z Home Assistant.
- **Ikony:** każde pole ikony pokazuje ikonę, którą pokaże panel. Kliknięcie otwiera galerię ikon z
  czcionki panelu (MDI 7.4.47): wyszukiwanie po nazwie i aliasie (działają też polskie słowa, np.
  *lampa*), sugestie dla encji, ostatnio używane, kategorie MDI; strzałki i Enter, na telefonie na cały
  ekran. Nazwę nadal można wpisać – pod polem pojawiają się podpowiedzi z podglądem. Puste pole pokazuje
  **ikonę domyślną** (przerywana ramka, „Domyślna: …”), którą integracja dobiera według domeny, stanu i
  klasy urządzenia; *Użyj domyślnej* czyści pole. Nazwa, której nie ma w czcionce, daje ostrzeżenie
  (panel pokazałby `alert-circle-outline`).
- **Walidacja w trakcie pisania**, według tych samych reguł, których integracja używa przy wczytywaniu
  pliku: błędy pojawiają się przy polu (i na liście *Problemy* z odnośnikiem do pola) i blokują zapis;
  encja, której nie ma w Home Assistant albo jest innego typu, to tylko ostrzeżenie.
- **Zapisz** (Ctrl+S): ponownie sprawdzane na serwerze, zapis atomowy; poprzedni plik zostaje jako
  `panels.yaml.bak` i w `.nspanel-backups/` (ostatnie 5). Jeśli plik zmienił się na dysku po wczytaniu go
  przez edytor, wybierasz: nadpisać albo wczytać plik i porzucić swoje zmiany. Komentarze z pliku nie
  są zachowywane (edytor uprzedza, gdy plik je ma).
- **Przeładuj panele:** przeładowuje integrację z zapisanym plikiem, bez restartu Home Assistant. Przy
  niezapisanych zmianach najpierw pyta (zapisz i przeładuj / przeładuj bez zapisu); wyjście ze strony z
  niezapisanymi zmianami też wymaga potwierdzenia.
- **Cofnij / ponów** (Ctrl+Z / Ctrl+Y), **wczytaj z pliku**, prosty podgląd karty.
- Po angielsku i po polsku (według języka Home Assistant), motyw jasny i ciemny, układ na telefon.

## Encje i powiadomienia

Każdy panel to urządzenie z encjami:

| Encja | Co robi |
|---|---|
| **Powiadomienie** (`notify`) | `notify.send_message`: na wygaszaczu tekst zastępuje pogodę do dotknięcia; na karcie otwiera stronę powiadomienia |
| **Obudź ekran** (`button`) | jak dotknięcie wygaszacza |
| **Strona** (`sensor`) | `screensaver` albo tytuł karty na ekranie (atrybuty `card_type`, `card_key`) |
| **Karta** (`select`) | pokazuje kartę, np. kamerę po dzwonku; przycisk wstecz wraca do poprzedniej karty |
| **Firmware ekranu** (`update`) | aktualizacja firmware ekranu z postępem |

Więcej opcji daje akcja `nspanel_lovelace_ui.notify`:

```yaml
action: nspanel_lovelace_ui.notify
data:
  panel: nspanel-1        # opcjonalnie, puste = wszystkie panele
  title: Pranie
  message: Pralka skończyła
  mode: popup             # auto | screensaver | popup | clear (zamyka powiadomienie na wygaszaczu)
  timeout: 60             # tylko strona powiadomienia, sekundy; 0 = do zamknięcia
  buzzer: true            # Tasmota: Buzzer 2,2,2
```

Diagnostyka do zgłoszenia błędu: Ustawienia → Urządzenia i usługi → NSPanel Lovelace UI → ⋮ → *Pobierz diagnostykę*.

## Różnice względem dodatku

- Edytor kart jest w menu bocznym Home Assistant (*Edytor kart* wyżej), a nie w dodatku.
- Jeden wpis integracji steruje wszystkimi panelami (`single_config_entry`).
- Domyślna `timeZone` to strefa czasowa Home Assistant zamiast `Europe/Berlin`.

## Rozwój

```bash
docker build -t nspanel-ha-tests -f tests_ha/Dockerfile .
docker run --rm -v "$PWD:/work" nspanel-ha-tests
```

Testy korzystają z `pytest-homeassistant-custom-component` (Python 3.14). Home Assistant nie działa na Windows, więc
uruchamiaj je w Dockerze (albo w WSL / Linux / macOS z venv Pythona 3.14: `pip install -r requirements_test.txt && pytest`).

### Opcje wygaszacza (firmware 55)

| Opcja (poziom panelu) | Domyślnie | Znaczenie |
|---|---|---|
| `weatherIcons` | `color` | `color`: kolorowe obrazki pogody (Meteocons) przy firmware 55+ i domyślnym czarnym tle wygaszacza; `font`: zawsze jednokolorowe ikony MDI |
| `weatherPictureBase` | 26 (EU), 24 (US) | ID pierwszego obrazka pogody, jeśli zaimportowano je w innym miejscu (HMI/BUILD-55.md) |
| `timeTemplate` | – | szablon wyświetlany zamiast godziny, np. `"{{ states('sensor.nspanel_temp') }}°"` (`°` wymaga firmware 55) |
| `largeIconFontId` | 8 (US pionowy: 7) | indeks fontu ikon 64 px dla `font: large-icon` |

Ikony prognozy mają teraz warunki i kolor swojego dnia, częściowe zachmurzenie w nocy pokazuje
księżyc, a siatka przełącza się między 3×2 i 4×2 według liczby *widocznych* elementów.

## Firmware ekranu

Integracja może serwować z Home Assistant firmware ekranu (.tft) i sterownik Berry dla Tasmoty oraz
wgrywać go encją aktualizacji **Firmware ekranu** każdego panelu. Budowa firmware z fontami ikon MDI 7,
wydanie i instalacja pakietu: [HMI/FIRMWARE.pl.md](HMI/FIRMWARE.pl.md).

## Historia zmian

### 5.2.6
- **Edytor kart – wybór ikon:** galeria ikon panelu (wyszukiwanie po nazwie i aliasie, polskie słowa,
  sugestie dla encji, ostatnio używane, kategorie, klawiatura, układ na telefon), podgląd przy każdym
  polu ikony, **ikona domyślna** encji przy pustym polu, podpowiedzi z podglądem przy wpisywaniu.
  Zastępuje nieczytelny obrazek obok nazwy.
- Nieznane nazwy ikon (których nie ma w czcionce panelu) dają ostrzeżenie przy polu zamiast cichego
  `alert-circle-outline` na panelu.

### 5.2.5
- **Edytor kart** w menu bocznym (administratorzy): formularze dla każdego typu karty, walidacja na
  żywo przy polu, Zapisz (atomowo, kopie zapasowe, wykrywanie konfliktu) i Przeładuj panele; patrz
  *Edytor kart*.
- Jeden schemat dla wczytywania i edycji (`backend/config_schema.py`): integracja i edytor stosują te
  same reguły; timeFormat/dateFormat/locale na najwyższym poziomie działa teraz też dla paneli.

### 5.2.4
- **Obudź ekran** działa jak dotknięcie wygaszacza (panel pokazuje swoją kartę z normalną jasnością);
  wysyłane wcześniej polecenie HMI `wake` nie rozjaśniało prawdziwego panelu.

### 5.2.3
- Encje każdego panelu: **Powiadomienie** (`notify.send_message`), przycisk **Obudź ekran**, czujnik
  **Strona**, wybór **Karta**; akcja `nspanel_lovelace_ui.notify` (tekst na wygaszaczu albo strona
  powiadomienia, czas, buzzer, zamknięcie); pobieranie diagnostyki.

### 5.2.2
Poprawki z migracji prawdziwego panelu (HMI 53 z 2023, AppDaemon z HACS) na firmware 55:
- Ekrany, które nie proszą o zawartość wygaszacza (starsze wydania HMI 53), dostają ją zaraz po
  zmianie strony, jak w AppDaemon – pogoda nie jest już pusta przed aktualizacją firmware.
- Okienko aktualizacji ekranu, którego nie widać (przykrył je inny backend), nie blokuje już panelu:
  następne dotknięcie je zamyka.
- Import: panel bez kart dostaje przykładową kartę zamiast błędu; brakujący `timeZone` bierze strefę
  czasową Home Assistant; kreator znajduje plik aplikacji AppDaemon także w podfolderach `appdaemon/apps`;
  zniknęła podpowiedź dotycząca tylko dodatku.
- Ikona integracji (Home Assistant 2026.3+ czyta ją z `brand/`); README: zdalna aktualizacja.
- Repozytorium zawiera teraz tylko integrację: usunięto aplikację AppDaemon, dodatek, ioBroker, IP-Symcon,
  Node-RED, dokumentację mkdocs i ich workflowy (zostają w historii git i w oryginalnym projekcie).
  Przykładowa konfiguracja: [examples/panels.yaml](examples/panels.yaml).

### 5.2.1
- Pakiet firmware ekranu jest pobierany automatycznie z wydania GitHub o numerze integracji, gdy go nie ma
  albo jest starszy (sprawdzany SHA-256, potem przeładowanie). Akcja `nspanel_lovelace_ui.download_firmware`,
  wyłączenie: `firmware_download: false` w `panels.yaml`. Błąd pobierania widać w Naprawach.

### 5.2.0
- Pogoda: każdy dzień prognozy ma własną ikonę i kolor (wcześniej kolor bieżącej pogody), warianty
  nocne, kolory jak w Home Assistant, poprawiony kolor `windy-variant`, ikona dla `exceptional`.
- Kolorowe obrazki pogody (Meteocons) z firmware 55 (`weatherIcons`), `timeTemplate` zamiast zegara
  (upstream #1405), układ siatki według widocznych elementów (upstream #1190).
- Postęp i błędy aktualizacji ekranu w encji aktualizacji (raportuje je sterownik Berry 10, upstream #995).
- Ikony: Material Design Icons 7.4.47 (7447 ikon, działają aliasy przemianowanych ikon). Nowe ikony
  wymagają firmware ekranu 55, zobacz HMI/FIRMWARE.pl.md.
- Encja aktualizacji „Firmware ekranu” dla każdego panelu i akcja `nspanel_lovelace_ui.update_berry_driver`:
  .tft i sterownik Berry są serwowane lokalnie przez Home Assistant z `<config>/nspanel_lovelace_ui/firmware/`.
- Nowy font siatki `font: large-icon` (font ikon 64 px z firmware 55, `largeIconFontId`, domyślnie 8).
- Opcjonalne `firmware_base_url` w panels.yaml (adres po zwykłym HTTP, z którego panele pobierają pliki).
- Migracja: `nspanel-firmware.zip` wrzucony do `<config>/nspanel_lovelace_ui/` jest sprawdzany i rozpakowywany
  przy przeładowaniu; import `apps.yaml` rozwiązuje `!secret`, kreator sam znajduje `appdaemon/apps/apps.yaml` i
  wyłącza zaimportowane aplikacje AppDaemon (`disable: true`, kopia `apps.yaml.nspanel-backup`).
  Instrukcja przejścia z wersji AppDaemon/HACS: [MIGRATION.pl.md](MIGRATION.pl.md).

### 5.1.0
- Zduplikowane klucze w `panels.yaml` nie zatrzymują już integracji. Używana jest ostatnia wartość (jak w AppDaemon),
  a ostrzeżenie z numerem linii pojawia się w Ustawienia → Naprawy (upstream #1480).
- Panele są budzone tylko przez zmiany stanu encji użytych w `panels.yaml` (plus `sun.sun`). Szablony nadal śledzą
  wszystkie encje, których używają (upstream #1465).
- `navItem1` / `navItem2` z polem `entity` zastępują lewy / prawy przycisk nawigacji na każdej karcie, także ukrytej,
  np. `navItem1: {entity: navigate.home}` zamiast strzałki w górę (upstream #1470, zachowanie z AppDaemon).
- Wyładowanie integracji w trakcie startu panelu nie zostawia już jego wątku na 5 sekund.
