# Research: FL Studio zoom shortcuts (the target behavior)

Source: [FL Studio online manual — Shortcuts](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/basics_shortcuts.htm) (fetched 2026-06-15).

## Piano Roll

- **`PgUp` / `PgDn`** — Zoom in / Zoom out (horizontal / time axis).
- No documented default keyboard shortcut for **vertical** zoom (it's done via the vertical zoom slider / mouse).

## Playlist

- **`PgUp` / `PgDn`** — Zoom in / Zoom out.
- **`Shift+1`…`Shift+3`** — Horizontal zoom levels (1 = out … 3 = in).
- **`Shift+4`** — Horizontal zoom, show all.
- **`Shift+5`** — Zoom to selection.
- **`Shift+0`** — Center playlist to play-head.

## Selection-based zoom (both windows)

- **`Ctrl+Right-Click` + drag** — drag to make a zoom selection (zoom on release).
- **`Ctrl+Shift+Right-Click`** — zoom to selected clip.

## Implication for our remap

FL's horizontal zoom is cleanly `PgUp`/`PgDn`, so we mirror that in Piapro. FL has **no** standard vertical-zoom key, so we introduce a convention: **`Ctrl+PgUp` / `Ctrl+PgDn`** for vertical (changeable on request).
