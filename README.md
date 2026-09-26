# RadioMaster (lofi.py)

A single-file, curses-based terminal internet radio / music player, built for a real terminal — not a generic TUI framework demo.

This repo is self-documenting: every new working session should start by reading **PROJECT_REFERENCE.md** (how the app is built, its conventions) and **PROJECT_STATUS.md** (what state it's in right now, what's next).

## Run it
```
python3 lofi.py
```
Requires: Python 3 (stdlib only — `tomllib` is used for TOML theme support on 3.11+, with a graceful fallback below that) and `mpv` installed and on `PATH` (used purely as a backend via its JSON IPC socket — no video, no terminal takeover).

## Files
- `lofi.py` — the entire application
- `PROJECT_REFERENCE.md` — architecture, subsystems, conventions
- `PROJECT_STATUS.md` — current phase, immediate goal, roadmap, session log
- `themes/` — standalone `.toml` theme files (drop-in for `~/.lofi_cli_themes/` or wherever `cfg['theme_dir']` points). `themes/reference.toml` is the exhaustive "every option, explicitly set and commented" specimen — start here when authoring a new theme.
