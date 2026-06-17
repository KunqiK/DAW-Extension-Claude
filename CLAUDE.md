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
- [ ] **🚩 Does Piapro Studio EXPORT `.vsqx`?** (File ▸ Export) — gates the "re-lyric while preserving tuning" feature, which needs tuned notes back out as a readable file. Also: get untuned+tuned `.vsqx` samples from Piapro as schema ground truth (→ build the VSQX reader against real data).
- [x] Build a **VSQX reader** (`vsqx_reader.py`) — done; reused by re-lyric (built ✅), and will back the visualizer/playback/editing.
- [x] **Re-lyric while preserving tuning** — built + tested (surgical `<y>` rewrite). → pending user test in Piapro.
- [ ] Converter v2 next: **piano-roll visualizer**, then **playback routed to FL** (loopMIDI), then **light editing**.
- [ ] Confirm lyric language (Japanese kana vs romaji) for the converter's defaults.
- [ ] Verify Piapro imports our generated `.vsqx` (notes + lyrics) — try `midi2vsqx/samples/twinkle.vsqx`.
- [x] Vertical zoom **SOLVED:** root cause was *timing*, not key encoding. The default `Send`/`SendInput` batches Ctrl+Shift+bracket in one instant — too fast for Piapro to register. F11 (`SendEvent` + 60 ms key delay) worked (confirmed by user). v0.4 locks this in for Alt+wheel and guards against the old mid-send wheel leak (`*Wheel::return` while `g_VZooming`).
- [ ] Converter sample: lyrics must be **one kana (mora) per note** — fixed `make_twinkle.py` to き-ら-き-ら-ひ-か-る (was 2 kana/note).

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

### 2026-06-16 — Session 2: Hotkey diagnostic v0.3 + converter fixes
#### Phase 1 (hotkeys)
- 🐞 **User result:** F8/F9 (clean synthetic `Ctrl+Shift+]`/`[`, no Alt/wheel) did **nothing** — not even a partial zoom.
- 🔑 **Key inference:** Piapro accepts synthetic *wheel* events (H-zoom via `Ctrl+Shift+wheel` works) but rejects our synthetic *bracket keystroke*. Likely cause = the send method: scan-code `{sc01B}` is keyboard-layout-dependent (user types JP kana → may not be a US layout), or timing.
- 🔧 **Shipped v0.3** (`hotkeys/PiaproFLHotkeys.ahk`, validated load-clean via `/ErrorStdOut`): horizontal zoom unchanged; **F8–F11 now test 4 send methods** for `Ctrl+Shift+]` — F8 char `^+]`, F9 virtual-key `^+{vkDD}`, F10 scan-code `^+{sc01B}`, F11 slow `SendEvent` (60 ms key delay). Each shows a tooltip naming the method. Alt+wheel temporarily uses the F8 "char" method (`{Alt up}^+]`).
- ✅ **RESULT (user):** **F11 zoomed vertically** — the others did nothing. So the blocker was *timing*: `SendInput` (default `Send`) batches Ctrl+Shift+bracket too fast for Piapro; `SendEvent` with a 60 ms key delay (paced like typing) registers. Not a layout/encoding issue.
- 🔧 **Shipped v0.4** (validated load-clean): Alt+wheel now `Critical` + `{Alt up}` + `SendEvent("^+]"/"^+[")` at `SetKeyDelay(60,30)`, restored in a `finally`. Removed the F8–F11 diagnostics. Added a leak guard — while `g_VZooming`, `*WheelUp/Down::return` so a stray physical notch can't escape as `Ctrl+Shift+wheel` (the old horizontal-leak bug).
- 🐞 **v0.4 bug (user):** Alt+wheel zoomed only **once per Alt press** — couldn't hold-and-scroll like horizontal. Cause: the `{Alt up}` we send to clean the combo also desyncs AHK's Alt state, so `!WheelUp` stops matching until Alt is physically re-pressed.
- 🔧 **Shipped v0.5** (validated load-clean): in the `finally`, re-press Alt with `Send("{Alt down}")` **only if still physically held** (`GetKeyState("Alt","P")`) → AHK stays in sync, continuous hold-and-scroll works, no stuck-Alt if released mid-send. Exposed `g_ZoomDelay`/`g_ZoomPress` (default 60/30 ms) as a user-tunable speed knob. **→ User testing continuous vertical zoom.**
#### Phase 2 (converter)
- 🐞 **Fixed sample lyrics:** `make_twinkle.py` used 2 kana/note (`きら/きら/ひか/…`). VOCALOID wants **one mora per note** → now き-ら-き-ら-ひ-か-る (7 morae = the 7 notes of "きらきら星"). Regenerated `samples/twinkle.vsqx` (verified: 7 single-kana `<y>` tags). The converter code was never at fault — it stores exactly the one string typed per note.
- 📋 **Documented how to run the converter** for the user (open MIDI → one syllable/note, Enter = next → Export VSQX → Piapro File ▸ Import ▸ VSQX).
- ✅ **Converter setup confirmed:** ran `pip install -r requirements.txt` → `mido 1.3.3` already present. User tried the app, likes it.
- 💡 **Converter v2 wishlist (user):** (1) **piano-roll visualizer** (show timing + note length, not a table); (2) **instant playback** with an instrument of choice — user suggested it be *built into FL* to borrow FL instruments; (3) **real-time MIDI editing**.
  - **Reality check given to user:** "built into FL" isn't feasible for a Python app (would need a full VST in C++/JUCE — explicitly rejected; FL scripting only covers MIDI control surfaces, not custom editor UIs). The *goal* (hear notes with a good instrument) is reachable two other ways: **(A)** built-in playback via Windows General-MIDI synth (pick instrument; zero setup), or **(B)** route MIDI to FL via a virtual cable (loopMIDI) for the real FL sound (one-time setup, FL running). Visualizer + light editing fit the Tkinter app fine; full real-time editing overlaps with FL (the original premise was "enter notes in FL, add lyrics here").
  - ✅ **User picked:** all three (visualizer + playback + editing), playback **routed to FL** (virtual MIDI cable / loopMIDI).
