# PROJECT_REFERENCE.md — RadioMaster (lofi.py)

Read this once per session to know how the app is built and what rules to follow before touching code. See PROJECT_STATUS.md for what's currently in progress.

## What this is
A single-file (`lofi.py`, ~4750 lines) curses TUI for browsing/playing internet radio stations, backed by `mpv`. No framework, no packages beyond the Python 3 standard library. Runs with `python3 lofi.py`.

## Runtime dependencies
- Python 3 stdlib only. `tomllib` (3.11+) is used for TOML theme parsing; if unavailable, the app falls back to legacy single-file JSON theme overrides and never scans/writes the TOML theme directory.
- `mpv` binary must be on `PATH`. If it's missing, `MPVRemote.mpv_available` flips to `False` and the app is expected to keep running (playback just doesn't work) rather than crash.

## On-disk files the app owns
- `~/.lofi_cli.json` — main config (`ConfigManager`): stations, folders, history, volume, last station, etc.
- `~/.lofi_cli.log` — debug log (`log_debug()`), capped in-memory ring buffer of the last 50 lines is also kept for an in-app debug view.
- `~/.lofi_cli_themes/` — TOML theme directory (default). Individual `.toml` files, one per theme, with `extends` inheritance.
- `~/.lofi_cli_themes.json` — legacy single-file JSON theme format, still read for migration/fallback.
- `/tmp/lofi_cli_mpv_<pid>.sock` — per-process mpv IPC socket, created and torn down each run.

## Core subsystems

### Playback — `MPVRemote`
- Spawns `mpv --no-video --idle --no-terminal --input-ipc-server=<socket>` as a subprocess and talks to it exclusively over the **JSON IPC socket**, never over stdin. (There's a deliberate note in the code: mpv does not execute slave-mode text commands written to a bare stdin pipe unless explicitly told to treat stdin as a command source — this bit the project before, hence IPC-only.)
- `_pipe_reader` threads forward mpv's own stdout/stderr into the shared debug log, so a failed stream shows *why* it failed instead of silently doing nothing.
- `_event_reader` is a daemon thread that listens to mpv's IPC events (`start-file`, `playback-restart`, `end-file`, etc.) and maintains `playback_state` (`idle` / `resolving` / `playing` / `error`) as ground truth. This replaced an earlier version that assumed playback succeeded the instant a `loadfile` command was *sent* — which produced a permanent false "Streaming" status when a stream silently failed to resolve.

### Theming — TOML theme engine
- Themes live as individual TOML files in a directory, with an `extends` key for inheritance (`resolve_theme`, `load_theme_registry`).
- `validate_theme_directory` / `validate_theme_dict` / `autofix_theme_dict` implement a validator with structured `ThemeIssue` objects (severity, path, message, optional autofix) and an in-app validator UI (`draw_theme_validator`, `draw_theme_validator_detail`) to surface and fix issues without leaving the app.
- Color resolution supports exact hex (`parse_hex_color`) with graceful degradation to the nearest xterm-256 color (`nearest_256_color`, `_build_xterm256_rgb_table`) for terminals without true-color support.
- Colors are addressed through **semantic roles**, not raw color numbers (see `resolve_color_component`, `now_playing_style`, `selection_style`, `tab_style`, etc.) — a theme defines what "selection" or "now playing" means, not which color slot to poke.
- Legacy JSON theme files are migrated into the TOML directory format on load (`_migrate_json_theme_file_to_dir`).

### ASCII art / typography
- `render_ascii_word` / `render_ascii_word_raw` draw custom ASCII fonts with two-tone shading (`draw_shaded_ascii_row`), with per-theme glyph and font resolution (`resolve_ascii_font`, `glyph()`, `label()`) and fallback chains for terminals with limited glyph support.

### Layout / canvas
- The whole layout (column widths, box sizes, art centering) was tuned by eye around a normal terminal (~171×39). Rather than stretching to fill an arbitrarily large terminal, the app draws onto a **capped canvas** (`MAX_CANVAS_W`, `create_canvas`) centered in the physical terminal — below the cap it fills the terminal exactly as before; above it, extra space becomes a calm margin, not stretched/sparse content.
- `handle_resize` recomputes canvas placement on terminal resize.

### App state / UI flow — `LofiApp`
- One large class driving the whole UI: station list, tabs (now playing / history / stats), wizards (add/edit station, folder create/manage, factory reset confirm, theme directory input), fuzzy search/filter (`fuzzy_score`, `update_filter`), scroll animation (`animate_scroll_to`), sleep timer, volume HUD.
- `draw()` is the single per-frame render entry point; `handle_input()` / `handle_wizard_input()` / `handle_theme_validator_input()` etc. are the corresponding per-mode input handlers, called from the main loop in `run()`.
- History/stats: each play session is tracked and finalized (`_finish_history_entry`), aggregated into `compute_stats()` and a per-station `get_station_history_stats()`.

## Conventions to keep
- **Single file.** Don't split `lofi.py` into modules unless explicitly asked — this is a deliberate personal-tool choice, not an oversight.
- **Stdlib only.** No new pip dependencies without asking first and explaining why in plain language.
- **Testing is visual and manual.** There is no automated test suite. John runs the app in his real terminal and reports visual discrepancies directly — he catches real bugs, not cosmetic nitpicks. Don't assume something works because the code "looks right"; flag anything that needs his eyes on a real terminal.
- **Don't touch working, unrelated code** while making a change — keep diffs scoped to the task at hand.
- **IPC over stdin, always**, for anything mpv-related — see the note in `MPVRemote`'s docstring above; this was a real, already-solved bug, don't reintroduce it.

## Rules for this repo (looser set — personal project)
- No strict phase-gating required, but do check PROJECT_STATUS.md for what's already in progress before starting something unrelated.
- New libraries: fine to propose, just say why first.
- Pull latest before starting a session's work (in case changes were made outside this sandbox).
- Commit and push in reasonably small, working increments rather than one giant diff at the end — protects against losing work if a session cuts off.
- Fully rewrite PROJECT_STATUS.md at the end of a session (not just appended), plus a short dated line in its session log.
- Only ever name John (GitHub: `privacyfreak84`) in status/log entries — no fictitious contributors.
