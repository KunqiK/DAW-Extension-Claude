# Made by M. Y. — Lyric Tool 🎤

Put lyrics on a melody for **Piapro Studio** (VOCALOID). Two jobs:

1. **New lyrics on a melody** — load a MIDI from FL Studio, type one syllable per note, export a `.vsqx` Piapro can import.
2. **Re-word a tuned song** — open a `.vsqx` you already tuned in Piapro and put *new* words on it **without losing any of your tuning** (great for choruses that reuse the melody).

---

## Getting it running

### Easiest — the app (no Python needed)
1. Get the **`MadeByMY-LyricTool`** folder (to share it, zip the whole folder and send the zip; the recipient unzips it).
2. Open the folder and double-click **`MadeByMY-LyricTool.exe`** inside it. (Keep the exe together with its `_internal` folder — don't move the exe out on its own.)
   - Windows may show *"Windows protected your PC"* (the app isn't signed). Click **More info → Run anyway**. It's safe — a small homemade tool.
   - *(It's a one-folder build on purpose: a single-file .exe unpacks to a temp folder on launch and that can fail — "Failed to extract … return code -1" — when antivirus interferes. The folder build has no unpack step.)*

### From the source code (if you'd rather)
1. Install **Python 3** from python.org — tick **“Add Python to PATH”** during install.
2. Download the project folder.
3. Double-click **`midi2vsqx/Open Lyric Tool.bat`** — it finds your Python and installs the libraries the first time automatically.
   - Manual alternative: open a terminal in `midi2vsqx/` → `pip install -r requirements.txt` → `python app.py`.

---

## The 60-second tour

| Button | What it does |
|---|---|
| **Open MIDI** | Load a melody (MIDI from FL Studio). Each note becomes a row — type a syllable. |
| **Import VSQx** | Open a tuned `.vsqx` to **re-word it** (keeps your tuning). Pick a vocal line if there are several. |
| **Untuned ref** | *Optional.* Adds the pre-tuning ("untuned reference") file so syllable splits are exact (see note below). |
| **Batch lyrics** | Paste many syllables at once instead of typing one by one. |
| **Export VSQX** | Save the result. In Piapro: **File ▸ Import ▸ VSQX**, then **Job ▸ Convert phonemes to match language**. |
| **▶ Play / Out / Sound** | Hear it — through Windows, or routed to **FL Studio** (see Playback). |
| **? Help** | Opens the full in-app guide, including a **keyboard-shortcuts** list. |

### Layout
One window, side by side: the **piano-roll visualizer** fills the left, and the **lyric list** is a tall column on the right (type a syllable per row). The edit/zoom controls sit in a strip along the bottom.

The **piano-roll** shows your notes: **orange** = a syllable's start, **lavender** = a held/tuning note. Click a row (or a note) to find/select it. **Zoom** like FL Studio — **Zoom H −/＋** or **Ctrl + wheel** for time (horizontal), **V −/＋** or **Alt + wheel** for pitch (vertical). Plain wheel scrolls up/down, **Shift + wheel** sideways; a scrollbar appears when notes are taller than the view, and the roll grows when you enlarge the window.

### Editing a melody (Open MIDI mode)
Right on the piano-roll you can: **drag** a note to move/re-pitch it · drag its **right edge** to resize · **double-click empty space** to add a note · select a row and press **Delete** to remove · **Transpose all** with −8va/−1/+1/+8va (or Shift+↑/↓, Ctrl+↑/↓). Made a mistake? **Undo/Redo** with Ctrl+Z / Ctrl+Y. *(Editing is off when re-wording a tuned file, so your Piapro tuning is never altered — there, clicking a note just highlights its syllable.)*

A live **“X / N lyrics”** counter (top-right) turns green once every note has a word, and notes still missing one are tinted in the table — so you can see at a glance what's left. The app also **remembers** your font, instrument, MIDI output and window size between runs.

---

## Workflow A — new lyrics
**Open MIDI** → type one syllable per note (Enter = next) → **Export VSQX** → import in Piapro → run the phoneme Job.

## Workflow B — re-word a tuned song (keep tuning)
**Import VSQx** → pick the vocal line → type the new words over each syllable → **Export VSQX** → import in Piapro → run the phoneme Job. Your pitches and note-splits are preserved; only the words change.

> **Splits & syllable counts:** the tool groups each tuned syllable for you. If a held vowel sits next to a real vowel syllable it can be ambiguous — then also use **Import Untuned Reference VSQx** (the pre-tuning version). The tuned and un-tuned versions must have the **same number of syllables**, or the tool will warn you.

## Playback → hear it in FL Studio
Quick: set **Out = Microsoft GS Wavetable Synth**, pick a **Sound**, press **▶ Play**. Click a row/note first to play from there (like dropping a playhead); the top row plays from the start.
With your FL instrument: install **loopMIDI**, create a port, enable it as a MIDI input in FL (**Options ▸ MIDI Settings**), select your instrument's channel, then set **Out** to that port here. Full step-by-step is under **? Help → 5 · Play it back**.

---

*Questions? Everything here is also inside the app under **? Help**.*
