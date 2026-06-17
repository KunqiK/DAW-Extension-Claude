# hotkeys/ — Piapro Studio zoom that matches FL Studio

[`PiaproFLHotkeys.ahk`](PiaproFLHotkeys.ahk) is an [AutoHotkey v2](https://www.autohotkey.com/) script that makes Piapro Studio respond to FL Studio's zoom gestures. Because Piapro is closed-source and runs *inside* FL Studio, the script is **context-sensitive**: it only acts while a **Piapro Studio** window is focused, so FL Studio's own shortcuts are never affected.

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
