# Firmware 55: zmiany w HMI krok po kroku

[English version](BUILD-55.en.md) · Wykonuj razem z [BUILD.md](BUILD.md), po podmianie fontów (krok 4) i przed *Compile*.

Każdą zmianę robisz w 3 projektach (EU, US pionowy, US poziomy), chyba że opis mówi inaczej. Kod
do wklejania jest gotowy. Wklejasz go w panelu **Event** (na dole po prawej) wybranej strony albo
komponentu, w zakładce zdarzenia podanej w opisie. Wszystkie zmiany backendu (integracja) są już
zrobione. Działają dopiero z tym firmware, a stare firmware je ignoruje.

| # | Zmiana | Strony | Warianty |
|---|---|---|---|
| A | Kolorowe ikony pogody (obrazki) | screensaver | wszystkie |
| B | Znak `°` w foncie zegara (`timeTemplate`) | fonty | wszystkie |
| C | Dłuższy bufor poleceń w siatce 4×2 (#1456) | cardGrid2 | wszystkie |
| D | Prośba o treść po wejściu na stronę (#1475) | 11 stron | tylko US pionowy |
| E | AM/PM nie nachodzi na godzinę, długa data mieści się (#1485) | screensaver | wszystkie |
| F | Ikony statusu nie znikają po zmianie koloru tła (#1026) | screensaver | wszystkie |

## A. Kolorowe ikony pogody

**1. Obrazki** (`HMI/pictures/weather/`, 30 plików PNG: `00-main-…` do `29-forecast-…`).
W panelu *Picture* (na dole po lewej) kliknij **+**, zaznacz wszystkie 30 plików i dodaj.
Kolejność ma znaczenie, bo backend wylicza ID z numeru pliku:

| Wariant | ID `00-main-clear-day` | ID `29-forecast-tornado` |
|---|---|---|
| EU | 26 | 55 |
| US pionowy / poziomy | 24 | 53 |

Po dodaniu sprawdź na liście 3 pozycje: pierwszą (słońce 70×66), ID 15. obrazka (`15-forecast-clear-day`,
słońce 40×40) i ostatnią (tornado 40×40). Jeśli kolejność się pomieszała (zdarza się przy zaznaczaniu
w oknie Windows), usuń dodane obrazki i dodaj je jeszcze raz w 2 turach: najpierw `00`–`14`, potem `15`–`29`.

**2. Komponenty** na stronie `screensaver`: z *Toolbox* przeciągnij 5 razy **Picture** i ustaw atrybuty
(`objname`, `pic`, `x`, `y`; `pic` = ID pierwszego obrazka, czyli 26 w EU i 24 w US):

| objname | EU x, y | US poziomy x, y | US pionowy x, y | pic |
|---|---|---|---|---|
| `pMain` | 26, 208 | 41, 208 | 125, 259 | 26 / 24 |
| `pF1` | 146, 242 | 161, 242 | 23, 410 | 41 / 39 |
| `pF2` | 228, 242 | 243, 242 | 103, 410 | 41 / 39 |
| `pF3` | 309, 242 | 324, 242 | 183, 410 | 41 / 39 |
| `pF4` | 390, 242 | 405, 242 | 263, 410 | 41 / 39 |

**3. Kod.** Strona `screensaver`, zdarzenie **Preinitialize Event**: dopisz na końcu:

```
vis pMain,0
vis pF1,0
vis pF2,0
vis pF3,0
vis pF4,0
```

Ten sam kod dopisz w handlerze `notify`, w gałęzi, która **pokazuje** powiadomienie (po
`vis tNotifyText,1`). W gałęzi `else` (po `vis tNotifyText,0`) dopisz przywracanie obrazków:

```
if(tMainIcon.txt=="")
{
    vis pMain,1
}
if(tF1Icon.txt=="")
{
    vis pF1,1
}
if(tF2Icon.txt=="")
{
    vis pF2,1
}
if(tF3Icon.txt=="")
{
    vis pF3,1
}
if(tF4Icon.txt=="")
{
    vis pF4,1
}
```

(Backend zostawia pustą ikonę z fontu tam, gdzie pokazuje obrazek, więc pusty tekst oznacza obrazek.)

Ten sam kod przywracania wklej też w komponencie **`tc0`** (TouchCap, pasek komponentów pod ekranem),
zdarzenie **Touch Press Event**, po `vis tNotifyText,0` (wewnątrz `if(dim!=0)`): dotknięcie ekranu też
zamyka powiadomienie. Handlery poleceń (`notify`, `weatherUpdate`, `color`) są w komponencie **`tmSerial`**
(Timer), zdarzenie **Timer Event**.

**4. Nowe polecenie `weatherPics`.** Strona `screensaver`, komponent timera z obsługą poleceń (to ten
sam kod, w którym jest `if(tInstruction.txt=="weatherUpdate"…)`). Wklej ten blok tuż **przed**
linią `if(tInstruction.txt=="color"&&tNotifyHead.txt==""&&tNotifyText.txt=="")`:

```
if(tInstruction.txt=="weatherPics"&&tNotifyHead.txt==""&&tNotifyText.txt=="")
{
    spstr strCommand.txt,tTmp.txt,"~",1
    if(tTmp.txt=="")
    {
        vis pMain,0
    }else
    {
        covx tTmp.txt,sys0,0,0
        pMain.pic=sys0
        vis pMain,1
    }
    spstr strCommand.txt,tTmp.txt,"~",2
    if(tTmp.txt=="")
    {
        vis pF1,0
    }else
    {
        covx tTmp.txt,sys0,0,0
        pF1.pic=sys0
        vis pF1,1
    }
    spstr strCommand.txt,tTmp.txt,"~",3
    if(tTmp.txt=="")
    {
        vis pF2,0
    }else
    {
        covx tTmp.txt,sys0,0,0
        pF2.pic=sys0
        vis pF2,1
    }
    spstr strCommand.txt,tTmp.txt,"~",4
    if(tTmp.txt=="")
    {
        vis pF3,0
    }else
    {
        covx tTmp.txt,sys0,0,0
        pF3.pic=sys0
        vis pF3,1
    }
    spstr strCommand.txt,tTmp.txt,"~",5
    if(tTmp.txt=="")
    {
        vis pF4,0
    }else
    {
        covx tTmp.txt,sys0,0,0
        pF4.pic=sys0
        vis pF4,1
    }
}
```

Test w symulatorze (po wyjściu z trybu ramek, BUILD.md krok 5): `page screensaver`, potem
`pMain.pic=26` i `vis pMain,1` (w US: 24). Słońce powinno pojawić się w miejscu ikony pogody.

## B. Font zegara z `°`

W panelu *Fonts* zaznacz **indeks 5** (`NotoSand-Bold-TxtOnly-128`, h:128) i podmień (🔄) na
`HMI/fonts/generated/clock-bold-128.zi`. Wynik: `NotoSand-Bold-TxtOnly-128(h:128, encode:utf-8, qty:96)` (nazwa zostaje, liczba znaków rośnie z 95 do 96).
Dzięki temu `timeTemplate` w `panels.yaml` (np. `"{{ states('sensor.nspanel_temp') }}°"`) pokaże
temperaturę zamiast godziny. W US pionowym pole godziny ma 320 px, więc mieści się „21.5°” bez litery „C”.

## C. cardGrid2: dłuższy bufor (#1456)

Strona `cardGrid2`, zmienna **`strCommand`**, atrybut `txt_maxl`: zmień `700` na **`900`**.
Jeśli *Compile* zgłosi brak pamięci RAM na tej stronie, ustaw `800` (to wartość sprawdzona w zgłoszeniu).

## D. Tylko US pionowy: prośba o treść (#1475)

W US pionowym poniższe strony nie wysyłają prośby o treść, więc po przejściu na nie ekran
zostaje pusty: `cardEntities`, `cardThermo`, `cardMedia`, `cardAlarm`, `cardQR`, `cardPower`,
`cardChart`, `cardLChart`, `screensaver`, `screensaver2`, `screensaver3`. Na każdej z nich, w
zdarzeniu **Preinitialize Event**, wklej na **samym początku** (tak jak w EU):

```
tSend.txt="event,renderCurrentPage"
//send calc crc
btlen tSend.txt,sys0
crcrest 1,0xffff // reset CRC
crcputh 55 bb
crcputs sys0,2
crcputs tSend.txt,0
//send cmd
printh 55 bb
prints sys0,2
prints tSend.txt,0
prints crcval,2
```

## E. AM/PM i długa data (#1485)

Strona `screensaver`, handler `time`: po bloku `if(tAMPM.txt=="") … else …` dopisz:

```
if(p0.w!=320)
{
    if(tAMPM.txt=="")
    {
        tTime.xcen=1
    }else
    {
        tTime.xcen=0
    }
}
```

(Z AM/PM godzina wyrównuje się do lewej i nie wchodzi pod AM/PM; w US pionowym AM/PM jest pod godziną.)

Handler `date`: po `tDate.txt=pageIcons.vaDate.txt` dopisz:

```
if(p0.w==320)
{
    strlen tDate.txt,sys0
    if(sys0>22)
    {
        tDate.font=0
    }else
    {
        tDate.font=2
    }
}
```

(W US pionowym długa data, np. „Wednesday, 11 November 2026”, dostaje mniejszy font 24 px.)

## F. Ikony statusu po zmianie koloru (#1026)

Strona `screensaver`, handler `color`: na końcu bloku, tuż przed jego zamykającym `}`, dopisz:

```
ref tIcon1
ref tIcon2
```

## Po zmianach

1. **Compile.** Bez błędów; rozmiar powinien urosnąć o ok. 0,2 MB (obrazki) i zmieścić się w 16 MB.
2. **Debug.** Test ikon z BUILD.md (krok 5) i test obrazka z punktu A.
3. **Eksport** `.tft` (BUILD.md krok 6), potem `hmi_info.py --check <wariant>`.
4. Jeśli edytor odrzuci przypisanie atrybutu (np. `xcen` albo `font` „nie można zmienić w czasie
   działania”), zanotuj komunikat i pomiń tę jedną zmianę. Reszta działa niezależnie.
