# midi2vsqx — Lyrics → VSQX converter

A small Python desktop app: load a MIDI file exported from FL Studio, type one syllable per note, and export a `.vsqx` that **Piapro Studio** imports.

## Status

- ✅ Core conversion works (MIDI → valid VOCALOID4 `.vsqx`, schema verified).
- ✅ Desktop GUI for fast lyric entry.
- 🚧 Real-world Piapro import — pending verification on a Piapro install (try the sample below and tell me how it goes).

## Requirements

- Python 3.9+
- `pip install -r requirements.txt` (installs [`mido`](https://mido.readthedocs.io/))

## Use it

1. In **FL Studio**: compose the melody, then **File ▸ Export ▸ MIDI file**.
2. Run the app: `python app.py`
3. **Open MIDI…** (Ctrl+O) — the notes appear in a table (Bar.Beat · Pitch · Duration · Lyric).
4. Click a **Lyric** cell (or press Enter) and type one syllable per note. **Enter saves and jumps to the next note** for fast entry; Esc cancels.
5. **Export VSQX…** (Ctrl+S).
6. In **Piapro Studio**: **File ▸ Import ▸ VSQX**. If every note sings “a”, run **Job ▸ Convert phonemes to match language**.

## Try the sample (no FL Studio needed)

`samples/twinkle.vsqx` is a ready-made example — import it straight into Piapro to test whether the format works. Regenerate it any time with:

```
python samples/make_twinkle.py
```

## Files

| File | Role |
|------|------|
| `app.py` | Desktop GUI (Tkinter) for loading MIDI and entering lyrics |
| `midi_reader.py` | MIDI parsing via `mido` → notes in 480-PPQ ticks |
| `vsqx_writer.py` | Writes VOCALOID4 `.vsqx` (verified schema) |
| `samples/` | Demo MIDI + VSQX and the generator script |

## Notes & limits (v1)

- **Lyrics-focused:** you author notes in FL Studio; this tool attaches lyrics (no in-app note editing yet).
- **Phonemes** default to `a`, left *unlocked* so Piapro can re-derive them from your lyrics.
- Uses the **first** tempo + time signature found (multi-tempo songs are future work).
- After import you may need to **select the Miku voice** in Piapro.
