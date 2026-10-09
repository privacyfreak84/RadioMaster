# PROJECT_STATUS.md — RadioMaster (lofi.py)

Rewritten fully at the end of each session — not appended to. See PROJECT_REFERENCE.md for architecture/conventions (theme engine section especially — it's the biggest subsystem).

## Current state
`lofi.py` in this repo is the actual current version — it already includes everything described below (confirmed by inspecting the file directly: `ASCII_FONTS`, `exact_color_mode`, all style resolvers, the validator, TOML directory loading are all present and are the final, Gemini-bug-fixed versions, not earlier drafts).

**Core app** (mature, stable, not touched recently): station list/folders/fuzzy search, `mpv` JSON-IPC playback with real IPC-confirmed state, history/stats, add/edit/delete wizards with a "re-add previously deleted defaults" flow, sleep timer, volume HUD, responsive/small-terminal layout (content-aware Now Playing/Context split, three-tier footer degradation, clipped text everywhere an internal pane boundary exists).

**Theme engine — Layer 1 (visual language): done.**
Density, Now Playing style variants, selection style, tab style, section header style, metadata style, dialog padding, empty states, dialog title alignment — all theme-controlled, all backward-compatible (no existing builtin's look changed unless it opts in). Full detail in PROJECT_REFERENCE.md.

**Theme engine — Layer 2 (author-facing infra): mostly done.**
- Reference theme (exhaustive, every field set, non-default enum choices) — done, both as `BUILTIN_THEMES['reference']` and a standalone `reference.toml` (kept byte-identical by construction).
- External TOML theme directory with `extends`, cycle detection, auto-migration from legacy JSON, in-app configurable directory — done.
- Validator with auto-fix (Tools menu -> Validate Theme Files) — done, including the specific "misplaced top-level key" TOML gotcha check.
- Exact hex color support with graceful multi-tier fallback (`exact_color_mode`) — done, including a real bug found and fixed via an external second opinion (Gemini) mid-session: readback verification via `curses.color_content()` has no teeth against a terminal that lies about `init_color()` support, replaced with closest-existing-slot allocation.
- Custom ASCII fonts (registry, per-theme custom fonts, case-sensitive glyphs) — done, built along the way while working on Layer 2.
- **Preview mode — not started.**
- **Theme-author documentation — not started** (deliberately last, per the agreed plan, until the schema's proven stable).

**Known, deliberate (not accidental) gaps** — see PROJECT_REFERENCE.md's "Known, deliberate gaps" section for full detail:
- `border` color slot is resolvable but nothing in the render code reads it yet (dialog borders use `primary`, main frame uses plain fg/bg).
- `decorative` color only affects the ASCII-title banner's shading, not the empty-state flourish glyph.

## Immediate goal
John's annotated Cendre screenshot (2026-10-09) listed visual issues. Done this session: misaligned colons (Now Playing + Context pane, also affected Retro Radio), prominent title (`header_style = "badge"`), bigger/louder tabs (`tab_style = "pill"`), both opted into by Cendre. **Still open, pending John's answer:** (1) the "wasted space" band under the Now Playing info — it does *not* reproduce on this repo's HEAD (at 191x41 the divider sits one row under the last field, row 14, because the split is content-sized; John's screenshot shows it at row 22, which is what the old proportional-split branch produces), so John is probably running a different copy than the repo, or has an unpushed local change; (2) the station icon/name still renders as a small emoji + plain bold name on HEAD — John believes this was mostly fixed, so it may also be in an unpushed copy. Do not build either until that's resolved. After that the natural next items are, in order: **preview mode** (last unstarted Layer 2 item), then the "stop and dogfood" checkpoint (confirm the schema doesn't need to change shape across Cendre/Retro Radio/Cream/Reference), then theme-author docs, then stabilize + actual public GitHub release. Station packs are explicitly a separate, later branch.

## Roadmap (agreed, layered — see PROJECT_REFERENCE.md for the full backstory)
1. Layer 1 — visual language (density, NP variants, selection, tabs, section headers, metadata, dialogs+padding, empty states, footer) — done
2. Layer 2a — reference theme — done
3. Layer 2b — external TOML theme files — done
4. Layer 2c — validator + auto-fix — done
5. **Layer 2d — preview mode** <- next unstarted item
6. Layer 2e — theme-author documentation (short, human-readable: quick start / structure / colors / glyphs / borders / layout / inheritance / examples — not a 70-page manual)
7. Dogfood checkpoint — confirm schema is stable across all existing themes before freezing it
8. Stabilize API, write README, actual public GitHub release
9. *Separate branch, only after public release*: station packs (distributable station collections — mpv backend already isn't YouTube-only, confirmed via an earlier `.m3u8` experiment), pack import/export, community ecosystem

## Known issues
Nothing currently broken and unfixed. The two "known gaps" above are documented design debt, not bugs — flag before touching `border`/`decorative` color semantics since fixing them changes every existing theme's visible dialog borders.

## Session log
- **2026-10-09** — Fixed from John's Cendre screenshot: (a) colon misalignment — metadata labels now pad to the widest actual label instead of hardcoded spaces (Classic/Cream/Reference output verified byte-identical; Retro Radio visibly corrected); (b) new `header_style` (`plain`/`badge`) + `header_cap` glyph, Cendre uses `badge` with app_icon `◈ C E N D R E` (the old `🌫` emoji rendered as a broken glyph for John); (c) new `tab_style = "pill"`, Cendre uses it. Registered in validator, serializer key list, GLYPH_KEYS, reference theme and reference.toml (still parse-equal). Verified with a pty+pyte harness incl. real cell colors and 60x15 / 80x24 / 100x30 / 140x45 / 191x41. Test harness used a fake `mpv` (IPC socket stub) since mpv isn't installed in the sandbox. Not yet confirmed in John's real terminal.
- **2026-09-26** — Repo initialized from John's working `lofi.py`. Added README.md, PROJECT_REFERENCE.md, PROJECT_STATUS.md from scratch, then substantially expanded both after John supplied 4 prior conversation exports covering the full theme-engine build (polish pass -> theme engine -> Layer 1 -> Layer 2). No app code changes this session -- purely a documentation/history-import session, so future sessions don't need those transcripts re-pasted.
