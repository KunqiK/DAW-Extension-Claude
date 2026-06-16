# CLAUDE.md — DAW Extension (Claude)

> Running development log + project memory. Updated each working session.
> (Also auto-loaded by Claude Code as project context.)

## Project overview

A personal toolkit to make **Piapro Studio** (Crypton VOCALOID editor, runs as a VSTi inside FL Studio) pleasant to use alongside **FL Studio** on Windows. Three goals, in priority order:

1. **Hotkeys** — make Piapro's zoom (and later other) hotkeys match FL Studio.
2. **Lyrics → VSQx converter** — a small Python desktop app: load an FL Studio MIDI export, type one syllable per note, export a Piapro-ready `.vsqx`.
3. **UI improvement** — explore making Piapro's dated UI friendlier (feasibility-limited; see Phase 3).

## Environment (verified 2026-06-15)

- **Piapro Studio VSTi x64 v2.0.4.1** — closed-source. Plugin DLL: `C:\Program Files\VstPlugins\Piapro Studio VSTi.dll`; engine: `C:\Program Files\Crypton\Piapro Studio VSTi x64\` (`PPS.dll`, `VsqDatabase.dll`); settings: `%APPDATA%\Crypton`. Imports **VSQx and MIDI**. Edition: **Piapro Studio for Hatsune Miku V4X** (bundled) — *not* NT.
- **FL Studio 2025 (25.2.5)** primary; 21 and 20 also installed.
- **Git 2.54**, **Python 3.9.6**, **GitHub CLI 2.94.0**, **AutoHotkey v2.0.26** installed. (Node.js not needed.)

**Tool paths** (per-user installs aren't always on the shell PATH — use full paths):
- gh: `C:\Program Files\GitHub CLI\gh.exe`
- AutoHotkey64: `%LOCALAPPDATA%\Programs\AutoHotkey\v2\AutoHotkey64.exe`
- Window Spy: `%LOCALAPPDATA%\Programs\AutoHotkey\UX\WindowSpy.ahk`
- Piapro VST DLL: `C:\Program Files\VstPlugins\Piapro Studio VSTi.dll`
- **FL zoom shortcuts (target):** Piano Roll & Playlist `PgUp`/`PgDn` = zoom in/out (horizontal). No FL default for vertical zoom.

## Decisions

- **Converter scope:** lyrics-focused (reuse FL Studio for note entry).
- **Converter tech:** Python desktop app (Tkinter). *Not* a real VST plugin.
- **Hotkeys tool:** AutoHotkey v2, context-sensitive to the Piapro window so FL Studio's own keys are untouched.
- **Zoom gestures (revised):** replicate FL's *mouse-wheel* zoom inside Piapro — **Ctrl+wheel = horizontal**, **Alt+wheel = vertical** (up = in). User zooms with the wheel, not `PgUp`/`PgDn`.
- **GitHub:** gh CLI + browser login; public repo `DAW-Extension-Claude`.
- **Reporting:** mirror outcomes to the Notion "DAW Extension Claude" page using toggle blocks; keep this log current each exchange.

## How to run

- **Hotkeys:** double-click `hotkeys/PiaproFLHotkeys.ahk` (needs AutoHotkey v2). In Piapro: `Ctrl+wheel` = horizontal zoom ✅; `Alt+wheel` = vertical (under test).
- **Converter:** `pip install -r midi2vsqx/requirements.txt`, then `python midi2vsqx/app.py`. Open MIDI → type lyrics → Export VSQX → Piapro **File ▸ Import ▸ VSQX**. Demo files: `python midi2vsqx/samples/make_twinkle.py`.

## Open questions / TODO

- [x] Identify the Piapro window — title `Piapro Studio`, host `FL64` (see `docs/research/piapro-window-and-zoom.md`).
- [x] Piapro native zoom: `Ctrl+Shift+wheel` = horizontal zoom; vertical-zoom trigger still unknown.
- [x] Piapro vertical zoom = `Ctrl+Shift+]`/`[` → mapped FL Alt+wheel to it (v0.2).
- [ ] Export a reference `.vsqx` from Piapro to use as the schema ground truth.
- [ ] Confirm lyric language (Japanese kana vs romaji) for the converter's defaults.
- [ ] Verify Piapro imports our generated `.vsqx` (notes + lyrics) — try `midi2vsqx/samples/twinkle.vsqx`.
- [ ] Verify whether Piapro accepts AHK-synthetic `Ctrl+Shift+]`/`[` (F8/F9 test) for vertical zoom.

## Session log

### 2026-06-15 — Session 1: Planning & scaffold
- Gathered requirements. User is an intro-level programmer on Windows; composes with FL Studio + Piapro Studio.
- Verified environment (see above): found Piapro Studio VSTi v2.0.4.1 and FL Studio 2025/21/20; Git + Python present; gh/AHK absent.
- Researched: FL zoom shortcuts (`PgUp`/`PgDn` horizontal), Piapro imports VSQx+MIDI, converter approach, and [UtaFormatix3](https://github.com/sdercolin/utaformatix3) as a format reference.
- Locked decisions (see Decisions) via a short Q&A.
- Wrote the approved plan; created repo scaffold (`README.md`, `.gitignore`, this log, `hotkeys/`, `midi2vsqx/`, `docs/research/`).
- Initialized git on `main`; first commit `2f1fe83` (6 files).
- Installed **GitHub CLI 2.94.0** and **AutoHotkey v2.0.26** (winget). gh not yet on this shell's PATH — using full path until Claude Code restarts.
- Set up the Notion **Development Log** with toggle blocks (Session 1 logged).
- ✅ **GitHub:** authenticated as KunqiK; created + pushed public repo **https://github.com/KunqiK/DAW-Extension-Claude**.

#### Phase 1 progress (hotkeys)
- 🔎 **Reframe:** user zooms in FL via **mouse-wheel gestures** (Ctrl+wheel = horizontal, Alt+wheel = vertical, up = in) — not keys. Goal: replicate those gestures in Piapro.
- ✅ **Piapro window identified** via Win32 enumeration: GUI titled `Piapro Studio` (volatile `Afx:` class → match by title), hosted in `FL64`. AHK target: `SetTitleMatchMode(2)` + `WinActive("Piapro Studio")`.
- ✅ **Piapro native zoom learned:** plain wheel = V-scroll, Shift+wheel = H-scroll, **Ctrl+Shift+wheel = H-zoom** (up=in); Ctrl+wheel & Alt+wheel = nothing. Vertical-zoom trigger not found yet.
- ✅ **Shipped `hotkeys/PiaproFLHotkeys.ahk` v0.1:** in Piapro, **Ctrl+wheel → Ctrl+Shift+wheel** (horizontal zoom, FL parity), scoped to `WinActive("Piapro Studio")` via `{Blind}`.
- ✅ **Horizontal zoom confirmed working** by user. **Vertical zoom found:** Piapro `Ctrl+Shift+]`/`[` (keyboard) + a +/− button bottom-right.
- ✅ **v0.2:** mapped FL **Alt+wheel → `Ctrl+Shift+]`/`[`** (vertical zoom).
- 🐞 **Vertical zoom debugging:** diagnostic (scan-code brackets + tooltip) showed **tooltip fires but no zoom** → the hotkey works, but Piapro rejects the keystroke. Root cause: the held **Alt taints the combo** (Piapro saw Ctrl+Shift+Alt+]; AHK does *not* auto-release Alt for *wheel* hotkeys).
- 🔧 **SendEvent attempt → wrong result:** Alt+wheel zoomed *horizontally* — a physical scroll notch leaked mid-send while Ctrl+Shift were held (= stray Ctrl+Shift+wheel).
- 🔧 **Now under test (commit 3c5340d):** atomic `Send("{Alt up}^+{bracket}{Alt down}")` (SendInput, uninterruptible) + **F8/F9** keys that send a clean `Ctrl+Shift+]`/`[` (no Alt/wheel) to isolate whether Piapro accepts the synthetic keystroke. **→ User testing F8/F9 + Alt+wheel.**

#### Phase 2 progress (converter) — built while user away
- ✅ **Researched VSQ4** against UtaFormatix3's template + writer (in `scratch/`). Tags: `t/dur/n/v/y/p`; resolution 480; tempo×100; part at preMeasure; note `<t>` song-relative; phoneme left unlocked so Piapro re-derives.
- ✅ **Built + tested core** (`midi2vsqx/midi_reader.py` via `mido`; `vsqx_writer.py`). Sample Twinkle MIDI → valid `vsq4`, 7 notes, correct ticks/tempo; XML well-formed.
- ✅ **Built GUI** (`app.py`, Tkinter): load MIDI → note table → fast lyric entry (Enter = next) → Export VSQX. Compiles + constructs OK.
- ✅ **Sample committed:** `midi2vsqx/samples/twinkle.{mid,vsqx}` + `make_twinkle.py`. `mido` installed (user site).
- ⏳ **Pending user test:** does Piapro import the `.vsqx` (notes + lyrics)? Quick check: import `samples/twinkle.vsqx`.
