# Firmware 55: kod do podmiany w Nextion Editor

Każdy plik to **pełny kod jednego zdarzenia**. W Nextion Editor zaznacz komponent (albo stronę),
wybierz zakładkę zdarzenia, kliknij w pole kodu, **Ctrl+A** i wklej cały plik (zastępuje stary kod).
Pliki generuje `python HMI/code_gen/patches_55.py` z obecnego kodu (`n2t-out`), więc pasują
1:1 do projektów w repo. Komponenty i obrazki dodajesz wcześniej według `HMI/BUILD-55.md` (A1, A2).

| Plik | Gdzie wkleić |
|---|---|
| `01-screensaver-strona-Preinitialize.txt` | strona `screensaver` (kliknij tło strony) → Preinitialize Event |
| `02-screensaver-tmSerial-TimerEvent.txt` | strona `screensaver`, komponent `tmSerial` (pasek pod ekranem) → Timer Event |
| `03-screensaver-tc0-TouchPressEvent.txt` | strona `screensaver`, komponent `tc0` → Touch Press Event |
| `10`…`22-<strona>-strona-Preinitialize.txt` (tylko `us-p`) | dana strona → Preinitialize Event (#1475) |
| `99-ramki-testowe-symulator.txt` | nie wklejać do kodu: ramki protokołu do testu w Debug (tryb Hex), z ID obrazków tego wariantu |

Folder: `eu` = `HMI/nspanel.HMI`, `us-p` = `HMI/US/portrait/nspanel_US_P.HMI`,
`us-l` = `HMI/US/landscape/nspanel_US_L.HMI`.

Poza tymi plikami zostają 2 zmiany w atrybutach (BUILD-55.md): font indeksu 5 (B) i
`cardGrid2` → `strCommand` → `txt_maxl` = 900 (C).
