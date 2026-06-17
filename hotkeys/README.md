# hotkeys/ — AutoHotkey helpers for Piapro Studio

Two [AutoHotkey v2](https://www.autohotkey.com/) scripts that make the dated,
closed-source Piapro Studio nicer to use from FL Studio. They're independent —
run either or both.

| Script | What it adds |
|---|---|
| [`PiaproFLHotkeys.ahk`](PiaproFLHotkeys.ahk) | FL-style mouse-wheel **zoom** inside Piapro |
| [`PiaproPanel.ahk`](PiaproPanel.ahk) | a floating **Play/Stop** panel docked to the Piapro window (Phase 3) |

## PiaproFLHotkeys.ahk — zoom that matches FL Studio

This script makes Piapro Studio respond to FL Studio's zoom gestures. Because Piapro is closed-source and runs *inside* FL Studio, the script is **context-sensitive**: it only acts while a **Piapro Studio** window is focused, so FL Studio's own shortcuts are never affected.

## What it does

| You do (FL Studio style) | Piapro receives | Result | Status |
|---|---|---|---|
| **Ctrl + mouse wheel** | `Ctrl+Shift+wheel` (Piapro's native zoom) | Zoom **horizontally** (up = in, down = out) | ✅ Working |
| **Alt + mouse wheel** | `Ctrl+Shift+]` / `Ctrl+Shift+[` | Zoom **vertically** (up = in, down = out) | ✅ Working |

### Why the translation?
Piapro's *native* horizontal zoom is `Ctrl+Shift+wheel`; plain `Ctrl+wheel` does nothing. The script quietly converts your FL-style `Ctrl+wheel` into Piapro's `Ctrl+Shift+wheel`. AutoHotkey can't invent a zoom action — it can only send gestures Piapro already understands.

## Setup & use

1. Install AutoHotkey v2 (once): `winget install --id AutoHotkey.AutoHotkey`
2. **Double-click `PiaproFLHotkeys.ahk`.** A green **H** icon appears in the system tray and a tooltip confirms it loaded.
3. Focus Piapro Studio (inside FL Studio) and use **Ctrl + wheel** to zoom horizontally.

**Stop it:** right-click the tray **H** → *Exit*.
**After editing the script:** right-click the tray **H** → *Reload Script* (or just re-run the file).

### Run automatically at login (optional)
Press `Win+R`, type `shell:startup`, Enter, and drop a **shortcut** to `PiaproFLHotkeys.ahk` into that folder.

## Troubleshooting
- **Nothing happens:** make sure the tray **H** is present and that the Piapro editor window (not FL's main window) is focused.
- **Zoom direction feels inverted:** tell me and I'll swap `WheelUp`/`WheelDown` in the script.

---

## PiaproPanel.ahk — a floating Play/Stop panel (Phase 3)

Piapro is closed-source, so we can't restyle its real UI. Instead this draws a
small **always-on-top panel** that **docks to the Piapro window** (top-right) and
follows it around, giving big, clearly-labelled buttons for clunky actions. v1
has a **▶ Play / Stop** button. It only appears while **FL Studio is the
foreground app** (so it won't float over your other windows), and hides when
Piapro is closed or minimized.

### Setup & use
1. AutoHotkey v2 installed (same as above).
2. **Double-click `PiaproPanel.ahk`** (a tray icon + tooltip confirm it loaded).
   It can run alongside `PiaproFLHotkeys.ahk`.
3. Open Piapro inside FL Studio → the panel appears in Piapro's top-right corner.
   Click **▶ Play / Stop** to start/stop playback.

### The transport key (please confirm)
Clicking the button focuses Piapro and sends its play/stop key, set near the top
of the script:

```ahk
global TRANSPORT_KEY := "Space"   ; <- change this if Space doesn't toggle play
```

`Space` is the universal DAW play/stop and the best guess, but Piapro can't be
inspected from outside — **if the button does nothing or the wrong thing, tell me
which key Piapro uses for play/stop and I'll update this one line** (or split it
into separate Play and Stop keys). Same goes for where the panel sits — say the
word and I'll move it.

### Coming next
The script is built around a small action list, so more buttons are easy to add
once their Piapro keys/menus are confirmed: **Job ▸ Convert phonemes to match
language**, **Import/Export VSQx**, **reset/fit zoom**, etc.

**Stop it / edit it:** right-click the tray icon → *Exit* / *Reload Script*.
