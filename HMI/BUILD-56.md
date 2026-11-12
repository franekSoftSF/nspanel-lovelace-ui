# Firmware 56: poprawki błędów HMI krok po kroku

[English version](BUILD-56.en.md) · Wykonuj na projekcie firmware 55 (po [BUILD-55.md](BUILD-55.md)), razem z
[BUILD.md](BUILD.md) (kompilacja, test w symulatorze, eksport `.tft`).

Te błędy znalazło porównanie kodu ekranu (`HMI/n2t-out/*.txt`) z tym, co wysyła integracja (wersja
5.2.8, testy `tests_ha/test_views.py`). Tam, gdzie się dało, integracja już je omija. Ta lista to
zmiany, które naprawiają je w samym ekranie. Opisany jest model **EU** (jedyny budowany). Wersje US
mają te same strony, ale numery linii są inne.

Kod do wklejenia jest gotowy. Wklejasz go w panelu **Event** wybranej strony albo komponentu. Numery
linii odnoszą się do `HMI/n2t-out/<strona>.txt` i pomagają znaleźć miejsce.

| # | Strona | Błąd | Czy integracja go omija? |
|---|---|---|---|
| G | cardQR | Kod QR nie rysuje się przy jednym wierszu; kod ma najwyżej 80 znaków | tak (pusty 2. wiersz); limit 80 nie |
| H | cardAlarm | Przyciski uzbrajania i przycisk dodatkowy nie znikają po zmianie stanu | tak (ponowne otwarcie strony) |
| I | cardThermo | Po przejściu z dwóch nastaw na jedną zostają oba suwaki | tak (ponowne otwarcie strony) |
| J | popupThermo | Puste przyciski trybów są widoczne i można je nacisnąć | częściowo (ignoruje naciśnięcie) |
| K | cardMedia | Pierwszy wiersz nie otwiera wyboru źródła; 6. wiersz nie otwiera listy wyboru | nie |
| L | cardChart | Słupki znikają, gdy największa wartość > 176; polecenie ma 275 znaków | tak (dzielenie przez 10ⁿ, mniej słupków) |
| M | popupTimer | Edycja czasu kończy się na 59 minutach | nie |
| N | pageStartup | Numer wersji 56 | — |

## G. cardQR: kod przy jednym wierszu i dłuższy kod

**1.** Strona `cardQR`, zdarzenie obsługi poleceń `entityUpd` (komponent `tmSerial`, Timer Event,
okolice linii 599–608). Zamień końcowy fragment:

```
if(type2.txt=="delete"||type2.txt=="")
{
    if(type1.txt=="delete"||type1.txt=="")
    {
        qrcode m1.x,m1.y,200,65535,defaultBcoColor,-1,8,vaQR.txt
    }
}else
{
    qrcode m0.x,m0.y,200,65535,defaultBcoColor,-1,8,vaQR.txt
}
```

na:

```
if(type1.txt=="delete"||type1.txt=="")
{
    if(type2.txt=="delete"||type2.txt=="")
    {
        qrcode m1.x,m1.y,200,65535,defaultBcoColor,-1,8,vaQR.txt
    }else
    {
        qrcode m0.x,m0.y,200,65535,defaultBcoColor,-1,8,vaQR.txt
    }
}else
{
    qrcode m0.x,m0.y,200,65535,defaultBcoColor,-1,8,vaQR.txt
}
```

**2.** Zmienna `vaQR` (lista komponentów strony `cardQR`): atrybut **txt_maxl** z `80` na `160`
(kod Wi-Fi z 32-znakową nazwą sieci i 63-znakowym hasłem ma ok. 110 znaków).

## H. cardAlarm: przyciski znikają, gdy nie są potrzebne

Strona `cardAlarm`, obsługa `entityUpd` (`tmSerial`, okolice linii 736–830).

**1.** Każdy z 4 bloków `armN` (linie 738, 746, 754, 762) uzupełnij o gałąź `else`. Przykład dla
`arm1`, tak samo `arm2`, `arm3` i `arm4`:

