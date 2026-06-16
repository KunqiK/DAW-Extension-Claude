# hotkeys/ — Piapro Studio hotkeys to match FL Studio

An [AutoHotkey v2](https://www.autohotkey.com/) script that remaps Piapro Studio's zoom hotkeys to match FL Studio. Because Piapro Studio is closed-source and runs *inside* FL Studio as a plugin, the script is **context-sensitive**: the remaps fire **only while the Piapro editor window is focused**, so FL Studio's own keys are never affected.

## Status

🚧 In progress. Pending an on-machine discovery step (Piapro window class + its native zoom input).

## Target mapping (FL Studio → Piapro)

| Action | Key | Notes |
|--------|-----|-------|
| Zoom in / out **horizontally** | `PgUp` / `PgDn` | Exact FL Studio match |
| Zoom in / out **vertically** | `Ctrl+PgUp` / `Ctrl+PgDn` | FL has no default; convention, tunable |

## Setup (once the script is ready)

1. Install AutoHotkey v2: `winget install --id AutoHotkey.AutoHotkey`
2. Double-click `PiaproFLHotkeys.ahk` (a tray icon appears).
3. _(Optional)_ Add a shortcut to it in `shell:startup` to auto-run at login.

_Usage details and the autostart steps will be finalized here once the script is tested._
