# Firmware 56: HMI bug fixes step by step

[Polska wersja](BUILD-56.md) · Apply these to the firmware 55 project (after [BUILD-55.en.md](BUILD-55.en.md)),
together with [BUILD.en.md](BUILD.en.md) (compile, simulator test, `.tft` export).

These bugs were found by comparing the display code (`HMI/n2t-out/*.txt`) with what the integration
sends (version 5.2.8, tests `tests_ha/test_views.py`). Where possible, the integration already works
around them. This list fixes them in the display itself. It describes the **EU** model (the only
one built). The US variants have the same pages but different line numbers.

The code is ready to paste into the **Event** panel of the page or component named in each step.
Line numbers refer to `HMI/n2t-out/<page>.txt` and help to find the place.

| # | Page | Bug | Integration workaround? |
|---|---|---|---|
| G | cardQR | No QR code with exactly one row; the code holds at most 80 characters | yes (blank 2nd row); not for the 80 limit |
| H | cardAlarm | Arm buttons and the extra button never hide after a state change | yes (opens the page again) |
| I | cardThermo | After switching from two set points to one, both controls stay | yes (opens the page again) |
| J | popupThermo | Empty mode buttons are visible and can be pressed | partly (the press is ignored) |
| K | cardMedia | The first row does not open the source list; row 6 does not open an input_select | no |
| L | cardChart | Bars vanish when the top value is over 176; the command holds 275 characters | yes (divide by 10ⁿ, fewer bars) |
| M | popupTimer | Editing stops at 59 minutes | no |
| N | pageStartup | Version number 56 | — |

## G. cardQR: the code with one row, and longer codes

**1.** Page `cardQR`, the `entityUpd` handler (`tmSerial`, Timer Event, about lines 599–608).
Replace the final part:

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

with:

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

**2.** Variable `vaQR` (component list of `cardQR`): set **txt_maxl** from `80` to `160`. A Wi-Fi code with
a 32-character network name and a 63-character password has about 110 characters.

## H. cardAlarm: buttons hide when they are not needed

Page `cardAlarm`, the `entityUpd` handler (`tmSerial`, about lines 736–830).

**1.** Add an `else` branch to each of the 4 `armN` blocks (lines 738, 746, 754, 762). Example for
`arm1`; the same for `arm2`, `arm3` and `arm4`:

```
if(arm1.txt!="")
{
    vis arm1,1
}else
{
    vis arm1,0
}
```

**2.** In the `//numpad status` block, branch `if(tTmp.txt!="disable")`, **remove** the line `vis b9,1`.
`b9` is the extra button, not a digit; field 27 decides whether it is shown.

**3.** Replace the `// extra button` block (about line 823) with:

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

## I. cardThermo: back to one set point

Page `cardThermo`, the `entityUpd` handler (about lines 1005–1021), block `//Second Temperature`.
After the closing `}` of `if(tTmp.txt!="")` add an `else` branch:

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

## J. popupThermo: empty mode buttons

Page `popupThermo` has 3 mode groups: `bMode1-3` (button `bModeNext`), `cMode1-3` (`cModeNext`) and
`dMode1-3` (`dModeNext`). In each of the 3 `…ModeNext` buttons, **Touch Press Event**, append the code
below. It is shown for group `b`; for `c` and `d` change the letter in the names:

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

`popupInSel` already does this (lines 621–704). Without it, a fan with 2 modes shows an empty third
button, and pressing it sends an index that does not exist (the integration ignores it since 5.2.8).

## K. cardMedia: source list and row 6

**1.** Button `bEntity1`, **Touch Press Event**: append the code below (as in `bEntity2`–`bEntity5`):

```
if(type1.txt=="media_pl")
{
    page popupInSel
}
```

The first row is the card's player. Touching its icon then opens the source list (`source_list`),
which the integration already handles.

**2.** Button `bEntity6`, **Touch Press Event** (about line 737): replace

```
if(entn.txt=="input_sel")
```

with:

```
if(type6.txt=="input_sel")
```

## L. cardChart: bar scale and a longer command

