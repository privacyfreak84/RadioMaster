"""Layout / rendering regression gate: render two copies of lofi.py through
the same scenarios and report any screen that differs, cell for cell
(character, fg, bg, reverse, underline, bold).

    git show HEAD:lofi.py > /tmp/lofi_before.py      # the version before your change
    python3 tools/compare_apps.py /tmp/lofi_before.py lofi.py

Matrix: 5 builtin themes x 5 terminal sizes (60x15 .. 191x41) x idle /
playing / history / stats, plus extra states (debug overlay, sleep timer,
search typing / no results, density cycle, selection moves) at 3 sizes.

Noise it deliberately ignores: digits (clock, 'Xm ago', session timers) are
masked, and bold is ignored in the station-list column because the
now-playing pulse toggles it on a wall clock. The debug-overlay log lines
are timing-sensitive - re-run before treating a debug-only diff as real.
An intentional visual change will (correctly) show up as differences; use
this to prove an *unintended* one didn't happen.
"""
import re, sys
from multiprocessing import Pool
import harness

THEMES = ["classic", "retro_radio", "cream", "reference", "cendre"]
BASE_SIZES = [(60, 15), (80, 24), (100, 30), (140, 45), (191, 41)]
EXTRA_SIZES = [(60, 15), (100, 30), (191, 41)]
BASE_STATES = {
    "idle": [' '],
    "playing": [' ', '\n'],
    "history": [' ', '\n', '2'],
    "stats": [' ', '\n', '3'],
}
EXTRA_STATES = {
    "debug": [' ', '\n', 'd'],
    "sleep": [' ', '\n', 't'],
    "sleep_hist": [' ', '\n', 't', '2'],
    "search_none": [' ', '/', 'zzzzqq'],
    "search_typing": [' ', '/', 'lo'],
    "density": [' ', '\n', 'v'],
    "sel_down": [' ', '\n', 'j', 'j', 'j'],
}


def snapshot(job):
    app, theme, (cols, rows), name, keys = job
    lines, scr, _ = harness.run(keys=keys, cols=cols, rows=rows, theme=theme, app=app)
    left_w = cols // 3
    cells = []
    for y in range(rows):
        for x in range(cols):
            c = scr.buffer[y][x]
            bold = c.bold if not (1 <= y and x <= left_w) else None
            cells.append((re.sub(r'\d', '#', c.data), c.fg, c.bg, bold, c.reverse, c.underscore))
    return (theme, f"{cols}x{rows}", name), cells, [re.sub(r'\d', '#', l) for l in lines]


def main(old_app, new_app):
    scenarios = [(t, s, n, k) for t in THEMES for s in BASE_SIZES for n, k in BASE_STATES.items()]
    scenarios += [(t, s, n, k) for t in THEMES for s in EXTRA_SIZES for n, k in EXTRA_STATES.items()]
    jobs = [(app, t, s, n, k) for app in (old_app, new_app) for (t, s, n, k) in scenarios]
    with Pool(8) as p:
        res = p.map(snapshot, jobs)
    half = len(res) // 2
    bad = []
    for o, n in zip(res[:half], res[half:]):
        if o[1] != n[1]:
            rows = [i for i, (a, b) in enumerate(zip(o[2], n[2])) if a != b]
            bad.append((o[0], rows))
    print(f"compared {half} screens; differing: {len(bad)}")
    for key, rows in bad[:40]:
        print("  ", key, "text rows:", rows[:12] if rows else "(colors/attributes only)")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
