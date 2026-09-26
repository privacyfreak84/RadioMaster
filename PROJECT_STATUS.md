# PROJECT_STATUS.md — RadioMaster (lofi.py)

Rewritten fully at the end of each session — not appended to. See PROJECT_REFERENCE.md for architecture/conventions.

## Current state
`lofi.py` is a working, mature single-file curses music player. As of this session it was imported into this repo as-is from John's working copy (~4750 lines). No changes were made to the app logic in this session — this was purely a repo/documentation setup session.

Known-working, already built:
- Station list, folders, fuzzy search/filter
- Playback via `mpv` JSON IPC (`MPVRemote`), with real IPC-confirmed playback state (not an assumption)
- History tracking and stats tab
- TOML theme engine with inheritance (`extends`), hex color support with 256-color degradation, semantic color roles
- In-app theme validator with autofix
- ASCII font rendering with two-tone shading and glyph fallback chains
- Capped/centered canvas layout for large terminals
- Add/edit/delete station wizards, folder management, factory reset, sleep timer, volume HUD

## Immediate goal
None set yet — waiting on John's next task. This session's only goal (repo setup) is done.

## Roadmap
Not yet defined beyond "keep developing lofi.py." Add items here as they come up.

## Known issues
None logged yet in this repo. (If there are open bugs from before this repo existed, add them here.)

## Session log
- **2026-09-26** — Repo initialized from John's working `lofi.py`. Added README.md, PROJECT_REFERENCE.md, PROJECT_STATUS.md. No app code changes. Next session should start by asking John what he wants to work on.