Today the bar scale is `(height-24)/maximum` in integers, so above a maximum of about 176 it becomes 0
and the bars vanish. The fix computes the scale in hundredths, like `cardLChart` does. Nextion
evaluates from left to right with no operator precedence, so the division by 100 must come right
after the multiplication by `vaYUnit.val`.

**1.** `tmSerial`, line 471: replace `vaYUnit.val=m0.h-24/vMax.val` with:

```
vaYUnit.val=m0.h-24*100/vMax.val
```

**2.** On these lines, add `/100` after every product with `vaYUnit.val`:

| Line | Before | After |
|---|---|---|
| 265, 309, 556 | `-1*vaYUnit.val*vaValue.val+vaBottom.val+1` … `vaYUnit.val*vaValue.val-1` | `-1*vaYUnit.val*vaValue.val/100+vaBottom.val+1` … `vaYUnit.val*vaValue.val/100-1` |
| 267, 558 | `draw sya0,-1*vaYUnit.val*vaValue.val+vaBottom.val+1,…` | `draw sya0,-1*vaYUnit.val*vaValue.val/100+vaBottom.val+1,…` |
| 270, 562 | `sya1=-1*vaYUnit.val*vaValue.val+vaBottom.val` | `sya1=-1*vaYUnit.val*vaValue.val/100+vaBottom.val` |
| 305 | `fill sya0+1,vaYUnit.val*vaValue.val+vaBottom.val+1,vaUnit.val*4/100,-1*vaYUnit.val*vaValue.val-1,…` | `fill sya0+1,vaYUnit.val*vaValue.val/100+vaBottom.val+1,vaUnit.val*4/100,-1*vaYUnit.val*vaValue.val/100-1,…` |
| 484 | `-1*vaYUnit.val*sys1+vaBottom.val` (twice) | `-1*vaYUnit.val*sys1/100+vaBottom.val` (twice) |
| 499 | `sys1*10+sys2*-1*vaYUnit.val+vaBottom.val-10` | `sys1*10+sys2*-1*vaYUnit.val/100+vaBottom.val-10` |
| 557 | `-1*vaYUnit.val*vaValue.val+vaBottom.val` (twice) | `-1*vaYUnit.val*vaValue.val/100+vaBottom.val` (twice) |

Lines 265–309 are in component `m0` (Hotspot, Touch Press Event, which highlights the touched bar).
The others are in `tmSerial`. Afterwards, search the page for `vaYUnit.val*`: every occurrence
except line 471 must have `/100` right after the product.

**3.** Variable `strCommand` of `cardChart`: set **txt_maxl** from `275` to `750` (like `cardMedia`).

## M. popupTimer: more than 59 minutes

Page `popupTimer`: the minute buttons (about lines 437–608) cap `n1` at 59. In every
`if(n1.val>59)` block, replace `59` with `999` in both places:

```
if(n1.val>999)
{
    n1.val=999
}
```

Leave the seconds (`n2`) at 59. Also check that component `n1` shows 3 digits (attribute **lenth**
= 0 or 3). Since 5.2.8 the integration shows hours as minutes (1:30:00 → 90:00), and Home
Assistant accepts `timer-start,00:90:00` as 90 minutes.

## N. Version 56

Page `pageStartup`, component `tVersion`: change `55` to `56` (as in [BUILD.en.md](BUILD.en.md)).

## After the build

1. Test in the simulator (*Debug*) with the frames from [patches/55/eu/99-ramki-testowe-symulator.txt](patches/55/eu/99-ramki-testowe-symulator.txt), plus:
   - a QR card `entityUpd` with one row: the code is drawn on the side;
   - an alarm card with 4 buttons, then with 1: the other 3 disappear;
   - a bar chart with the value 1600: the bars are visible.
2. Package: `scripts/make_firmware_package.py --version 56 --release v<version>`.
3. Integration, a separate change after firmware 56 is released: for `display_version >= 56`, turn
   off the workarounds:
   - the 10ⁿ bar division in `backend/charts.py`;
   - the QR code limit in `backend/wifi.py` (80 → 160).

   The blank second QR row and re-opening the page can stay, as they do no harm.