```
if(arm1.txt!="")
{
    vis arm1,1
}else
{
    vis arm1,0
}
```

**2.** W bloku `//numpad status`, w gałęzi `if(tTmp.txt!="disable")`, **usuń** linię `vis b9,1`
(`b9` to przycisk dodatkowy, nie cyfra; o jego widoczności decyduje pole 27).

**3.** Blok `// extra button` (okolice linii 823) zamień na:

```
// extra button
spstr strCommand.txt,b9.txt,"~",27
if(b9.txt!="")
{
    vis b9,1
    spstr strCommand.txt,tTmp.txt,"~",28
    covx tTmp.txt,b9.pco,0,0
    spstr strCommand.txt,vaAddBtn.txt,"~",29
}else
{
    vis b9,0
    vaAddBtn.txt=""
}
```

## I. cardThermo: powrót do jednej nastawy

Strona `cardThermo`, obsługa `entityUpd` (okolice linii 1005–1021), blok `//Second Temperature`.
Po zamykającym `}` bloku `if(tTmp.txt!="")` dopisz gałąź `else`:

```
}else
{
    vis btUp1,0
    vis xTempDest1,0
    vis btDown1,0
    vis tCF1,0
    vis bUp2,0
    vis xTempDest2,0
    vis bDown2,0
    vis tCF2,0
    vis btUp,1
    vis xTempDest,1
    vis btDown,1
    vis tCF,1
}
```

## J. popupThermo: puste przyciski trybów

Strona `popupThermo` ma 3 grupy trybów: `bMode1-3` (przycisk `bModeNext`), `cMode1-3` (`cModeNext`)
i `dMode1-3` (`dModeNext`). W każdym z 3 przycisków `…ModeNext`, zdarzenie **Touch Press Event**,
dopisz na końcu (przykład dla grupy `b`; dla `c` i `d` zmień literę w nazwach):

```
if(bMode1.txt=="")
{
    vis bMode1,0
}else
{
    vis bMode1,1
}
if(bMode2.txt=="")
{
    vis bMode2,0
}else
{
    vis bMode2,1
}
if(bMode3.txt=="")
{
    vis bMode3,0
}else
{
    vis bMode3,1
}
```

Tak samo robi to już `popupInSel` (linie 621–704). Bez tej zmiany np. przy 2 trybach wentylatora
trzeci przycisk jest pusty, a jego naciśnięcie wysyła indeks, którego nie ma (integracja od 5.2.8 go
ignoruje).

## K. cardMedia: wybór źródła i 6. wiersz

**1.** Przycisk `bEntity1`, zdarzenie **Touch Press Event**: dopisz na końcu (jak w `bEntity2`–`bEntity5`):

```
if(type1.txt=="media_pl")
{
    page popupInSel
}
```

Pierwszy wiersz karty to odtwarzacz z karty, więc dotknięcie jego ikony otworzy wybór źródła
(`source_list`), który integracja już obsługuje.

**2.** Przycisk `bEntity6`, zdarzenie **Touch Press Event** (okolice linii 737): zamień

```
if(entn.txt=="input_sel")
```

na:

```
if(type6.txt=="input_sel")
```

## L. cardChart: skala słupków i dłuższe polecenie

Skala słupków liczy się dziś jako `(wysokość−24)/maksimum` na liczbach całkowitych. Przy maksimum
powyżej ok. 176 wynik to 0 i słupki znikają. Poprawka liczy skalę w setnych, tak jak `cardLChart`.
Nextion liczy od lewej do prawej, bez kolejności działań, więc dzielenie przez 100 musi stać zaraz po
mnożeniu przez `vaYUnit.val`.

**1.** `tmSerial`, linia 471: `vaYUnit.val=m0.h-24/vMax.val` zamień na:

```
vaYUnit.val=m0.h-24*100/vMax.val
```

**2.** W tych liniach dopisz `/100` po każdym iloczynie z `vaYUnit.val`:

