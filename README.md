# DAW Extension (Claude)

A personal productivity toolkit that makes **Piapro Studio** (Crypton's VOCALOID editor) pleasant to use alongside **FL Studio** on Windows. Built incrementally as a learning project with [Claude Code](https://claude.com/claude-code).

## The problem this solves

I compose in FL Studio but use Piapro Studio for vocal synthesis. Piapro is dated and its keyboard/workflow differs from FL Studio, which slows me down. This toolkit closes that gap.

## Components

| Folder | What it does | Status |
|--------|--------------|--------|
| [`hotkeys/`](hotkeys/) | AutoHotkey v2 script remapping Piapro Studio's zoom hotkeys to match FL Studio | 🚧 In progress |
| [`midi2vsqx/`](midi2vsqx/) | Python desktop app: load an FL Studio MIDI export, type lyrics per note, export a Piapro-ready `.vsqx` | 📋 Planned |
| [`docs/`](docs/) | Research notes (FL shortcuts, Piapro manual, VSQx schema) | 🚧 In progress |

## Requirements

- Windows 11
- FL Studio (tested against 2025 / 21 / 20)
- Piapro Studio VSTi x64 (v2.0.4.1)
- [AutoHotkey v2](https://www.autohotkey.com/) — for the hotkeys
- Python 3.9+ — for the converter

## Quick start

Each component has its own README with setup and usage. Start with [`hotkeys/`](hotkeys/).

## Project log

The running development log lives in [`CLAUDE.md`](CLAUDE.md). Outcomes are also mirrored to a private Notion page.

---

*This is a personal hobby project. Piapro Studio, FL Studio, and VOCALOID are trademarks of their respective owners; this project is not affiliated with or endorsed by them.*