- ⭐ **NEW killer feature (user) — "re-lyric while preserving tuning":** Workflow today is painful: import lyrics (1 mora/note) → tune in Piapro (each mora gets split into several short notes at different pitches, all sharing the mora's lyric) → to reuse the same melody+tuning with **new** lyrics (e.g. a chorus), the user must restart from the untuned version and re-tune everything. **Desired:** the tool saves a baseline (mora→note layout) at export; user re-imports the **tuned** `.vsqx`; tool diffs vs baseline and, when new lyrics are entered, propagates each new mora to **all** sub-notes within the original note's span (e.g. "wa" split into 3 notes → new lyric "ke" applied to all 3). This is the project's highest-value idea (kills repeated re-tuning).
  - ✅ **BLOCKER CLEARED:** Piapro Studio **does export `.vsqx`**. User provided `samples/untuned.vsqx` + `samples/tuned.vsqx` (same phrase) — committed `5cf4ef6`.
  - 🔑 **Key discovery from the real tuned file — Piapro tuning model:** splitting a mora for tuning produces **one lead note that keeps the lyric + phoneme** (e.g. `ら` / `4 a`) followed by **`ー` continuation notes** (phoneme `-`, the "hold this vowel" mark). Example: untuned `ら` (dur 960) → tuned 5 notes `[ら, ー, ー, ー, ー]` over the same 960 ticks at different pitches. The user's mental model ("all 3 notes say wa") is slightly off — only the lead carries the syllable; the `ー` notes prolong its vowel.
  - 🎯 **Re-lyric design (simplified by the above):** change **only the lead note's** `<y>` (and `<p>`) per mora; leave `ー` notes untouched → the held vowel follows automatically and ALL tuning (pitch/dur/splits) is preserved. **Baseline copy not strictly needed** — every non-`ー` note in the tuned file = one mora, in time order; map new moras 1:1 (warn on count mismatch). Use untuned file only as a sanity check / to show originals.
  - 🧩 **Reader must handle real Piapro schema (differs from our writer):** `version 3.0.0.11`; `vVoice` has `id2`/`vPrm2`; **multiple** `<timeSig>`/`<tempo>` entries; a `<cc>` element before notes; real `<p>` phonemes present; note `<t>` is **relative to `vsPart` `<t>`** (abs = part.t + note.t); default XML namespace (`vsq4`) — parse namespace-aware. Likely need a small **hiragana→VOCALOID phoneme** map (or set `<y>` and tell user to run Piapro's "Convert phonemes to match language" Job).
  - **Recommended build order:** (1) re-lyric/tuning-preserving re-import → (2) piano-roll visualizer → (3) playback routed to FL (loopMIDI) → (4) light editing.
  - ✅ **MILESTONE 1 BUILT + TESTED — re-lyric round-trip works.**
    - New `midi2vsqx/vsqx_reader.py`: `read_vsqx()` (namespace-aware; handles real Piapro schema), `group_moras()` (collapses lead + `ー` notes into one mora), `relyric_vsqx()` (**surgical text replacement** of only the lead notes' `<y>` — preserves CDATA + all tuning byte-for-byte; unlocks `<p>` so VOCALOID re-derives). Extended `midi_reader` model: `Note.phoneme`, `Song.pre_measure`.
    - `app.py`: added **"Re-lyric tuned VSQX… (Ctrl+R)"** — loads a tuned file as one row per mora, type new lyrics, Export writes a tuned `.vsqx` with tuning intact (then user runs Piapro's phoneme Job).
    - **Test (scratch/test_relyric.py, gitignored):** `tuned.vsqx` ら→け changed **exactly 1 line** (`<y>`); 5 notes, pitches `[71,70,72,72,77]`, durs `[60,60,720,60,60]`, and the four `ー` all preserved. All modules compile; GUI constructs headlessly.
    - **→ User to test in Piapro:** Re-lyric `samples/tuned.vsqx` (e.g. ら→け), import the result, run Job ▸ Convert phonemes to match language, confirm tuning is kept.
    - **Next:** (2) piano-roll visualizer.
