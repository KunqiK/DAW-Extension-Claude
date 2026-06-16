# midi2vsqx/ — Lyrics → VSQx converter

A small Python desktop app (Tkinter) that turns an FL Studio **MIDI export** plus **typed lyrics** into a **Piapro-ready `.vsqx`** file.

## Status

📋 Planned (Phase 2). Built after the hotkeys.

## Intended workflow

1. In **FL Studio**: compose the melody in the piano roll → export as a **MIDI file**.
2. In this app: **Load** the `.mid` → the notes appear in a table → type **one syllable per note**.
3. **Export** a `.vsqx`.
4. In **Piapro Studio**: **File ▸ Import ▸ VSQx** → notes + lyrics appear.

## Planned structure

- `app.py` — Tkinter GUI (note/lyric table, fast `Tab`/`Enter` entry, FL-like hotkeys).
- `midi_reader.py` — parse notes via [`mido`](https://mido.readthedocs.io/).
- `vsqx_writer.py` — emit VSQ4 XML (validated against a Piapro-exported reference).
- `requirements.txt` — `mido`.
- `samples/` — example `.mid` and exported `.vsqx`.

_Setup and run instructions will be added when the app exists._
