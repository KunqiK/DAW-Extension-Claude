# Made by M. Y. — Lyric Tool 🎤

Put lyrics on a melody for **Piapro Studio** (VOCALOID). Two jobs:

1. **New lyrics on a melody** — load a MIDI from FL Studio, type one syllable per note, export a `.vsqx` Piapro can import.
2. **Re-word a tuned song** — open a `.vsqx` you already tuned in Piapro and put *new* words on it **without losing any of your tuning** (great for choruses that reuse the melody).

---

## Getting it running

### Easiest — the app (no Python needed)
1. Get **`MadeByMY-LyricTool.exe`** (one file).
2. Double-click it.
   - Windows may show *"Windows protected your PC"* (because the app isn't signed). Click **More info → Run anyway**. It's safe — it's just a small homemade tool.

### From the source code (if you'd rather)
1. Install **Python 3.9+** from python.org — tick **“Add Python to PATH”** during install.
2. Download the project folder.
3. Double-click **`midi2vsqx/Open Lyric Tool.bat`** (first run installs the one library it needs).
   - Manual alternative: open a terminal in `midi2vsqx/` → `pip install -r requirements.txt` → `python app.py`.

---

## The 60-second tour

| Button | What it does |
|---|---|
| **Open MIDI** | Load a melody (MIDI from FL Studio). Each note becomes a row — type a syllable. |
| **Import VSQx** | Open a tuned `.vsqx` to **re-word it** (keeps your tuning). Pick a vocal line if there are several. |
| **Import Untuned Reference VSQx** | *Optional.* Adds the pre-tuning file so syllable splits are exact (see note below). |
| **Batch lyrics** | Paste many syllables at once instead of typing one by one. |
| **Export VSQX** | Save the result. In Piapro: **File ▸ Import ▸ VSQX**, then **Job ▸ Convert phonemes to match language**. |
| **▶ Play / Out / Sound** | Hear it — through Windows, or routed to **FL Studio** (see Playback). |
| **Font** | Change the look. **? Help** opens the full in-app guide. |

The **piano-roll** strip shows your notes: **orange** = a syllable's start, **lavender** = a held/tuning note. Click a row to find it. In *Open MIDI* mode you can **drag notes** to move/re-pitch, drag a right edge to resize, and **Delete** to remove.

---

## Workflow A — new lyrics
**Open MIDI** → type one syllable per note (Enter = next) → **Export VSQX** → import in Piapro → run the phoneme Job.

## Workflow B — re-word a tuned song (keep tuning)
**Import VSQx** → pick the vocal line → type the new words over each syllable → **Export VSQX** → import in Piapro → run the phoneme Job. Your pitches and note-splits are preserved; only the words change.

> **Splits & syllable counts:** the tool groups each tuned syllable for you. If a held vowel sits next to a real vowel syllable it can be ambiguous — then also use **Import Untuned Reference VSQx** (the pre-tuning version). The tuned and un-tuned versions must have the **same number of syllables**, or the tool will warn you.

## Playback → hear it in FL Studio
Quick: set **Out = Microsoft GS Wavetable Synth**, pick a **Sound**, press **▶ Play**.
With your FL instrument: install **loopMIDI**, create a port, enable it as a MIDI input in FL (**Options ▸ MIDI Settings**), select your instrument's channel, then set **Out** to that port here. Full step-by-step is under **? Help → 5 · Play it back**.

---

*Questions? Everything here is also inside the app under **? Help**.*
