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
  - ✅ **MILESTONE 1b — bare-vowel tuning tails handled.** User reported a 2nd tuning style: tails aren't always `ー` — they can be the **bare vowel** (kana あいうえお or romaji a/i/u/e/o). e.g. `tuned_complex.vsqx` = `ke e e e e` (each tail lyric/phoneme `e`). Old code saw 5 moras; and re-lyric to `ra` would've needed the user to hand-edit every `e`→`a`.
    - Fix (`vsqx_reader.py`): `is_continuation()` now treats `ー` **or a bare vowel** as a tail; `group_moras`/`count_moras` updated (first note is always a lead). `relyric_vsqx` now **propagates the new syllable's vowel to bare-vowel tails** (ke→ra rewrites its `e` tails to `a`), keeping `ー` tails as `ー`; output vowel matches the new syllable's script (kana vs romaji). Added `vowel_of()` + a kana→vowel table.
    - **Tested (scratch/test_relyric.py):** `tuned.vsqx` ら→け (ー tails kept) ✓; `tuned_complex.vsqx` ke,e,e,e,e → `ra,a,a,a,a` (romaji) ✓ and → `ら,あ,あ,あ,あ` (kana) ✓; tuning preserved in all. **Known simplification:** all bare-vowel tails take the new mora's vowel (fine for melisma; deliberate vowel changes mid-mora would be flattened).
    - ⚠️ A running app instance has the OLD module — **restart the app** (close + relaunch via `Open Lyric Tool.bat`) to get this fix.
  - 📥 **Multi-track sample received:** `samples/multi_track.vsqx` = 3 tracks (Copy Harm 1 / Harm 1 / Keyzone Classic 1) + an extra "no tuning" part. Confirms the need for clip/track selection.
  - ✅ **MILESTONE 1c — baseline disambiguation BUILT.** Ambiguity: a tuned `ke e e e e` is byte-identical whether it's one "ke" melisma OR "ke" melisma + a real "e" syllable; the tuned file alone can't tell (same `<y>`/`<p>`). **User chose the un-tuned-baseline approach.**
    - `vsqx_reader.py` refactor: `plan_relyric(notes, new_lyrics, baseline_starts=None)` decides each note's new lyric (None = unchanged). With `baseline_starts` (sorted song-relative starts of the un-tuned moras) it maps tuned notes to moras **by time-span** (`_mora_index_by_baseline`); else falls back to the `ー`/bare-vowel heuristic. `relyric_vsqx(..., baseline_path=None)` reads the baseline file and routes through `plan_relyric`. Both modes apply via the same surgical, document-order text rewrite (plan index ↔ note-block index).
    - `app.py`: new **"+ un-tuned (exact splits)…"** button → loads the un-tuned file, table becomes one row per ORIGINAL syllable; export passes `baseline_path`.
    - **Tested:** no baseline → `ke,e,e,e,e`→`ra,a,a,a,a` (1 mora); 2-mora baseline → `ra,a,a,a,e` (trailing `e` kept); real `untuned↔tuned` pair OK. Compiles; GUI constructs.
  - ✅ **MILESTONE 2 — TRACK/CLIP PICKER BUILT.** A vsqx can hold several vocal lines (`multi_track.vsqx` = 4 clips: Copy Harm 1/harm down, Harm 1/Keyzone Classic 1, Keyzone Classic 1/LEAD, Keyzone Classic 1/no tuning).
    - `vsqx_reader.py`: `Clip` dataclass + `read_clips()` (one entry per `vsPart`, with track/part names, doc-order index, notes); `moras_of(notes)` extracted from `group_moras`; `relyric_clip(in, clip_index, new_lyrics, out, baseline_starts)` rewrites **only the chosen `vsPart`** (via `_VSPART_BLOCK` slice), leaving all other lines byte-identical; whole file written back (re-import drops in just that corrected line).
    - `app.py`: opening a multi-line file pops a **`_choose_clip` picker** (Listbox by "Track — part, N notes/M syllables"); 1-clip files skip it. `+ un-tuned` now matches the baseline's SAME line by track/part name (index fallback). Export → `relyric_clip` with the chosen clip + optional `baseline_starts`. New `_show_clip` helper renders a clip as moras (tuned) or per-note (baseline).
    - **Tested (scratch/test_relyric.py [5]):** re-lyric clip 2 (LEAD) of `multi_track.vsqx` → clips 0/1/3 byte-identical, clip 2 pitches/counts preserved, first syllable changed. Compiles; GUI constructs; clip path exercised headlessly.
    - **Decision:** output keeps the WHOLE file with only the chosen line changed (simplest + always valid). If Piapro's VSQX import duplicates the unchanged lines on re-import, revisit single-line export.
  - ✅ **REAL-WORLD CONFIRMED (user):** re-lyric round-trip works in Piapro (import + phoneme Job → new words sing, tuning kept). Foundation validated.
  - ✅ **MILESTONE 3 — piano-roll visualizer + Ina theme + baseline picker.**
    - **Baseline picker:** `_choose_clip` gained `preselect`/`prompt`/`ok_text`; `open_baseline` now offers a picker over the un-tuned file's lines (defaulting to the name-matched one) instead of silent auto-match — per user request to choose the track there too.
    - **Piano-roll visualizer** (`app.py`): a `tk.Canvas` above the table draws the loaded notes on a time×pitch grid — lead notes ORANGE, `ー`/vowel tails LILAC, lyric labels on leads, bar gridlines, h-scroll, left-edge offset to the first bar. Selecting a table row highlights that syllable's notes (PAPER) and scrolls to it. For a tuned clip the table shows moras (58) while the roll shows ALL notes (149) → the tuning splits are visible. `draw_notes` fed by `open_midi` (MIDI notes) and `_show_clip` (raw clip notes).
    - **Ina'nis theme** (`_apply_theme`, ttk 'clam'): palette INK `#000000`, ABYSS `#1b1822` (derived), PLUM `#575068`, PURPLE `#62567E`, LILAC `#9575E2`, ORANGE `#f29a30` accent, PAPER `#e1d8ef` text. Themed buttons/labels/Treeview/scrollbars/status + the inline Entry editor + the picker Listbox.
    - **Tested:** compiles; headless construct + draw for MIDI (7 notes) and the LEAD clip (149 notes / 58 rows) + selection highlight all run clean. Launched for the user to view.
  - ✅ **COMMIT #1 pushed** (`6bd866c..cd53f61`): re-lyric engine, GUI pickers, piano-roll, theme, samples, launcher, docs.
  - ✅ **MILESTONE 4 — playback + batch lyrics + in-app help + mismatch warning + UI polish.**
    - **Playback** (`mido` + **python-rtmidi** backend, added to requirements): `▶ Play`/`■ Stop`, an **Out** port combo (Windows exposes *Microsoft GS Wavetable Synth*; a **loopMIDI** port → FL appears here once installed), and a **Sound** combo (14 GM instruments). Plays `draw_notes` in a daemon thread timed by `60/(bpm·480)` s/tick; CC123 all-off + restore button in `finally`; `_on_close` stops the thread. Verified the GS port opens/closes.
    - **Batch lyrics** (`batch_lyrics`): paste space/newline-separated syllables to fill the table at once; optional **auto-split kana** via `split_kana_moras` (きらきら→き ら き ら, きゃ stays one); warns on count≠notes.
    - **In-app Help** (`_show_help`): scrollable guide covering all five workflows + the piano-roll colour key. Plus a small on-roll legend (orange=syllable, lavender=held).
    - **Syllable-mismatch safeguard** (`unmapped_moras`): when an un-tuned baseline is loaded, export warns if N baseline syllables get no tuned notes (counts don't match). Answers user Q: **yes, tuned & un-tuned must have equal syllable counts.**
    - **UI polish:** bigger fonts (Segoe UI 10 / Bahnschrift title / Consolas mono), INK header bar with title + orange accent rule, themed Combobox/Checkbutton, window 1000×680. Baseline mode keeps the roll showing the TUNED notes (table = un-tuned syllables) via `_show_clip(..., draw=self.clip.notes)`.
    - **Tested:** all modules compile; headless build + load (MIDI + clip) + kana split + unmapped detection + GS port open/close all pass. Launched for user.
  - ✅ **COMMIT #2 pushed** (`cd53f61..eea06f9`): playback, batch lyrics, help, mismatch guard, UI polish.
  - ✅ **MILESTONE 5 — note editing + font picker + Help readability + relabels.**
    - **Light note editing (MIDI mode only)** (`app.py`): drag a piano-roll note to move/re-pitch, drag its right edge to resize (1/16 = 120-tick snap), select a row + Delete to remove. `_hit_note`/`_roll_press`/`_roll_drag`/`_roll_release`/`_delete_note`, gated by `_editable()` (export_mode=="midi"); `_draw_piano_roll` stores `_pad/_row_h/_kmax`. Re-lyric mode stays read-only so Piapro tuning is never altered. Edits flow into `self.song.notes` → table + export.
    - **Live font picker** (user request): `FONT_THEMES` (Segoe/Bahnschrift/Consolas/Verdana/Yu Gothic); header Combobox → `_set_font_theme` rebuilds `self.fonts` and re-runs `_apply_theme` + redraw. All widgets/dialogs/canvas now read `self.fonts`.
    - **Help readability:** `_show_help` Text now uses paragraph spacing (tag `spacing1/3`, `lmargin`, body `spacing2`) so sections breathe; matches chosen font.
    - **Relabels (user):** title → **"Made by M. Y."** (window + header); buttons → "Open MIDI (Ctrl+O)", **"Import VSQx (Ctrl+R)"**, **"Import Untuned Reference VSQx"**, "Batch lyrics", "Export VSQX (Ctrl+S)" — all "…" removed. Info moved to the playback bar (right).
    - 🐞 **Gotcha logged:** a Write hit an `fsync` error and silently dropped the `__init__` font/edit-state lines while later edits referenced them → `AttributeError: no attribute 'fonts'` at construct. Re-added the state; **after an fsync error, re-Read the file before trusting it.**
    - **Tested:** compiles; headless build + font switch (Bahnschrift/Consolas) + MIDI load + hit-test ('move') + delete (7→6) + 28 help lines all pass. Launched for user.
    - ✅ **User confirmed:** UI looks good; re-lyric round-trip works in Piapro.
  - **→ COMMIT #3 incoming** (this milestone).
  - **Possible next:** click-a-note-to-select on the roll; add-note; remember last MIDI port; per-syllable vowel control for tails.
