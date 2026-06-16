# Research: Piapro Studio window + zoom (Phase 1)

## How Piapro runs
Piapro Studio VSTi is hosted inside **FL Studio** (process `FL64.exe`, FL Studio 2025).

Windows observed (Piapro open in FL Studio, 2026-06):
- **GUI window — the one we target.** Title: `Piapro Studio`. Class: `Afx:<hex>:b:...` ⚠️ the hex is a module address that **changes every launch**, so never match on the class — match on the **title**.
- FL's plugin wrapper (child of FL): class `TPluginForm`, title `Piapro Studio VSTi (Master)`; inside it `TVSTPanel` and `TNewCaption`.

## AutoHotkey targeting
Scope the remaps to the Piapro context by title substring:

```ahk
SetTitleMatchMode(2)            ; substring match
#HotIf WinActive("Piapro Studio")
    ; ... remaps here ...
#HotIf
```

This matches both `Piapro Studio` (GUI) and `Piapro Studio VSTi (Master)` (wrapper) but **not** FL Studio's main window (`FL Studio 2025`). Remaps fire only while Piapro is focused.

## Goal (FL Studio parity)
Replicate the FL Studio mouse-wheel zoom gestures inside Piapro:
- **Ctrl + mouse wheel** → zoom **horizontal** (scroll up = in, down = out)
- **Alt + mouse wheel** → zoom **vertical** (scroll up = in, down = out)

## Edition
**Piapro Studio for Hatsune Miku V4X** (bundled with the Miku V4 voicebank) — *not* the newer NT. Imports VSQx (relevant to Phase 2).

## Native zoom / scroll mechanism (confirmed by user)
In the VOCALOID piano window:

| Gesture | Piapro behavior |
|---|---|
| Plain wheel | Scroll vertically |
| Shift + wheel | Scroll horizontally |
| Ctrl + wheel | (nothing) |
| Alt + wheel | (nothing) |
| **Ctrl + Shift + wheel** | **Zoom horizontally** (up = in, down = out) |

- **Horizontal zoom trigger = `Ctrl+Shift+wheel`.**
- **Vertical zoom trigger = `Ctrl+Shift+]` (in) / `Ctrl+Shift+[` (out)** — keyboard; also a +/− control at the bottom-right. Wheel combos (Ctrl+Alt, Alt+Shift, Ctrl+Alt+Shift) do nothing.

## Mapping (FL parity)
- FL `Ctrl+wheel` (horizontal) → send **`Ctrl+Shift+wheel`** to Piapro. ✅ implemented in `hotkeys/PiaproFLHotkeys.ahk` (uses `{Blind}` to keep Ctrl held and add Shift).
- FL `Alt+wheel` (vertical) → send **`Ctrl+Shift+]` / `Ctrl+Shift+[`** to Piapro. ✅ implemented (no `{Blind}`, so the held Alt is dropped).