| Linia | Było | Ma być |
|---|---|---|
| 265, 309, 556 | `-1*vaYUnit.val*vaValue.val+vaBottom.val+1` … `vaYUnit.val*vaValue.val-1` | `-1*vaYUnit.val*vaValue.val/100+vaBottom.val+1` … `vaYUnit.val*vaValue.val/100-1` |
| 267, 558 | `draw sya0,-1*vaYUnit.val*vaValue.val+vaBottom.val+1,…` | `draw sya0,-1*vaYUnit.val*vaValue.val/100+vaBottom.val+1,…` |
| 270, 562 | `sya1=-1*vaYUnit.val*vaValue.val+vaBottom.val` | `sya1=-1*vaYUnit.val*vaValue.val/100+vaBottom.val` |
| 305 | `fill sya0+1,vaYUnit.val*vaValue.val+vaBottom.val+1,vaUnit.val*4/100,-1*vaYUnit.val*vaValue.val-1,…` | `fill sya0+1,vaYUnit.val*vaValue.val/100+vaBottom.val+1,vaUnit.val*4/100,-1*vaYUnit.val*vaValue.val/100-1,…` |
| 484 | `-1*vaYUnit.val*sys1+vaBottom.val` (2 razy) | `-1*vaYUnit.val*sys1/100+vaBottom.val` (2 razy) |
| 499 | `sys1*10+sys2*-1*vaYUnit.val+vaBottom.val-10` | `sys1*10+sys2*-1*vaYUnit.val/100+vaBottom.val-10` |
| 557 | `-1*vaYUnit.val*vaValue.val+vaBottom.val` (2 razy) | `-1*vaYUnit.val*vaValue.val/100+vaBottom.val` (2 razy) |

Linie 265–309 są w komponencie `m0` (Hotspot, Touch Press Event: podświetlenie dotkniętego słupka),
pozostałe w `tmSerial`. Po zmianie wyszukaj na stronie `vaYUnit.val*`: każde wystąpienie poza linią
471 musi mieć zaraz po iloczynie `/100`.

**3.** Zmienna `strCommand` strony `cardChart`: **txt_maxl** z `275` na `750` (jak `cardMedia`).

## M. popupTimer: więcej niż 59 minut

Strona `popupTimer`: przyciski zmiany minut (okolice linii 437–608) ograniczają `n1` do 59. W każdym
bloku `if(n1.val>59)` zamień `59` na `999`, w obu miejscach:

```
if(n1.val>999)
{
    n1.val=999
}
```

Sekund (`n2`) nie zmieniaj, zostaje 59. Sprawdź też, czy komponent `n1` mieści 3 cyfry (atrybut
**lenth** = 0 albo 3). Integracja od 5.2.8 pokazuje godziny jako minuty (1:30:00 → 90:00). Home
Assistant przyjmuje `timer-start,00:90:00` jako 90 minut.

## N. Wersja 56

Strona `pageStartup`, komponent `tVersion`: zmień `55` na `56` (zgodnie z [BUILD.md](BUILD.md)).

## Po zbudowaniu

1. Test w symulatorze (*Debug*), ramki z [patches/55/eu/99-ramki-testowe-symulator.txt](patches/55/eu/99-ramki-testowe-symulator.txt)
   oraz:
   - `entityUpd` karty QR z jednym wierszem: kod ma się narysować z boku;
   - karta alarmu: najpierw 4 przyciski, potem 1, a 3 mają zniknąć;
   - wykres słupkowy z wartością 1600: słupki mają być widoczne.
2. Pakiet: `scripts/make_firmware_package.py --version 56 --release v<wersja>`.
3. Integracja, osobna zmiana po wydaniu firmware 56: dla `display_version >= 56` wyłączyć obejścia
   (dzielenie słupków przez 10ⁿ w `backend/charts.py`, limit kodu QR 80 → 160 w `backend/wifi.py`).
   Pusty 2. wiersz QR i ponowne otwieranie strony mogą zostać, bo nie szkodzą.
