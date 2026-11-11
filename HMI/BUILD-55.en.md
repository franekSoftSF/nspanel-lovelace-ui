# Firmware 55: HMI changes step by step

[Polska wersja](BUILD-55.md) · Do this together with [BUILD.en.md](BUILD.en.md), after replacing the fonts (step 4) and before *Compile*.

Make every change in the 3 projects (EU, US portrait, US landscape) unless the text says otherwise.
The code is ready to paste. Paste it in the **Event** panel (bottom right) of the given page or
component, on the tab of the named event. All backend (integration) changes are already done. They
take effect only with this firmware; older firmware ignores them.

| # | Change | Pages | Variants |
|---|---|---|---|
| A | Colour weather icons (pictures) | screensaver | all |
| B | Degree sign in the clock font (`timeTemplate`) | fonts | all |
| C | Longer command buffer in the 4×2 grid (#1456) | cardGrid2 | all |
| D | Ask for content when a page opens (#1475) | 11 pages | US portrait only |
| E | AM/PM does not overlap the time, long dates fit (#1485) | screensaver | all |
| F | Status icons survive a background colour change (#1026) | screensaver | all |

## A. Colour weather icons

**1. Pictures** (`HMI/pictures/weather/`, 30 PNG files: `00-main-…` to `29-forecast-…`).
In the *Picture* panel (bottom left) click **+**, select all 30 files and add them. The order matters,
because the backend derives the IDs from the file number:

| Variant | ID of `00-main-clear-day` | ID of `29-forecast-tornado` |
|---|---|---|
| EU | 26 | 55 |
| US portrait / landscape | 24 | 53 |

After adding, check 3 entries: the first (sun 70×66), the 15th picture (`15-forecast-clear-day`,
sun 40×40) and the last (tornado 40×40). If the order got mixed up (Windows' file dialog sometimes
does this), delete the added pictures and add them again in 2 rounds: first `00`–`14`, then `15`–`29`.

**2. Components** on the page `screensaver`: drag **Picture** from the *Toolbox* 5 times and set the
attributes (`objname`, `pic`, `x`, `y`; `pic` = ID of the first picture, 26 in EU and 24 in US):

| objname | EU x, y | US landscape x, y | US portrait x, y | pic |
|---|---|---|---|---|
| `pMain` | 26, 208 | 41, 208 | 125, 259 | 26 / 24 |
| `pF1` | 146, 242 | 161, 242 | 23, 410 | 41 / 39 |
| `pF2` | 228, 242 | 243, 242 | 103, 410 | 41 / 39 |
| `pF3` | 309, 242 | 324, 242 | 183, 410 | 41 / 39 |
| `pF4` | 390, 242 | 405, 242 | 263, 410 | 41 / 39 |

**3. Code.** Page `screensaver`, **Preinitialize Event**: append:

```
vis pMain,0
vis pF1,0
vis pF2,0
vis pF3,0
vis pF4,0
```

Append the same code in the `notify` handler, in the branch that **shows** the notification (after
`vis tNotifyText,1`). In the `else` branch (after `vis tNotifyText,0`) append the restore code:

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

(The backend leaves the font icon empty wherever it shows a picture, so an empty text means a picture.)

Paste the same restore code in component **`tc0`** (TouchCap, component strip below the screen),
**Touch Press Event**, after `vis tNotifyText,0` (inside `if(dim!=0)`): touching the screen also closes
the notification. The command handlers (`notify`, `weatherUpdate`, `color`) are in component **`tmSerial`**
(Timer), **Timer Event**.

**4. New command `weatherPics`.** Page `screensaver`, the timer component with the command handling
(the code that contains `if(tInstruction.txt=="weatherUpdate"…)`). Paste this block right **before**
the line `if(tInstruction.txt=="color"&&tNotifyHead.txt==""&&tNotifyText.txt=="")`:

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

Simulator test (after leaving the frame mode, BUILD.en.md step 5): `page screensaver`, then
`pMain.pic=26` and `vis pMain,1` (US: 24). A sun should appear where the weather icon is.

## B. Clock font with `°`

In the *Fonts* panel select **index 5** (`NotoSand-Bold-TxtOnly-128`, h:128) and replace it (🔄) with
`HMI/fonts/generated/clock-bold-128.zi`. Result: `NotoSand-Bold-TxtOnly-128(h:128, encode:utf-8, qty:96)` (the name stays, the glyph count grows from 95 to 96).
With it, `timeTemplate` in `panels.yaml` (e.g. `"{{ states('sensor.nspanel_temp') }}°"`) shows a
temperature instead of the time. On US portrait the time field is 320 px wide, so "21.5°" fits, without the "C".

## C. cardGrid2: longer buffer (#1456)

Page `cardGrid2`, variable **`strCommand`**, attribute `txt_maxl`: change `700` to **`900`**.
If *Compile* reports that the page runs out of RAM, use `800` (the value verified in the issue).

## D. US portrait only: ask for content (#1475)

On US portrait these pages do not ask for their content, so the screen stays empty after
switching to them: `cardEntities`, `cardThermo`, `cardMedia`, `cardAlarm`, `cardQR`, `cardPower`,
`cardChart`, `cardLChart`, `screensaver`, `screensaver2`, `screensaver3`. On each of them, in the
**Preinitialize Event**, paste at the **very beginning** (as in EU):

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

## E. AM/PM and long dates (#1485)

Page `screensaver`, handler `time`: after the block `if(tAMPM.txt=="") … else …` append:

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

(With AM/PM the time is left-aligned and does not run under AM/PM; on US portrait AM/PM is below the time.)

Handler `date`: after `tDate.txt=pageIcons.vaDate.txt` append:

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

(On US portrait a long date such as "Wednesday, 11 November 2026" gets the smaller 24 px font.)

## F. Status icons after a colour change (#1026)

Page `screensaver`, handler `color`: at the end of the block, right before its closing `}`, append:

```
ref tIcon1
ref tIcon2
```

## Afterwards

1. **Compile.** No errors; the size grows by about 0.2 MB (pictures) and stays below 16 MB.
2. **Debug.** Icon test from BUILD.en.md (step 5) and the picture test from section A.
3. **Export** the `.tft` (BUILD.en.md step 6), then `hmi_info.py --check <variant>`.
4. If the editor rejects an attribute assignment (e.g. `xcen` or `font` "cannot be changed at run
   time"), note the message and skip that one change. The other changes work independently.
