import curses
import json
import os
import re
import socket
import subprocess
import time
import sys
import random
import logging
import copy
import threading
import locale
import shutil
import textwrap

try:
    import tomllib
    TOML_READ_SUPPORT = True
except ImportError:
    # Python < 3.11 has no stdlib TOML reader. The app still runs fine -
    # it just falls back to the legacy single-file JSON theme overrides
    # and never scans/writes the TOML theme directory.
    TOML_READ_SUPPORT = False

# --- DEBUG SYSTEM SETUP ---
LOG_FILE = os.path.expanduser("~/.lofi_cli.log")
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

DEBUG_LOGS = []

def log_debug(msg):
    logging.debug(msg)
    DEBUG_LOGS.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    if len(DEBUG_LOGS) > 50:
        DEBUG_LOGS.pop(0)

CONFIG_FILE = os.path.expanduser("~/.lofi_cli.json")

# The whole layout (column widths, box sizes, art centering) was tuned by eye
# around a normal terminal (~171x39). Letting it stretch to fill a much bigger
# terminal (e.g. 270x59) doesn't make it "responsive" - it just spreads the
# same amount of content over more space, so everything reads as small and
# sparse. Instead, the app draws onto a "canvas" window capped at these
# dimensions and centered in the physical terminal; below the cap it still
# fills the terminal exactly as before, so smaller/normal terminals are
# unaffected. Growing further just adds a calm margin instead of stretched
# whitespace inside the app itself.
MAX_CANVAS_W = 200
MAX_CANVAS_H = 50

# Station Database (seed data - copied into the user's config on first run,
# after which the config file is the source of truth so users can add/edit/delete freely)
DEFAULT_STATIONS = [
    # --- Lofi Girl ---
    {"slug": "lg-deep-sleep", "channel": "Lofi Girl", "name": "Deep Sleep Music", "url": "https://www.youtube.com/watch?v=LTiqKDrjqr4", "tags": ["lofi girl", "lofi", "sleep", "ambient", "calm"]},
    {"slug": "lg-sleep-radio", "channel": "Lofi Girl", "name": "Sleep Lofi Radio", "url": "https://www.youtube.com/watch?v=VAlMDl00mYY", "tags": ["lofi girl", "lofi", "sleep", "relax"]},
    {"slug": "lg-study", "channel": "Lofi Girl", "name": "Lofi Hip Hop (Study)", "url": "https://www.youtube.com/watch?v=X4VbdwhkE10", "tags": ["lofi girl", "lofi", "hiphop", "study", "beats"]},
    {"slug": "lg-synth", "channel": "Lofi Girl", "name": "Synth Ambient", "url": "https://www.youtube.com/watch?v=GSfT7H87zq4", "tags": ["lofi girl", "synth", "ambient", "space", "sleep"]},
    {"slug": "lg-pomodoro", "channel": "Lofi Girl", "name": "Study With Me (Pomodoro)", "url": "https://www.youtube.com/watch?v=qGohtGC5Rtk", "tags": ["lofi girl", "study", "pomodoro", "focus"]},
    {"slug": "lg-sad", "channel": "Lofi Girl", "name": "Sad Lofi Radio", "url": "https://www.youtube.com/watch?v=CwPCy1GLS38", "tags": ["lofi girl", "lofi", "sad", "rain", "beats"]},
    {"slug": "lg-asian", "channel": "Lofi Girl", "name": "Asian Lofi Radio", "url": "https://www.youtube.com/watch?v=1Tl2FtV06qo", "tags": ["lofi girl", "lofi", "asian", "relax"]},
    {"slug": "lg-jazz", "channel": "Lofi Girl", "name": "Jazz Lofi Radio", "url": "https://www.youtube.com/watch?v=E2vONfzoyRI", "tags": ["lofi girl", "lofi", "jazz", "chill"]},
    {"slug": "lg-chill", "channel": "Lofi Girl", "name": "Lofi Hip Hop (Chill)", "url": "https://www.youtube.com/watch?v=JD-kMIpDfnY", "tags": ["lofi girl", "lofi", "sleep", "chill", "beats"]},
    {"slug": "lg-piano", "channel": "Lofi Girl", "name": "Relaxing Piano", "url": "https://www.youtube.com/watch?v=N0snMcR6aaA", "tags": ["lofi girl", "piano", "focus", "relax"]},
    {"slug": "lg-xmas", "channel": "Lofi Girl", "name": "Christmas Lofi", "url": "https://www.youtube.com/watch?v=XSXEaikz0Bc", "tags": ["lofi girl", "christmas", "cozy", "festive"]},
    {"slug": "lg-classic", "channel": "Lofi Girl", "name": "Classical Music", "url": "https://www.youtube.com/watch?v=jXAEIWcGXwE", "tags": ["lofi girl", "classical", "study", "read"]},
    {"slug": "lg-relax-jazz", "channel": "Lofi Girl", "name": "Relaxing Jazz", "url": "https://www.youtube.com/watch?v=A8jDx9TLMQc", "tags": ["lofi girl", "jazz", "cozy", "study"]},
    {"slug": "lg-halloween", "channel": "Lofi Girl", "name": "Halloween Lofi", "url": "https://www.youtube.com/watch?v=3GQY80jyysQ", "tags": ["lofi girl", "halloween", "spooky"]},
    {"slug": "lg-fire", "channel": "Lofi Girl", "name": "Fireplace Ambience", "url": "https://www.youtube.com/watch?v=q_4KI-ChIIs", "tags": ["lofi girl", "ambient", "fire", "cozy"]},
    {"slug": "lg-guitar", "channel": "Lofi Girl", "name": "Chill Guitar", "url": "https://www.youtube.com/watch?v=E_XmwjgRLz8", "tags": ["lofi girl", "guitar", "chill", "study"]},
    {"slug": "lg-sleep-amb2", "channel": "Lofi Girl", "name": "Sleep Ambient", "url": "https://www.youtube.com/watch?v=xORCbIptqcc", "tags": ["lofi girl", "ambient", "sleep", "relax"]},
    {"slug": "lg-medieval", "channel": "Lofi Girl", "name": "Medieval Lofi", "url": "https://www.youtube.com/watch?v=IxPANmjPaek", "tags": ["lofi girl", "medieval", "lofi"]},
    {"slug": "lg-rain", "channel": "Lofi Girl", "name": "Gentle Rain Ambience", "url": "https://www.youtube.com/watch?v=-OekvEFm1lo", "tags": ["lofi girl", "rain", "ambient", "cozy"]},
    {"slug": "lg-dark", "channel": "Lofi Girl", "name": "Dark Ambient", "url": "https://www.youtube.com/watch?v=S_MOd40zlYU", "tags": ["lofi girl", "ambient", "dark", "escape"]},
    {"slug": "lg-synthwave", "channel": "Lofi Girl", "name": "Synthwave Radio", "url": "https://www.youtube.com/watch?v=4xDzrJKXOOY", "tags": ["lofi girl", "synthwave", "game", "chill"]},

    # --- The Bootleg Boy ---
    {"slug": "bb-sad", "channel": "The Bootleg Boy", "name": "Sad & Sleepy Beats", "url": "https://www.youtube.com/watch?v=FWjZ0x2M8og", "tags": ["the bootleg boy", "bootleg boy", "lofi", "sad", "sleep"]},

    # --- Steezy As Fuck ---
    {"slug": "saf-coffee", "channel": "Steezy As Fuck", "name": "Coffee Shop Radio", "url": "https://www.youtube.com/watch?v=blAFxjhg62k", "tags": ["steezy as fuck", "steezy", "lofi", "jazz", "coffee", "chill"]},
    {"slug": "saf-hiphop", "channel": "Steezy As Fuck", "name": "Lofi Hip Hop (Sleep/Study)", "url": "https://www.youtube.com/watch?v=rPjez8z61rI", "tags": ["steezy as fuck", "steezy", "lofi", "sleep", "study", "relax"]},

    # --- Chill With Taiki ---
    {"slug": "cwt-chill", "channel": "Chill With Taiki", "name": "24/7 Chill Lofi Hip Hop", "url": "https://www.youtube.com/watch?v=qH3fETPsqXU", "tags": ["chill with taiki", "taiki", "lofi", "hiphop", "chill", "sleep"]},

    # --- Nemo's Dreamscapes ---
    {"slug": "nd-mill", "channel": "Nemo's Dreamscapes", "name": "Stormy Night by Old Mill", "url": "https://www.youtube.com/watch?v=MYno31GY3zQ", "tags": ["nemos dreamscapes", "nemo", "oldies", "rain", "storm", "thunder", "asmr"]},
    {"slug": "nd-neverland", "channel": "Nemo's Dreamscapes", "name": "Dreaming of Neverland", "url": "https://www.youtube.com/watch?v=6CQ84mcOVMU", "tags": ["nemos dreamscapes", "nemo", "oldies", "night", "crickets", "asmr"]},
    {"slug": "nd-fallout", "channel": "Nemo's Dreamscapes", "name": "Fallout Radio (Rain)", "url": "https://www.youtube.com/watch?v=qrZL7xdgQvk", "tags": ["nemos dreamscapes", "nemo", "oldies", "rain", "chill", "fallout"]},
    {"slug": "nd-summer", "channel": "Nemo's Dreamscapes", "name": "1940s Summer Evening", "url": "https://www.youtube.com/watch?v=iXif_7KOG3U", "tags": ["nemos dreamscapes", "nemo", "oldies", "summer", "rain", "asmr"]},
    {"slug": "nd-calm", "channel": "Nemo's Dreamscapes", "name": "Calm Before The Storm", "url": "https://www.youtube.com/watch?v=x30hX9F3txs", "tags": ["nemos dreamscapes", "nemo", "oldies", "thunder", "ambient"]},
    {"slug": "nd-motel", "channel": "Nemo's Dreamscapes", "name": "Route 66 Motel (Storm)", "url": "https://www.youtube.com/watch?v=SwgSJmz6cpA", "tags": ["nemos dreamscapes", "nemo", "oldies", "storm", "asmr"]},
    {"slug": "nd-rain", "channel": "Nemo's Dreamscapes", "name": "Oldies & Rain", "url": "https://www.youtube.com/watch?v=37O8vwdgonY", "tags": ["nemos dreamscapes", "nemo", "oldies", "rain", "asmr"]},
    {"slug": "nd-night", "channel": "Nemo's Dreamscapes", "name": "A Great Night (Crickets)", "url": "https://www.youtube.com/watch?v=iXWGnKMCnUc", "tags": ["nemos dreamscapes", "nemo", "oldies", "night", "crickets"]},
    {"slug": "nd-fire", "channel": "Nemo's Dreamscapes", "name": "Oldies, Rain & Fire", "url": "https://www.youtube.com/watch?v=ELFWMkr6Z5Y", "tags": ["nemos dreamscapes", "nemo", "oldies", "rain", "fire", "storm"]},
    {"slug": "nd-coffee", "channel": "Nemo's Dreamscapes", "name": "Coffee Shop Rain", "url": "https://www.youtube.com/watch?v=nR-Zen2s2Qw", "tags": ["nemos dreamscapes", "nemo", "oldies", "coffee", "rain", "asmr"]}
]

ASCII_ART = [
    "██╗      ██████╗ ███████╗██╗",
    "██║     ██╔═══██╗██╔════╝██║",
    "██║     ██║   ██║█████╗  ██║",
    "██║     ██║   ██║██╔══╝  ██║",
    "███████╗╚██████╔╝██║     ██║",
    "╚══════╝ ╚═════╝ ╚═╝     ╚═╝"
]

# --- THEME ENGINE ---
# A theme controls colors, border style, and every icon/glyph in the UI (but NOT
# font size or terminal-level rendering - that's your terminal emulator's job,
# curses has no hook into it). User themes live in THEME_FILE as JSON and are
# deep-merged onto a builtin base, so a custom theme only needs to specify what
# it wants to change.
THEME_FILE = os.path.expanduser("~/.lofi_cli_themes.json")
# The legacy single-file theme store (above) is superseded by a discoverable
# directory of one .toml file per theme - a non-programmer can add a theme by
# dropping a file in here, without touching this .py file or hand-writing
# JSON. Path is user-configurable via cfg['theme_dir']; this is only the
# fallback when that's unset. See load_theme_registry() for the migration
# and merge logic between the two.
THEMES_DIR_DEFAULT = os.path.expanduser("~/.lofi_cli_themes/")

# Named aliases for the stable color-pair numbers apply_theme() initializes
# (see that method's docstring for the full contract). Draw code should use
# these instead of bare curses.color_pair(N) literals - same attribute value,
# but "PAIR_ERROR" tells you what it means without cross-referencing apply_theme.
#
# curses.color_pair() itself needs initscr() to have already run (it reads
# COLOR_PAIRS under the hood) - computing these at import time throws
# "must call initscr() first". So they start as None here and get their real
# values from init_pair_constants(), called from main() right after
# curses.wrapper() brings the screen up but before LofiApp (which is what
# actually uses them) is constructed.
PAIR_DEFAULT    = None   # terminal/theme default fg+bg, no override
PAIR_ACCENT     = None   # primary
PAIR_SUCCESS    = None   # playing/positive state
PAIR_WARNING    = None   # headings, hints, non-error caution
PAIR_SELECTION  = None   # highlight/selection
PAIR_LABEL      = None   # secondary, field labels
PAIR_ERROR      = None   # error/danger
PAIR_TEXT       = None   # plain text/background (matches bkgd)
PAIR_MUTED      = None   # de-emphasized text (not yet used in draw code)
PAIR_BORDER     = None   # panel borders/dividers (not yet used in draw code)
PAIR_DECORATIVE = None   # ornamental flourishes (not yet used in draw code)

def init_pair_constants():
    """Must be called once curses.initscr() has run (curses.wrapper() does
    this before invoking main()) and before any code references the PAIR_*
    names above."""
    global PAIR_DEFAULT, PAIR_ACCENT, PAIR_SUCCESS, PAIR_WARNING, PAIR_SELECTION
    global PAIR_LABEL, PAIR_ERROR, PAIR_TEXT, PAIR_MUTED, PAIR_BORDER, PAIR_DECORATIVE
    PAIR_DEFAULT    = curses.color_pair(0)
    PAIR_ACCENT     = curses.color_pair(1)
    PAIR_SUCCESS    = curses.color_pair(2)
    PAIR_WARNING    = curses.color_pair(3)
    PAIR_SELECTION  = curses.color_pair(4)
    PAIR_LABEL      = curses.color_pair(5)
    PAIR_ERROR      = curses.color_pair(6)
    PAIR_TEXT       = curses.color_pair(7)
    PAIR_MUTED      = curses.color_pair(8)
    PAIR_BORDER     = curses.color_pair(9)
    PAIR_DECORATIVE = curses.color_pair(10)

# ----------------------------------------------------------------------
# EXACT COLOR SUPPORT
#
# A theme's colors are normally just curses palette numbers (0-255, or -1
# for "terminal default") - authoring means picking the closest of 256
# fixed swatches, not specifying a color. Hex strings ("#3b82f6", or the
# 3-digit shorthand "#38f") are a second, equally valid way to write any
# color value in the schema, resolved at theme-apply time in one of two
# ways depending on what the terminal actually supports:
#
#   1. If the terminal can redefine its own palette (curses.can_change_color()
#      is True), LofiApp.resolve_color_component() hands the hex color a
#      real, otherwise-unused palette slot via curses.init_color() and every
#      draw call gets that exact RGB value, pixel for pixel.
#   2. If it can't (a real, common case - many terminals, including the
#      Linux console, report False here), the hex color is matched to
#      whichever of the 256 standard palette entries is closest by plain
#      Euclidean distance in RGB space, via nearest_256_color() below - so
#      the theme still looks *right*, just not pixel-exact, and nothing
#      ever crashes or falls back to a jarring default color over this.
#
# This is deliberately layered on top of the existing int/[fg,bg] pipeline,
# not a replacement for it - a plain int still means exactly what it always
# has, and everything downstream of resolve_color_component() (init_pair,
# the PAIR_* constants, every draw call) is completely unaware any of this
# happened; it just sees an ordinary palette number either way.
# ----------------------------------------------------------------------

def _build_xterm256_rgb_table():
    """The standard xterm 256-color palette as (r,g,b) 0-255 triples, index
    = palette number. Built from the well-documented formula rather than
    hand-typed, since hand-typing 256 RGB triples is exactly the kind of
    transcription-error-prone busywork that caused the ascii-font bugs
    earlier in this session:
      0-15:    the basic 16 ANSI colors (xterm's own conventional RGB values)
      16-231:  a 6x6x6 color cube (216 colors), each channel one of
               [0, 95, 135, 175, 215, 255]
      232-255: a 24-step grayscale ramp from 8 to 238
    """
    table = [
        (0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0),
        (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
        (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0),
        (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
    ]
    ramp = [0, 95, 135, 175, 215, 255]
    for r in range(6):
        for g in range(6):
            for b in range(6):
                table.append((ramp[r], ramp[g], ramp[b]))
    for i in range(24):
        v = 8 + i * 10
        table.append((v, v, v))
    return table

XTERM256_RGB = _build_xterm256_rgb_table()

def nearest_256_color(r, g, b, max_slot=None, exclude=None):
    """The palette index whose RGB is closest to (r,g,b) by plain squared
    Euclidean distance - simple, deterministic, and good enough for
    "closest reasonable swatch" without pulling in a real color-science
    dependency for something used a handful of times per theme switch.

    max_slot restricts the search to indices 0..max_slot (a terminal that
    only actually has, say, 16 real colors shouldn't get an index that
    means nothing to it) - None searches the full 256-entry table.

    exclude skips indices already claimed for a *different* exact-RGB
    request this session (see resolve_color_component: allocating the
    already-closest slot for redefinition means two different theme colors
    that are both "closest to slot 40" need the second one to fall back to
    its next-best option instead of silently colliding on the same slot).
    Returns None only if every candidate in range is excluded - the caller
    is expected to fall back to plain (non-exact) nearest-match in that
    case, same as the ordinary "ran out of slots" path."""
    excluded = set(exclude) if exclude else ()
    best_i, best_d = None, None
    for i, (pr, pg, pb) in enumerate(XTERM256_RGB):
        if max_slot is not None and i > max_slot:
            break
        if i in excluded:
            continue
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if best_d is None or d < best_d:
            best_i, best_d = i, d
    if best_i is None and excluded:
        # Every in-range candidate was excluded (an exact-color allocation
        # scenario) - fall back to the unrestricted best match rather than
        # returning nothing, so ordinary (non-exact) nearest-match calls
        # that never pass `exclude` are completely unaffected by this path.
        return nearest_256_color(r, g, b, max_slot=max_slot)
    return best_i

_HEX_COLOR_RE = re.compile(r'^#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})$')

def parse_hex_color(s):
    """Parse '#3b82f6' or the 3-digit shorthand '#38f' (each digit doubled,
    the same convention CSS uses) into an (r,g,b) 0-255 triple. Returns None
    for anything that isn't a well-formed hex color, rather than raising -
    every caller treats None as "not a hex color, handle some other way"."""
    if not isinstance(s, str) or not _HEX_COLOR_RE.match(s):
        return None
    digits = s[1:]
    if len(digits) == 3:
        digits = ''.join(ch * 2 for ch in digits)
    return tuple(int(digits[i:i + 2], 16) for i in (0, 2, 4))

def is_color_component(value):
    """True if `value` is something apply_theme()/the validator should
    accept as one half of a [fg, bg] pair or a bare background/foreground
    value: -1, any int, or a well-formed hex string."""
    if isinstance(value, bool):
        return False  # bool is technically an int subtype in Python - explicitly exclude it
    if isinstance(value, int):
        return True
    return parse_hex_color(value) is not None

BORDER_STYLES = {
    "sharp":   {"h": "─", "v": "│", "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
                "t_down": "┬", "t_up": "┴", "t_left": "├", "t_right": "┤"},
    "rounded": {"h": "─", "v": "│", "tl": "╭", "tr": "╮", "bl": "╰", "br": "╯",
                "t_down": "┬", "t_up": "┴", "t_left": "├", "t_right": "┤"},
    "double":  {"h": "═", "v": "║", "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
                "t_down": "╦", "t_up": "╩", "t_left": "╠", "t_right": "╣"},
    "ascii":   {"h": "-", "v": "|", "tl": "+", "tr": "+", "bl": "+", "br": "+",
                "t_down": "+", "t_up": "+", "t_left": "+", "t_right": "+"},
}

DEFAULT_TAG_ICONS = {
    'rain': '🌧', 'storm': '⛈', 'thunder': '⛈', 'fire': '🔥', 'jazz': '🎷',
    'piano': '🎹', 'classical': '🎹', 'guitar': '🎸', 'medieval': '🏰',
    'halloween': '🎃', 'christmas': '🎄', 'sleep': '😴', 'space': '🌌',
    'synth': '🌆', 'synthwave': '🌆', 'game': '🎮', 'fallout': '☢',
    'crickets': '🦗', 'night': '🌙', 'ambient': '🌫', 'coffee': '☕',
    'study': '📚', 'focus': '🎯', 'chill': '🧊', 'sad': '💧', 'asian': '🎏',
}

# A terminal can't be told to render one word bigger than the text around it -
# the font size is the font size. But a *shape* built out of several rows of
# ordinary characters can look as big and as stylized as we want, entirely
# under our own control. ASCII_FONTS is a registry of named block fonts a
# theme can pick between (or a theme can embed its own instead - see
# resolve_ascii_font() on LofiApp) used to render a theme's pane title as
# chunky ASCII art instead of a single line of normal text. Opt-in per theme
# via `"ascii_title": True`, so themes that are happy with a plain title
# (like Classic) are completely unaffected.
#
# Each font is self-contained: its own char_width/char_height (different
# fonts can be different sizes - nothing in the renderer assumes 3x5
# anymore) and a glyphs table of uppercase letter -> list of char_height
# strings. A letter's own rows must all be the same length as each other,
# but that width doesn't have to match every other letter in the font
# exactly (real block fonts vary a little letter to letter) - char_width is
# a nominal/typical value for documentation and layout estimates, not a
# hard per-glyph constraint the renderer enforces.
ASCII_FONTS = {
    "block": {
        "char_width": 3, "char_height": 5,
        "glyphs": {
            'A': ["░█░", "█░█", "███", "█░█", "█░█"],
            'B': ["██░", "█░█", "██░", "█░█", "██░"],
            'C': ["░██", "█░░", "█░░", "█░░", "░██"],
            'D': ["██░", "█░█", "█░█", "█░█", "██░"],
            'E': ["███", "█░░", "██░", "█░░", "███"],
            'F': ["███", "█░░", "██░", "█░░", "█░░"],
            'G': ["░██", "█░░", "█▄█", "█░█", "░██"],
            'H': ["█░█", "█░█", "███", "█░█", "█░█"],
            'I': ["███", "░█░", "░█░", "░█░", "███"],
            'J': ["░░█", "░░█", "░░█", "█░█", "░█░"],
            'K': ["█░█", "██░", "█░░", "██░", "█░█"],
            'L': ["█░░", "█░░", "█░░", "█░░", "███"],
            'M': ["█░█", "███", "███", "█░█", "█░█"],
            'N': ["█░█", "███", "███", "███", "█░█"],
            'O': ["░█░", "█░█", "█░█", "█░█", "░█░"],
            'P': ["██░", "█░█", "██░", "█░░", "█░░"],
            'Q': ["░█░", "█░█", "█░█", "░██", "░░█"],
            'R': ["██░", "█░█", "██░", "█░█", "█░█"],
            'S': ["░██", "█░░", "░█░", "░░█", "██░"],
            'T': ["███", "░█░", "░█░", "░█░", "░█░"],
            'U': ["█░█", "█░█", "█░█", "█░█", "░█░"],
            'V': ["█░█", "█░█", "█░█", "█░█", "░█░"],
            'W': ["█░█", "█░█", "███", "███", "█░█"],
            'X': ["█░█", "░█░", "░█░", "░█░", "█░█"],
            'Y': ["█░█", "█░█", "░█░", "░█░", "░█░"],
            'Z': ["███", "░░█", "░█░", "█░░", "███"],
            ' ': ["░░", "░░", "░░", "░░", "░░"],
        },
    },
    # A larger, chunkier 5x5 font - exists mainly to prove a font can have
    # completely different dimensions from "block" and the renderer/layout
    # code doesn't care, it just reads char_width/char_height off whichever
    # font is active.
    "slab": {
        "char_width": 5, "char_height": 5,
        "glyphs": {
            'A': ["░███░", "█░░░█", "█████", "█░░░█", "█░░░█"],
            'B': ["████░", "█░░░█", "████░", "█░░░█", "████░"],
            'C': ["░████", "█░░░░", "█░░░░", "█░░░░", "░████"],
            'D': ["████░", "█░░░█", "█░░░█", "█░░░█", "████░"],
            'E': ["█████", "█░░░░", "███░░", "█░░░░", "█████"],
            'F': ["█████", "█░░░░", "███░░", "█░░░░", "█░░░░"],
            'G': ["░████", "█░░░░", "█░███", "█░░░█", "░████"],
            'H': ["█░░░█", "█░░░█", "█████", "█░░░█", "█░░░█"],
            'I': ["█████", "░░█░░", "░░█░░", "░░█░░", "█████"],
            'J': ["░░███", "░░░░█", "░░░░█", "█░░░█", "░███░"],
            'K': ["█░░░█", "█░░█░", "███░░", "█░░█░", "█░░░█"],
            'L': ["█░░░░", "█░░░░", "█░░░░", "█░░░░", "█████"],
            'M': ["█░░░█", "██░██", "█░█░█", "█░░░█", "█░░░█"],
            'N': ["█░░░█", "██░░█", "█░█░█", "█░░██", "█░░░█"],
            'O': ["░███░", "█░░░█", "█░░░█", "█░░░█", "░███░"],
            'P': ["████░", "█░░░█", "████░", "█░░░░", "█░░░░"],
            'Q': ["░███░", "█░░░█", "█░█░█", "█░░█░", "░██░█"],
            'R': ["████░", "█░░░█", "████░", "█░░█░", "█░░░█"],
            'S': ["░████", "█░░░░", "░███░", "░░░░█", "████░"],
            'T': ["█████", "░░█░░", "░░█░░", "░░█░░", "░░█░░"],
            'U': ["█░░░█", "█░░░█", "█░░░█", "█░░░█", "░███░"],
            'V': ["█░░░█", "█░░░█", "█░░░█", "░█░█░", "░░█░░"],
            'W': ["█░░░█", "█░░░█", "█░█░█", "██░██", "█░░░█"],
            'X': ["█░░░█", "░█░█░", "░░█░░", "░█░█░", "█░░░█"],
            'Y': ["█░░░█", "░█░█░", "░░█░░", "░░█░░", "░░█░░"],
            'Z': ["█████", "░░░█░", "░░█░░", "░█░░░", "█████"],
            ' ': ["░░░░░", "░░░░░", "░░░░░", "░░░░░", "░░░░░"],
        },
    },
}

def _match_ascii_letters(word, glyphs):
    """Shared by render_ascii_word/render_ascii_word_raw: for each character
    in `word`, find its glyph rows - exact character first, falling back to
    the uppercase version if that exact case isn't defined in this font (see
    render_ascii_word's docstring for why). Characters matching neither are
    dropped."""
    letters = []
    for ch in word:
        if ch in glyphs:
            letters.append(glyphs[ch])
        elif ch.upper() in glyphs:
            letters.append(glyphs[ch.upper()])
    return letters

def render_ascii_word(word, font=None, fill='█', empty=' '):
    """Render `word` as font['char_height'] lines of block-letter text, with
    a 1-column gap between letters. `font` defaults to ASCII_FONTS['block']
    - pass the result of LofiApp.resolve_ascii_font() to use a theme's own
    choice (named builtin or a fully custom embedded font).

    Case handling: tries each character exactly as given first, so a font
    that defines distinct upper/lowercase glyphs (e.g. 'a' drawn differently
    from 'A') actually gets to use them. Only if the exact character isn't
    in the font does it fall back to the uppercase version - so a font that
    (like every builtin today) only defines uppercase glyphs still renders
    lowercase input exactly as before; nothing about this changes for those
    fonts. Characters with no match either way are dropped, not left blank.

    Every ink character collapses to one flat `fill` character (both '█'
    and '▓' - a font's own second-tone/shading marker, see
    render_ascii_word_raw - become indistinguishable here). Use this when a
    single solid color is genuinely what's wanted; use render_ascii_word_raw
    + LofiApp.draw_shaded_ascii_row for a real two-tone render.

    Returns a list of strings, all the same length; empty list if nothing
    in `word` was renderable in this font."""
    font = font or ASCII_FONTS['block']
    glyphs = font['glyphs']
    height = font['char_height']
    letters = _match_ascii_letters(word, glyphs)
    if not letters:
        return []
    lines = []
    for row in range(height):
        lines.append(' '.join(letter[row] for letter in letters if row < len(letter))
                      .replace('█', fill).replace('░', empty).replace('▓', fill))
    return lines

def render_ascii_word_raw(word, font=None):
    """Like render_ascii_word, but keeps each glyph's original ink
    characters instead of collapsing them to one flat fill character - '█'
    (main ink) and '▓' (a font's own second tone: a shadow/highlight edge,
    the way 'N' and 'Q' in the 'block' font already use it) stay distinct,
    and '░'/gap cells become plain spaces. Meant to be drawn with
    LofiApp.draw_shaded_ascii_row, which colors '█' and '▓' runs
    differently - giving a real two-tone/beveled look using the theme's own
    colors, instead of every ascii_title banner being flat single-color.
    Returns a list of strings, all the same length; empty list if nothing
    in `word` was renderable in this font."""
    font = font or ASCII_FONTS['block']
    glyphs = font['glyphs']
    height = font['char_height']
    letters = _match_ascii_letters(word, glyphs)
    if not letters:
        return []
    lines = []
    for row in range(height):
        lines.append(' '.join(letter[row] for letter in letters if row < len(letter))
                      .replace('░', ' '))
    return lines


# Color values are [fg, bg] pairs. -1 means "the terminal's own default".
# 0-7 are the basic ANSI colors (safe everywhere). 8-255 are xterm 256-color
# palette indices - richer, but only used if the terminal actually reports
# 256-color support (checked at runtime; theme colors are clamped down to
# whatever curses.COLORS the terminal actually has, so a fancy theme degrades
# instead of crashing on an old/minimal terminal).
BUILTIN_THEMES = {
    "classic": {
        "meta": {"name": "Classic", "description": "The original look - cyan & green on your terminal's own background."},
        "colors": {
            "accent":    [curses.COLOR_CYAN, -1],
            "success":   [curses.COLOR_GREEN, -1],
            "warning":   [curses.COLOR_YELLOW, -1],
            "highlight": [curses.COLOR_BLACK, curses.COLOR_CYAN],
            "label":     [curses.COLOR_MAGENTA, -1],
            "error":     [curses.COLOR_RED, -1],
        },
        "border_style": "sharp",
        "pulse": True,
        "glyphs": {
            "app_icon": "🎵 Lofi Stream CLI",
            "favorite": "★",
            "status_playing": "●",
            "status_paused": "●",
            "status_idle": "○",
            "status_error": "✕",
            "spinner": "◐◓◑◒",
            "volume_fill": "#",
            "volume_empty": "-",
            "hud_fill": "█",
            "hud_empty": "░",
            "default_tag_icon": "♫",
            "tag_icons": dict(DEFAULT_TAG_ICONS),
        },
        "idle_art": list(ASCII_ART),
    },
    "retro_radio": {
        "meta": {"name": "Retro Radio", "description": "Warm amber valve-radio glow on a dark cabinet background, double-line borders, and its own radio-set vocabulary."},
        "colors": {
            "background": 94,   # a warm, dark wood-cabinet brown
            "foreground": 223,  # warm cream/tan body text, readable on the brown
            "accent":    [208, -1],
            "success":   [178, -1],
            "warning":   [166, -1],
            "highlight": [235, 214],
            "label":     [173, -1],
            "error":     [160, -1],
        },
        "border_style": "double",
        "pulse": True,
        "glyphs": {
            "app_icon": "📻 Retro Radio",
            "favorite": "◆",
            "status_playing": "◉",
            "status_paused": "◎",
            "status_idle": "○",
            "status_error": "✕",
            "spinner": "◴◷◶◵",
            "volume_fill": "=",
            "volume_empty": ".",
            "hud_fill": "▮",
            "hud_empty": "▯",
            "default_tag_icon": "📻",
            "tag_icons": dict(DEFAULT_TAG_ICONS),
        },
        "labels": {
            "title_stations": "Frequencies", "title_favorites": "Presets",
            "tab_now_playing": "On Air", "tab_history": "Log", "tab_stats": "Meters",
            "context_header": "Dial",
            "lbl_channel": "Station", "lbl_tags": "Genre", "lbl_started": "Tuned In",
            "lbl_listening": "Airtime", "lbl_status": "Signal", "lbl_volume": "Gain",
            "lbl_sleep_timer": "Sleep Timer", "lbl_folders": "Bank", "lbl_favorite": "Preset",
            "lbl_played": "Tuned", "lbl_total_time": "Total Airtime", "lbl_last_played": "Last Tuned",
            "now_playing_none": "On Air : Nothing",
            "status_word_playing": "On Air", "status_word_paused": "Standby",
            "status_word_idle": "Off Air", "status_word_resolving": "Tuning…",
            "status_word_unavailable": "No Signal",
            "recent_sessions": "Broadcast Log", "session_summary": "Log Summary",
            "listening_time": "Airtime Logged", "most_played": "Top Frequencies",
            "search_prompt": "Tune",
        },
        "idle_art": [
            "· · ─── ◉ RADIO ◉ ─── · ·",
            "     (nothing tuned in yet)",
        ],
    },
    "cream": {
        "meta": {"name": "Cream", "description": "Cream & steel-blue, inspired by the r/unixporn desktop that started this."},
        "colors": {
            "background": 230,  # soft cream, matching the desktop screenshot
            "foreground": 239,  # dark slate body text, readable on the cream
            "accent":    [24, -1],
            "success":   [65, -1],
            "warning":   [173, -1],
            "highlight": [230, 24],
            "label":     [95, -1],
            "error":     [131, -1],
        },
        "border_style": "sharp",
        "pulse": True,
        "now_playing_style": "dense",  # was 'minimal', which never draws idle_art below - dense
                                        # is what actually lets the "nothing playing" line show
        "selection_style": "marker",
        "glyphs": {
            "app_icon": "◈ Lofi Stream CLI",
            "favorite": "●",
            "status_playing": "▮",
            "status_paused": "▯",
            "status_idle": "▯",
            "status_error": "✕",
            "spinner": "▖▘▝▗",
            "volume_fill": "▮",
            "volume_empty": "▯",
            "hud_fill": "▮",
            "hud_empty": "▯",
            "default_tag_icon": "♪",
            "tag_icons": dict(DEFAULT_TAG_ICONS),
            "selection_marker": "▶",
        },
        "idle_art": [
            "──── ♪ nothing playing ♪ ────",
        ],
    },
    "cendre": {
        "meta": {"name": "Cendre", "description": "Ash-charcoal base with a muted teal/amber/mauve palette, lifted straight off a Neovim + btop desktop - down to borrowing its own NORMAL-mode vocabulary."},
        "colors": {
            "background": 233,  # nearest xterm-256 match for #15110F
            "foreground": 253,  # soft off-white body text
            "accent":    [95, -1],  # nearest xterm-256 match for #8F6B5C, a muted warm rose-brown
            "success":   [114, -1],  # the git-diff-add / btop-bar green
            "warning":   [173, -1],  # warm terracotta, echoing the autumn-leaf art in the hardware panel
            "highlight": [233, 95],
            "label":     [175, -1],  # dusty mauve, the type/pink accent in the code panes
            "error":     [167, -1],  # muted coral, the git-diff-remove red
        },
        "border_style": "rounded",
        "pulse": True,
        "ascii_title": True,
        "glyphs": {
            "app_icon": "🌫 Cendre",
            "favorite": "✦",
            "status_playing": "◆",
            "status_paused": "◇",
            "status_idle": "·",
            "status_error": "✕",
            "spinner": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
            "volume_fill": "▰",
            "volume_empty": "▱",
            "hud_fill": "▰",
            "hud_empty": "▱",
            "default_tag_icon": "🌫",
            "tag_icons": dict(DEFAULT_TAG_ICONS),
        },
        "labels": {
            "title_stations": "Buffers", "title_favorites": "Pinned",
            "tab_now_playing": "Insert", "tab_history": "Log", "tab_stats": "Metrics",
            "context_header": "Status Line",
            "lbl_channel": "Source", "lbl_started": "Opened", "lbl_listening": "Session",
            "lbl_status": "Mode", "lbl_volume": "Gain", "lbl_sleep_timer": "Timeout",
            "lbl_folders": "Workspace", "lbl_favorite": "Pinned", "lbl_played": "Runs",
            "lbl_last_played": "Last Run",
            "now_playing_none": "Insert : (empty buffer)",
            "status_word_paused": "Paused", "status_word_idle": "Normal",
            "status_word_resolving": "Loading…", "status_word_unavailable": "No mpv",
            "recent_sessions": "Recent Log", "session_summary": "Session Diff",
            "listening_time": "Uptime", "most_played": "Top Buffers",
            "search_prompt": "Find",
        },
        "idle_art": [
            "░▒▓  N O R M A L  ▓▒░",
            "      (buffer empty)",
        ],
    },

    # ------------------------------------------------------------------
    # REFERENCE THEME
    #
    # Not meant to be anyone's daily driver - this is the "everything you
    # can customize" specimen for theme authors. Every top-level key the
    # engine understands is set here explicitly (nothing left to fall
    # through to a default), and every enum-style option is deliberately
    # pointed at a *non-default* choice so selecting this theme visibly
    # proves each one is wired up, not just declared. Comments throughout
    # note what the alternatives are and where the default sits.
    #
    # This still lives as a Python dict because external TOML theme files
    # (Layer 2, step 2) haven't landed yet - when they do, this is the
    # theme that becomes the annotated starting template for that format.
    # ------------------------------------------------------------------
    "reference": {
        # See reference.toml (a standalone, heavily-commented copy of this
        # exact theme) for a full explanation of every option and exactly
        # which on-screen element every color controls - comments here stay
        # short since the two need to be kept in sync by hand.

        "meta": {
            'name': 'Reference',
            'description': 'Exhaustive theme-schema demo, with comments explaining exactly what every option and every color does. Start here when authoring a new theme.',
        },

        # colors: mixes hex strings and plain palette ints on purpose, to
        # prove both work everywhere, including split across one [fg, bg]
        # pair (see "border" and "secondary" below).
        "colors": {
            'background': '#14141f',
            'foreground': 252,
            'primary': '#4da6ff',
            'success': [
                77,
                -1,
            ],
            'warning': '#e0a030',
            'selection': ['#14141f', '#4da6ff'],
            'secondary': [
                '#c792ea',
                -1,
            ],
            'error': [
                203,
                -1,
            ],
            'muted': '#6c7280',
            'border': [
                61,
                '#4da6ff',
            ],
            'decorative': '#e0a030',
        },

        'border_style': 'rounded',
        'density': 'spacious',
        'dialog_title_align': 'center',
        'pulse': True,
        'ascii_title': True,
        'now_playing_style': 'dense',
        'selection_style': 'marker',
        'tab_style': 'underlined',
        'section_header_style': 'marker',
        'metadata_style': 'aligned',
        'empty_state_style': 'decorative',

        # ascii_font: a full custom embedded font (not one of the named
        # builtins) - every glyph has a genuinely distinct upper AND lower
        # case form, and every glyph's bottom row uses the shading ink
        # character, so this one theme demonstrates case-sensitive glyphs
        # and two-tone shading at the same time.
        "ascii_font": {
            'char_width': 5,
            'char_height': 5,
            'glyphs': {
                'A': ['░███░', '█░░░█', '█████', '█░░░█', '▓░░░▓'],
                'B': ['████░', '█░░░█', '████░', '█░░░█', '▓▓▓▓░'],
                'C': ['░████', '█░░░░', '█░░░░', '█░░░░', '░▓▓▓▓'],
                'D': ['████░', '█░░░█', '█░░░█', '█░░░█', '▓▓▓▓░'],
                'E': ['█████', '█░░░░', '███░░', '█░░░░', '▓▓▓▓▓'],
                'F': ['█████', '█░░░░', '███░░', '█░░░░', '▓░░░░'],
                'G': ['░████', '█░░░░', '█░███', '█░░░█', '░▓▓▓▓'],
                'H': ['█░░░█', '█░░░█', '█████', '█░░░█', '▓░░░▓'],
                'I': ['█████', '░░█░░', '░░█░░', '░░█░░', '▓▓▓▓▓'],
                'J': ['░░███', '░░░░█', '░░░░█', '█░░░█', '░▓▓▓░'],
                'K': ['█░░░█', '█░░█░', '███░░', '█░░█░', '▓░░░▓'],
                'L': ['█░░░░', '█░░░░', '█░░░░', '█░░░░', '▓▓▓▓▓'],
                'M': ['█░░░█', '██░██', '█░█░█', '█░░░█', '▓░░░▓'],
                'N': ['█░░░█', '██░░█', '█░█░█', '█░░██', '▓░░░▓'],
                'O': ['░███░', '█░░░█', '█░░░█', '█░░░█', '░▓▓▓░'],
                'P': ['████░', '█░░░█', '████░', '█░░░░', '▓░░░░'],
                'Q': ['░███░', '█░░░█', '█░█░█', '█░░█░', '░▓▓░▓'],
                'R': ['████░', '█░░░█', '████░', '█░░█░', '▓░░░▓'],
                'S': ['░████', '█░░░░', '░███░', '░░░░█', '▓▓▓▓░'],
                'T': ['█████', '░░█░░', '░░█░░', '░░█░░', '░░▓░░'],
                'U': ['█░░░█', '█░░░█', '█░░░█', '█░░░█', '░▓▓▓░'],
                'V': ['█░░░█', '█░░░█', '█░░░█', '░█░█░', '░░▓░░'],
                'W': ['█░░░█', '█░░░█', '█░█░█', '██░██', '▓░░░▓'],
                'X': ['█░░░█', '░█░█░', '░░█░░', '░█░█░', '▓░░░▓'],
                'Y': ['█░░░█', '░█░█░', '░░█░░', '░░█░░', '░░▓░░'],
                'Z': ['█████', '░░░█░', '░░█░░', '░█░░░', '▓▓▓▓▓'],
                'a': ['░░░░░', '░███░', '█░░░█', '█████', '▓░░░▓'],
                'b': ['░░░░░', '████░', '█░░░█', '████░', '▓░░░▓'],
                'c': ['░░░░░', '░████', '█░░░░', '█░░░░', '▓░░░░'],
                'd': ['░░░░░', '████░', '█░░░█', '█░░░█', '▓░░░▓'],
                'e': ['░░░░░', '█████', '█░░░░', '███░░', '▓░░░░'],
                'f': ['░░░░░', '█████', '█░░░░', '███░░', '▓░░░░'],
                'g': ['░░░░░', '░████', '█░░░░', '█░███', '▓░░░▓'],
                'h': ['░░░░░', '█░░░█', '█░░░█', '█████', '▓░░░▓'],
                'i': ['░░░░░', '█████', '░░█░░', '░░█░░', '░░▓░░'],
                'j': ['░░░░░', '░░███', '░░░░█', '░░░░█', '▓░░░▓'],
                'k': ['░░░░░', '█░░░█', '█░░█░', '███░░', '▓░░▓░'],
                'l': ['░░░░░', '█░░░░', '█░░░░', '█░░░░', '▓░░░░'],
                'm': ['░░░░░', '█░░░█', '██░██', '█░█░█', '▓░░░▓'],
                'n': ['░░░░░', '█░░░█', '██░░█', '█░█░█', '▓░░▓▓'],
                'o': ['░░░░░', '░███░', '█░░░█', '█░░░█', '▓░░░▓'],
                'p': ['░░░░░', '████░', '█░░░█', '████░', '▓░░░░'],
                'q': ['░░░░░', '░███░', '█░░░█', '█░█░█', '▓░░▓░'],
                'r': ['░░░░░', '████░', '█░░░█', '████░', '▓░░▓░'],
                's': ['░░░░░', '░████', '█░░░░', '░███░', '░░░░▓'],
                't': ['░░░░░', '█████', '░░█░░', '░░█░░', '░░▓░░'],
                'u': ['░░░░░', '█░░░█', '█░░░█', '█░░░█', '▓░░░▓'],
                'v': ['░░░░░', '█░░░█', '█░░░█', '█░░░█', '░▓░▓░'],
                'w': ['░░░░░', '█░░░█', '█░░░█', '█░█░█', '▓▓░▓▓'],
                'x': ['░░░░░', '█░░░█', '░█░█░', '░░█░░', '░▓░▓░'],
                'y': ['░░░░░', '█░░░█', '░█░█░', '░░█░░', '░░▓░░'],
                'z': ['░░░░░', '█████', '░░░█░', '░░█░░', '░▓░░░'],
                ' ': ['░░░░░', '░░░░░', '░░░░░', '░░░░░', '░░░░░'],
            },
        },

        "glyphs": {
            'app_icon': {
                'nerd': '\uf001 Reference',
                'unicode': '◆ Reference',
                'ascii': '[#] Reference',
            },
            'favorite': {
                'nerd': '\uf005',
                'unicode': '★',
                'ascii': '*',
            },
            'status_playing': '◆',
            'status_paused': '◇',
            'status_idle': '·',
            'status_error': '✕',
            'spinner': '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏',
            'volume_fill': '▰',
            'volume_empty': '▱',
            'hud_fill': '▰',
            'hud_empty': '▱',
            'default_tag_icon': '♫',
            'selection_marker': '➤',
            'section_marker': '▣',
            'empty_state_deco': '◇',
            'tag_icons': {
                'rain': '🌧',
                'storm': '⛈',
                'thunder': '⛈',
                'fire': '🔥',
                'jazz': '🎷',
                'piano': '🎹',
                'classical': '🎹',
                'guitar': '🎸',
                'medieval': '🏰',
                'halloween': '🎃',
                'christmas': '🎄',
                'sleep': '😴',
                'space': '🌌',
                'synth': '🌆',
                'synthwave': '🌆',
                'game': '🎮',
                'fallout': '☢',
                'crickets': '🦗',
                'night': '🌙',
                'ambient': '🌫',
                'coffee': '☕',
                'study': '📚',
                'focus': '🎯',
                'chill': '🧊',
                'sad': '💧',
                'asian': '🎏',
            },
        },

        "labels": {
            'title_stations': 'Stations',
            'title_favorites': 'Favorites',
            'tab_now_playing': 'Now Playing',
            'tab_history': 'History',
            'tab_stats': 'Stats',
            'context_header': 'Context',
            'debug_header': '=== LIVE DEBUG LOGS ===',
            'lbl_channel': 'Channel',
            'lbl_tags': 'Tags',
            'lbl_started': 'Started',
            'lbl_listening': 'Listening',
            'lbl_status': 'Status',
            'lbl_volume': 'Volume',
            'lbl_sleep_timer': 'Sleep Timer',
            'lbl_folders': 'Folders',
            'lbl_favorite': 'Favorite',
            'lbl_played': 'Played',
            'lbl_total_time': 'Total Time',
            'lbl_last_played': 'Last Played',
            'lbl_total_sessions': 'Total Sessions',
            'lbl_avg_session': 'Avg Session',
            'lbl_longest': 'Longest',
            'lbl_today': 'Today',
            'lbl_all_time': 'All Time',
            'now_playing_none': 'Now Playing: None',
            'status_word_playing': 'Streaming',
            'status_word_paused': 'Paused',
            'status_word_idle': 'Idle',
            'status_word_resolving': 'Resolving...',
            'status_word_unavailable': 'Unavailable',
            'status_word_error': 'Stream Unavailable',
            'stream_error': 'Stream Error',
            'mpv_unavailable': 'mpv not found in PATH - install mpv to enable playback',
            'recent_sessions': 'Recent Sessions',
            'session_summary': 'Session Summary',
            'listening_time': 'Listening Time',
            'most_played': 'Most Played',
            'search_prompt': 'Search',
            'no_history': '(nothing played yet)',
            'no_stats_data': '(no data yet)',
            'no_station_selected': '(no station selected)',
            'no_search_results': 'No results',
            'empty_folder': 'This folder is empty',
            'no_stations': 'No stations yet',
            'no_folders_yet': '(no folders yet)',
            'no_readd_candidates': '(none)',
            'footer_controls': '[Enter]Play/Pause [1-3]View [a]Add [e]Edit [x]Del [o]Folder [O]Manage [m]Menu [f/F]Favs [s]Search [?]Help [q]Quit',
            'footer_controls_medium': '[Enter]Play/Pause [a/e/x]Add/Edit/Del [o/O]Folders [m]Menu [f/F]Favs [?]Help [q]Quit',
            'footer_controls_compact': '[Enter]Play/Pause [m]Menu [?]Help [q]Quit',
        },

        "idle_art": ['-- R E F E R E N C E --', '   (nothing playing yet)'],
    },
}

def _deep_merge(base, override):
    """Merge `override` onto a copy of `base`, recursing into nested dicts so a
    user theme can override just one field (e.g. one color) without having to
    restate the entire theme."""
    result = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result

def _toml_escape_str(s):
    return (s.replace('\\', '\\\\').replace('"', '\\"')
             .replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r'))

def _toml_key(k):
    """A bare TOML key only allows [A-Za-z0-9_-]; anything else (a space,
    for the ' ' glyph a custom ascii_font almost always needs to define,
    being the most common example) has to be a quoted key instead."""
    if k and re.fullmatch(r'[A-Za-z0-9_-]+', k):
        return k
    return f'"{_toml_escape_str(k)}"'

def _toml_value(v):
    """Serialize a Python value to inline TOML. Deliberately narrow: only
    handles the shapes the theme schema actually produces (bool, int, str,
    list of those, and one level of dict-as-inline-table for glyph
    fallback-chain entries like {"nerd":..,"unicode":..,"ascii":..}) - this
    is not a general-purpose TOML writer."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return f'"{_toml_escape_str(v)}"'
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{_toml_key(k)} = {_toml_value(val)}" for k, val in v.items()) + " }"
    raise TypeError(f"theme_to_toml: don't know how to serialize {type(v).__name__}")

def theme_to_toml(theme_def):
    """Serialize one raw (unresolved) theme dict to TOML text, matching the
    exact table layout _load_toml_theme_dir() expects back: top-level
    scalars/lists, then [meta], [colors], [glyphs] (with tag_icons broken
    out into its own [glyphs.tag_icons] sub-table), [ascii_font] when it's a
    custom font table (with its own [ascii_font.glyphs] sub-table - when
    it's just a font name instead, that's a plain top-level string, no
    table needed), then [labels]. Used both by the one-time JSON->TOML
    migration and as the template a theme author can copy and hand-edit."""
    lines = []
    top_level_keys = ['extends', 'border_style', 'density', 'dialog_title_align',
                       'pulse', 'ascii_title', 'now_playing_style', 'selection_style',
                       'tab_style', 'section_header_style', 'metadata_style', 'empty_state_style']
    for key in top_level_keys:
        if key in theme_def:
            lines.append(f"{key} = {_toml_value(theme_def[key])}")
    if isinstance(theme_def.get('ascii_font'), str):
        lines.append(f"ascii_font = {_toml_value(theme_def['ascii_font'])}")
    if 'idle_art' in theme_def:
        lines.append(f"idle_art = {_toml_value(theme_def['idle_art'])}")
    if lines:
        lines.append("")

    if 'meta' in theme_def:
        lines.append("[meta]")
        for k, v in theme_def['meta'].items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")

    if 'colors' in theme_def:
        lines.append("[colors]")
        for k, v in theme_def['colors'].items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")

    if 'glyphs' in theme_def:
        glyphs = theme_def['glyphs']
        tag_icons = glyphs.get('tag_icons')
        lines.append("[glyphs]")
        for k, v in glyphs.items():
            if k == 'tag_icons':
                continue
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
        if tag_icons:
            lines.append("[glyphs.tag_icons]")
            for k, v in tag_icons.items():
                lines.append(f"{k} = {_toml_value(v)}")
            lines.append("")

    if isinstance(theme_def.get('ascii_font'), dict):
        font = theme_def['ascii_font']
        lines.append("[ascii_font]")
        if 'char_width' in font:
            lines.append(f"char_width = {_toml_value(font['char_width'])}")
        if 'char_height' in font:
            lines.append(f"char_height = {_toml_value(font['char_height'])}")
        lines.append("")
        glyphs = font.get('glyphs', {})
        if glyphs:
            lines.append("[ascii_font.glyphs]")
            for letter, rows in glyphs.items():
                lines.append(f"{_toml_key(letter)} = {_toml_value(rows)}")
            lines.append("")

    if 'labels' in theme_def:
        lines.append("[labels]")
        for k, v in theme_def['labels'].items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"

def _load_toml_theme_dir(themes_dir):
    """Scan themes_dir for *.toml files and parse each into a raw theme
    dict, keyed by filename stem. The filename - not meta.name - is the
    stable, discoverable identifier a theme is selected and extended by;
    meta.name is only ever a display label. Malformed files are logged and
    skipped rather than crashing theme loading for everything else."""
    themes = {}
    if not TOML_READ_SUPPORT or not os.path.isdir(themes_dir):
        return themes
    try:
        entries = sorted(os.listdir(themes_dir))
    except OSError as e:
        log_debug(f"Couldn't list themes dir {themes_dir}: {e}")
        return themes
    for fname in entries:
        if not fname.endswith('.toml'):
            continue
        name = fname[:-len('.toml')]
        path = os.path.join(themes_dir, fname)
        try:
            with open(path, 'rb') as f:
                parsed = tomllib.load(f)
            themes[name] = parsed
            issues = validate_theme_dict(parsed)
            for issue in issues:
                log_debug(f"Theme file {fname}: [{issue.severity}] {issue.path or '(root)'}: {issue.message}")
        except Exception as e:
            log_debug(f"Failed to parse theme file {path}: {e} - skipping it, other themes unaffected.")
    return themes

def validate_theme_directory(themes_dir, known_theme_names=None):
    """Validate every *.toml file in themes_dir, independent of whether it
    would actually load cleanly into the registry (a file with a parse
    error still gets a slot here, with the parse error as its one issue,
    so the in-app validator screen can show it instead of it just vanishing
    the way a normal load silently skips it). Returns an ordered list of
    (filename, raw_dict_or_None, issues) - raw_dict is None only when the
    file failed to parse as TOML at all, in which case autofix has nothing
    to work with."""
    results = []
    if not TOML_READ_SUPPORT or not os.path.isdir(themes_dir):
        return results
    try:
        entries = sorted(os.listdir(themes_dir))
    except OSError as e:
        log_debug(f"Couldn't list themes dir {themes_dir} for validation: {e}")
        return results
    for fname in entries:
        if not fname.endswith('.toml'):
            continue
        path = os.path.join(themes_dir, fname)
        try:
            with open(path, 'rb') as f:
                raw = tomllib.load(f)
        except Exception as e:
            results.append((fname, None, [ThemeIssue('error', '', f"Doesn't parse as TOML: {e}")]))
            continue
        results.append((fname, raw, validate_theme_dict(raw, known_theme_names=known_theme_names)))
    return results

def autofix_theme_file(themes_dir, fname, raw, issues):
    """Apply every auto-fixable issue for one theme file and write the
    result back to disk. The original is backed up to '<fname>.bak' first
    (overwriting any previous backup - this is a one-fix-at-a-time tool,
    not version control) so a bad auto-fix is always one file-copy away
    from undone. Returns (fixed_dict, applied_descriptions) - raises on
    any I/O failure rather than silently leaving the directory half-changed."""
    fixed, applied = autofix_theme_dict(raw, issues)
    if not applied:
        return fixed, applied
    path = os.path.join(themes_dir, fname)
    backup_path = path + '.bak'
    shutil.copy2(path, backup_path)
    with open(path, 'w') as f:
        f.write(theme_to_toml(fixed))
    log_debug(f"Auto-fixed {fname} ({len(applied)} change(s)); original backed up to {os.path.basename(backup_path)}.")
    return fixed, applied

def _migrate_json_theme_file_to_dir(themes_dir):
    """One-time move from the old single-file THEME_FILE to one .toml file
    per theme in themes_dir, so existing overrides survive the format
    switch instead of silently vanishing. Only archives (renames away) the
    old JSON file once every theme in it has been written out successfully
    - if even one write fails, the JSON file is left in place so nothing is
    lost, and load_theme_registry() will keep reading both sources until a
    later run gets a clean migration. A .toml file that already exists at
    the destination is never overwritten (treated as the user's own
    edit/replacement taking precedence), and doesn't count as a failure."""
    if not os.path.exists(THEME_FILE):
        return
    if not TOML_READ_SUPPORT:
        log_debug("TOML support unavailable (Python < 3.11) - leaving legacy theme JSON file in place, unmigrated.")
        return
    try:
        os.makedirs(themes_dir, exist_ok=True)
    except OSError as e:
        log_debug(f"Couldn't create themes dir {themes_dir} for migration: {e}")
        return
    try:
        with open(THEME_FILE, 'r') as f:
            user_themes = json.load(f)
    except Exception as e:
        log_debug(f"Failed to read {THEME_FILE} for migration: {e} - leaving it in place.")
        return

    any_failures = False
    any_written = False
    for name, theme_def in user_themes.items():
        dest = os.path.join(themes_dir, f"{name}.toml")
        if os.path.exists(dest):
            log_debug(f"Migration: {dest} already exists - leaving it as-is, not overwriting from JSON.")
            continue
        try:
            with open(dest, 'w') as f:
                f.write(theme_to_toml(theme_def))
            any_written = True
            log_debug(f"Migrated theme '{name}' from {THEME_FILE} to {dest}.")
        except Exception as e:
            any_failures = True
            log_debug(f"Failed to write migrated theme '{name}' to {dest}: {e}")

    if any_written and not any_failures:
        archived = THEME_FILE + '.migrated'
        try:
            os.rename(THEME_FILE, archived)
            log_debug(f"All themes migrated cleanly - archived old file to {archived}.")
        except OSError as e:
            log_debug(f"Themes migrated but couldn't archive old file {THEME_FILE}: {e}")
    elif any_failures:
        log_debug(f"Some themes failed to migrate - leaving {THEME_FILE} in place so nothing is lost.")

# ----------------------------------------------------------------------
# THEME VALIDATOR
#
# A theme .toml file that parses without error can still be structurally
# wrong in a way TOML's own parser has no way to catch - the most common
# real-world case being a bare key placed after a [table] header with
# nothing closing that table back out to the top level, so it silently
# becomes e.g. labels.idle_art instead of the theme's real idle_art. That
# file is 100% valid TOML; it just doesn't mean what its author intended.
# This validator checks the *parsed* dict against the schema the engine
# actually reads (see apply_theme/glyph/label above for where each of
# these vocabularies comes from), flags anything that doesn't fit, and -
# for the misplaced-key case specifically, since the fix is unambiguous -
# can auto-repair it.
# ----------------------------------------------------------------------

TOP_LEVEL_SCALAR_SCHEMA = {
    'extends':             str,
    'border_style':        {'sharp', 'rounded', 'double', 'ascii'},
    'density':              {'compact', 'normal', 'spacious'},
    'dialog_title_align':  {'left', 'center'},
    'pulse':               bool,
    'ascii_title':          bool,
    'now_playing_style':   {'dense', 'minimal'},
    'selection_style':     {'block', 'marker'},
    'tab_style':           {'numbered', 'underlined'},
    'section_header_style':{'plain', 'marker'},
    'metadata_style':      {'aligned', 'inline'},
    'empty_state_style':   {'plain', 'decorative'},
}
TOP_LEVEL_TABLE_KEYS = {'meta', 'colors', 'glyphs', 'labels'}
TOP_LEVEL_LIST_KEYS = {'idle_art'}
# Keys whose value can legitimately be one of two different TOML shapes -
# ascii_font is either a bare string (a name to look up in ASCII_FONTS) or
# a whole [ascii_font] table (a theme's own embedded custom font). Kept
# separate from TOP_LEVEL_SCALAR_SCHEMA, which assumes exactly one type per
# key, and validated by its own dedicated block further down instead.
TOP_LEVEL_POLYMORPHIC_KEYS = {'ascii_font'}
ALL_TOP_LEVEL_KEYS = set(TOP_LEVEL_SCALAR_SCHEMA) | TOP_LEVEL_TABLE_KEYS | TOP_LEVEL_LIST_KEYS | TOP_LEVEL_POLYMORPHIC_KEYS

COLOR_KEYS = {
    'background', 'foreground',
    'accent', 'primary', 'success', 'warning', 'highlight', 'selection',
    'label', 'secondary', 'error', 'muted', 'border', 'decorative',
}

GLYPH_KEYS = {
    'app_icon', 'favorite', 'status_playing', 'status_paused', 'status_idle',
    'status_error', 'spinner', 'volume_fill', 'volume_empty', 'hud_fill',
    'hud_empty', 'default_tag_icon', 'tag_icons', 'selection_marker',
    'section_marker', 'empty_state_deco',
}

LABEL_KEYS = {
    'title_stations', 'title_favorites', 'tab_now_playing', 'tab_history',
    'tab_stats', 'context_header', 'debug_header', 'lbl_channel', 'lbl_tags',
    'lbl_started', 'lbl_listening', 'lbl_status', 'lbl_volume',
    'lbl_sleep_timer', 'lbl_folders', 'lbl_favorite', 'lbl_played',
    'lbl_total_time', 'lbl_last_played', 'lbl_total_sessions',
    'lbl_avg_session', 'lbl_longest', 'lbl_today', 'lbl_all_time',
    'now_playing_none', 'status_word_playing', 'status_word_paused',
    'status_word_idle', 'status_word_resolving', 'status_word_unavailable',
    'status_word_error', 'stream_error', 'mpv_unavailable', 'recent_sessions',
    'session_summary', 'listening_time', 'most_played', 'search_prompt',
    'no_history', 'no_stats_data', 'no_station_selected', 'no_search_results',
    'empty_folder', 'no_stations', 'no_folders_yet', 'no_readd_candidates',
    'footer_controls', 'footer_controls_medium', 'footer_controls_compact',
}

# name of the sub-vocabulary each table key belongs to, for error messages
SUBTABLE_KEYS = {'colors': COLOR_KEYS, 'glyphs': GLYPH_KEYS, 'labels': LABEL_KEYS}

class ThemeIssue:
    """One validation finding. `path` is a dotted location like 'labels.idle_art'
    or 'colors.acent'. `autofix` is a (description, apply_fn) pair when the
    fix is unambiguous - apply_fn takes the raw theme dict and mutates it in
    place - or None when it isn't (unknown key with no obvious match, wrong
    type, etc. all need a human to decide)."""
    def __init__(self, severity, path, message, autofix=None):
        self.severity = severity  # 'error' | 'warning' | 'info' (info = not wrong, just worth knowing)
        self.path = path
        self.message = message
        self.autofix = autofix  # (description, callable(raw_dict)) or None

    def __repr__(self):
        return f"ThemeIssue({self.severity}, {self.path!r}, {self.message!r}, autofix={'yes' if self.autofix else 'no'})"

def _closest_match(name, candidates, max_distance=3):
    """Cheap typo-suggestion for unknown keys - plain Levenshtein, no
    dependency, only used to make an error message more actionable
    ('did you mean tab_now_playing?'), never to silently guess-and-fix."""
    def edit_distance(a, b):
        if len(a) < len(b):
            a, b = b, a
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            curr = [i]
            for j, cb in enumerate(b, 1):
                cost = 0 if ca == cb else 1
                curr.append(min(prev[j] + 1, curr[j-1] + 1, prev[j-1] + cost))
            prev = curr
        return prev[-1]
    best, best_d = None, max_distance + 1
    for c in candidates:
        d = edit_distance(name, c)
        if d < best_d:
            best, best_d = c, d
    return best if best_d <= max_distance else None

def validate_theme_dict(raw, known_theme_names=None):
    """Check one theme's raw (unresolved, as-parsed) dict against the schema
    the engine actually reads. Returns a list of ThemeIssue. Doesn't require
    curses or a running app - pure data in, findings out, so it's testable
    standalone and safe to run on every file at load time."""
    issues = []

    if not isinstance(raw, dict):
        return [ThemeIssue('error', '', f"Theme file doesn't contain a table at all (got {type(raw).__name__}).")]

    # --- top-level: unknown keys, and the flagship check - a known
    # top-level key name showing up *inside* colors/glyphs/labels instead,
    # almost always because a bare key was placed after that table's
    # header with nothing to close it back to top level. ---
    for key, value in raw.items():
        if key in ALL_TOP_LEVEL_KEYS:
            continue
        suggestion = _closest_match(key, ALL_TOP_LEVEL_KEYS)
        issues.append(ThemeIssue('warning', key,
            f"Unknown top-level key '{key}'" + (f" - did you mean '{suggestion}'?" if suggestion else "") +
            " (ignored; won't affect anything)."))

    for table_name in ('colors', 'glyphs', 'labels'):
        table = raw.get(table_name)
        if table is None:
            continue
        if not isinstance(table, dict):
            issues.append(ThemeIssue('error', table_name, f"'{table_name}' should be a table, got {type(table).__name__}."))
            continue
        vocab = SUBTABLE_KEYS[table_name]
        for key, value in table.items():
            if key in vocab:
                continue
            if key in TOP_LEVEL_SCALAR_SCHEMA or key in TOP_LEVEL_LIST_KEYS or key in TOP_LEVEL_POLYMORPHIC_KEYS:
                # The flagship, auto-fixable case: this is a real top-level
                # key that ended up nested here, almost certainly because it
                # was written after this table's header with no following
                # header to close it back to root scope.
                def make_fix(tname=table_name, k=key):
                    def fix(d):
                        v = d[tname].pop(k, None)
                        if k not in d:  # never clobber an existing top-level value
                            d[k] = v
                    return fix
                conflict = key in raw
                autofix = None if conflict else (
                    f"Move '{key}' out of [{table_name}] back to the top level, where it belongs.",
                    make_fix())
                msg = (f"'{key}' is a top-level option, but it's nested inside [{table_name}] here - "
                       f"almost always means it was placed after the [{table_name}] header in the file "
                       f"with nothing after it to close that table back to the top level.")
                if conflict:
                    msg += f" Can't auto-fix: '{key}' already has its own top-level value too - pick one by hand."
                issues.append(ThemeIssue('error', f"{table_name}.{key}", msg, autofix=autofix))
            else:
                suggestion = _closest_match(key, vocab)
                issues.append(ThemeIssue('warning', f"{table_name}.{key}",
                    f"Unknown {table_name} key '{key}'" + (f" - did you mean '{suggestion}'?" if suggestion else "") +
                    " (ignored; won't affect anything)."))

    # --- structural scalars: right type / right enum value ---
    for key, spec in TOP_LEVEL_SCALAR_SCHEMA.items():
        if key not in raw:
            continue
        value = raw[key]
        if spec is str:
            if not isinstance(value, str):
                issues.append(ThemeIssue('error', key, f"'{key}' should be text, got {type(value).__name__}."))
        elif spec is bool:
            if not isinstance(value, bool):
                issues.append(ThemeIssue('error', key, f"'{key}' should be true/false, got {type(value).__name__}."))
        elif isinstance(spec, set):
            if value not in spec:
                choices = " | ".join(sorted(spec))
                issues.append(ThemeIssue('error', key, f"'{key}' is '{value}', but must be one of: {choices}."))

    if 'extends' in raw and known_theme_names is not None:
        parent = raw['extends']
        if isinstance(parent, str) and parent not in known_theme_names:
            issues.append(ThemeIssue('error', 'extends', f"extends '{parent}', which isn't a known theme."))

    # --- idle_art: list of strings, plus an advisory on when it actually renders ---
    if 'idle_art' in raw:
        art = raw['idle_art']
        if not isinstance(art, list) or not all(isinstance(x, str) for x in art):
            issues.append(ThemeIssue('error', 'idle_art', "'idle_art' should be a list of text lines."))
        elif raw.get('now_playing_style') == 'minimal':
            issues.append(ThemeIssue('warning', 'idle_art',
                "This theme sets now_playing_style to 'minimal', which never draws idle_art "
                "(that style skips the metadata table and decoration entirely, by design) - "
                "so this art will never actually be seen unless now_playing_style changes to 'dense'."))
        else:
            issues.append(ThemeIssue('info', 'idle_art',
                "idle_art only ever renders when now_playing_style is 'dense' (the default), "
                "nothing has been played yet this session (it disappears for good once you play "
                "anything, until restart), and the layout isn't in compact mode - an automatic "
                "fallback used on short terminals that drops decoration first. It's normal for "
                "this not to show up under a small terminal or after playing a station."))

    # --- ascii_font: either a name in ASCII_FONTS, or a fully custom font table ---
    if 'ascii_font' in raw:
        font_value = raw['ascii_font']
        if isinstance(font_value, str):
            if font_value not in ASCII_FONTS:
                suggestion = _closest_match(font_value, ASCII_FONTS.keys())
                issues.append(ThemeIssue('error', 'ascii_font',
                    f"ascii_font '{font_value}' isn't a known font (available: {', '.join(sorted(ASCII_FONTS))})"
                    + (f" - did you mean '{suggestion}'?" if suggestion else "") +
                    ". Or embed your own font as an [ascii_font] table instead of a name."))
        elif isinstance(font_value, dict):
            char_height = font_value.get('char_height')
            glyphs = font_value.get('glyphs')
            known_font_table_keys = {'char_width', 'char_height', 'glyphs'}
            for k in font_value:
                if k not in known_font_table_keys:
                    suggestion = _closest_match(k, known_font_table_keys)
                    issues.append(ThemeIssue('warning', f'ascii_font.{k}',
                        f"Unknown key '{k}' in a custom ascii_font table" +
                        (f" - did you mean '{suggestion}'?" if suggestion else "") + " (ignored)."))
            if not isinstance(char_height, int) or char_height <= 0:
                issues.append(ThemeIssue('error', 'ascii_font.char_height', "A custom ascii_font needs 'char_height' set to a positive whole number."))
            if 'char_width' in font_value and not isinstance(font_value['char_width'], int):
                issues.append(ThemeIssue('error', 'ascii_font.char_width', "'char_width' should be a whole number."))
            if not isinstance(glyphs, dict) or not glyphs:
                issues.append(ThemeIssue('error', 'ascii_font.glyphs', "A custom ascii_font needs a non-empty 'glyphs' table (letter -> list of text rows)."))
            elif isinstance(char_height, int) and char_height > 0:
                for letter, rows in glyphs.items():
                    path = f"ascii_font.glyphs.{letter}"
                    if not isinstance(rows, list) or not all(isinstance(r, str) for r in rows):
                        issues.append(ThemeIssue('error', path, f"Glyph '{letter}' should be a list of text rows."))
                        continue
                    if len(rows) != char_height:
                        issues.append(ThemeIssue('error', path,
                            f"Glyph '{letter}' has {len(rows)} row(s), but char_height says {char_height} - every glyph needs exactly that many rows."))
                    row_widths = set(len(r) for r in rows)
                    if len(row_widths) > 1:
                        issues.append(ThemeIssue('error', path, f"Glyph '{letter}' has rows of different widths ({sorted(row_widths)}) - all rows in one glyph must be the same width."))
        else:
            issues.append(ThemeIssue('error', 'ascii_font',
                f"ascii_font should be a font name (text) or a custom font table, got {type(font_value).__name__}."))

        if not raw.get('ascii_title', False):
            issues.append(ThemeIssue('info', 'ascii_font',
                "ascii_font is set here, but ascii_title isn't true in this theme, so this font is "
                "configured but never actually used - pane titles render as plain text either way."))

    # --- colors: a curses palette number/-1, a hex color string, or a
    # 2-item [fg, bg] list where each item is independently either ---
    for key, value in raw.get('colors', {}).items():
        if key not in COLOR_KEYS:
            continue  # already reported above
        if is_color_component(value):
            continue
        if isinstance(value, list) and len(value) == 2:
            bad_sides = [v for v in value if not is_color_component(v)]
            if not bad_sides:
                continue
            for v in bad_sides:
                if isinstance(v, str) and v.startswith('#'):
                    issues.append(ThemeIssue('error', f"colors.{key}",
                        f"'{v}' isn't a valid hex color in {key} - needs 3 or 6 hex digits after '#', like #3b82f6 or #38f."))
                else:
                    issues.append(ThemeIssue('error', f"colors.{key}",
                        f"'{key}' has an invalid side {v!r} - each side of [fg, bg] should be a curses color number or a hex color."))
            continue
        if isinstance(value, str) and value.startswith('#'):
            issues.append(ThemeIssue('error', f"colors.{key}",
                f"'{value}' isn't a valid hex color - needs 3 or 6 hex digits after '#', like #3b82f6 or #38f."))
        else:
            issues.append(ThemeIssue('error', f"colors.{key}",
                f"'{key}' should be a curses color number, a hex color like \"#3b82f6\", or [fg, bg] where each side is independently either - got {value!r}."))

    # --- glyphs: plain string, or a {nerd/unicode/ascii} chain (tag_icons is its own str->str map) ---
    for key, value in raw.get('glyphs', {}).items():
        if key == 'tag_icons':
            if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
                issues.append(ThemeIssue('error', 'glyphs.tag_icons', "'tag_icons' should be a table of tag name -> glyph text."))
        elif key in GLYPH_KEYS:
            if isinstance(value, str):
                continue
            if isinstance(value, dict) and set(value.keys()) <= {'nerd', 'unicode', 'ascii'} and all(isinstance(v, str) for v in value.values()):
                continue
            issues.append(ThemeIssue('error', f"glyphs.{key}", f"'{key}' should be text, or a table with only nerd/unicode/ascii keys - got {value!r}."))

    # --- labels: plain strings ---
    for key, value in raw.get('labels', {}).items():
        if key in LABEL_KEYS and not isinstance(value, str):
            issues.append(ThemeIssue('error', f"labels.{key}", f"'{key}' should be text, got {type(value).__name__}."))

    return issues

def autofix_theme_dict(raw, issues=None):
    """Apply every auto-fixable issue in `issues` (or re-validate and fix
    everything fixable if issues isn't given) to a *copy* of raw, and return
    (fixed_dict, list_of_descriptions_applied). Never mutates the input, and
    never touches an issue without an autofix - those need a human."""
    if issues is None:
        issues = validate_theme_dict(raw)
    fixed = copy.deepcopy(raw)
    applied = []
    for issue in issues:
        if issue.autofix:
            description, fn = issue.autofix
            fn(fixed)
            applied.append(description)
    return fixed, applied

def load_theme_registry(theme_dir=None):
    """Builtin themes, plus anything the user has defined, layered on top
    from two possible sources merged together:

    1. The legacy single-file THEME_FILE (~/.lofi_cli_themes.json), a JSON
       object of {theme_name: {...partial theme...}} - kept working forever
       for anyone who never touches the new format.
    2. A discoverable directory of one .toml file per theme (themes_dir,
       defaulting to THEMES_DIR_DEFAULT, overridable via cfg['theme_dir']) -
       the actual author-facing format: no Python or JSON knowledge needed,
       just a text file with [colors]/[glyphs]/[labels] tables. On first run
       with an existing THEME_FILE, its contents are auto-migrated into this
       directory (see _migrate_json_theme_file_to_dir) so nothing is lost.

    If the same theme name exists in both, the .toml directory entry wins -
    it's the newer, more specific format, and post-migration is normally the
    only one that still has that name anyway.

    Inheritance: a theme can set "extends": "<other_theme_name>" to start
    from that theme's fully-resolved definition and override just the parts
    it cares about - the point being a person can write a 10-line personal
    theme ("extends cream, just change the accent color") instead of
    copying every field. A theme with no "extends" key implicitly extends
    "classic" (matching the original behavior, so nothing has to restate
    classic's whole color/glyph set just to tweak one thing) - unless it's
    overriding an existing theme of the same name outright, in which case it
    layers onto that theme's own raw definition instead, so e.g. a personal
    tweak to "cendre" still starts from cendre, not classic. A cycle in
    "extends" links (including a theme indirectly extending itself) is
    detected and broken rather than recursing forever - see resolve()
    below."""
    themes_dir = theme_dir or THEMES_DIR_DEFAULT
    _migrate_json_theme_file_to_dir(themes_dir)

    raw = copy.deepcopy(BUILTIN_THEMES)

    if os.path.exists(THEME_FILE):
        try:
            with open(THEME_FILE, 'r') as f:
                user_themes = json.load(f)
            for name, theme_def in user_themes.items():
                if name in raw and 'extends' not in theme_def:
                    raw[name] = _deep_merge(raw[name], theme_def)
                else:
                    raw[name] = theme_def
        except Exception as e:
            log_debug(f"Failed to load user themes from {THEME_FILE}: {e}")

    for name, theme_def in _load_toml_theme_dir(themes_dir).items():
        if name in raw and 'extends' not in theme_def:
            raw[name] = _deep_merge(raw[name], theme_def)
        else:
            raw[name] = theme_def

    resolved = {}

    def resolve(name, chain):
        if name in resolved:
            return resolved[name]
        if name not in raw:
            log_debug(f"Theme '{'->'.join(chain)}' extends unknown theme '{name}' - ignoring that link.")
            return {}
        if name in chain:
            log_debug(f"Theme inheritance cycle detected ({'->'.join(chain)}->{name}) - breaking it there.")
            return {}
        own = raw[name]
        parent_name = own.get('extends')
        if parent_name is None and name != 'classic':
            parent_name = 'classic'
        parent = resolve(parent_name, chain + [name]) if parent_name else {}
        merged = _deep_merge(parent, {k: v for k, v in own.items() if k != 'extends'})
        resolved[name] = merged
        return merged

    for name in raw:
        resolve(name, [])
    return resolved

def resolve_theme(name, registry):
    """Look up a theme by name (falling back to classic if it doesn't exist),
    and pre-compute its actual border character set (named style + any manual
    per-glyph overrides) so drawing code never has to think about the two-step
    resolution."""
    theme = registry.get(name)
    if not theme:
        log_debug(f"Unknown or unresolved theme '{name}', falling back to classic.")
        theme = registry['classic']
    theme = copy.deepcopy(theme)
    border_chars = dict(BORDER_STYLES.get(theme.get('border_style', 'sharp'), BORDER_STYLES['sharp']))
    border_chars.update(theme.get('border_chars', {}))
    theme['_border_chars'] = border_chars
    return theme

class ConfigManager:
    def __init__(self):
        self.config = {
            "favorites": [],
            "volume": 70,
            "last_station": None,
            "stations": None,
            "folders": None,
            "synced_default_slugs": None,
            "deleted_default_slugs": [],
            "history": [],
            "onboarded": True,
            "theme": "classic",
            "glyph_mode": "unicode",  # 'nerd' | 'unicode' | 'ascii' - see LofiApp.glyph()
            "density": None,  # 'compact' | 'normal' | 'spacious' | None (None = use theme's preferred density)
            "theme_dir": None,  # custom path for the per-file .toml theme directory; None = use THEMES_DIR_DEFAULT (~/.lofi_cli_themes/)
            "exact_color_mode": "auto",  # 'auto' (default: use exact RGB if the terminal claims support and a readback check confirms it actually works) | 'always' (skip the readback check - for terminals that verifiably support it but whose readback happens to disagree) | 'never' (force nearest-match always, ignoring can_change_color() entirely - the guaranteed-safe escape hatch for a terminal that mishandles color redefinition in a way no amount of readback verification can catch, since curses can only ask itself what it thinks it wrote, not what the terminal actually displays)
        }
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config.update(json.load(f))
            except Exception:
                pass

        # First run (or corrupted/missing stations list): seed from the built-in defaults.
        if not self.config.get('stations'):
            log_debug("No saved station list found; seeding from built-in defaults.")
            self.config['stations'] = copy.deepcopy(DEFAULT_STATIONS)
            self.config['onboarded'] = False

        # First run, or an upgrade from a version without folders: put every existing
        # station into a "Default" folder so nothing becomes invisible.
        if not self.config.get('folders'):
            log_debug("No folders found; creating 'Default' folder with all current stations.")
            self.config['folders'] = {"Default": [s['slug'] for s in self.config['stations']]}

        # Track which built-in defaults have already been introduced to this user's
        # library, so "Sync Defaults" only adds ones that are genuinely new.
        if not self.config.get('synced_default_slugs'):
            current_slugs = {s['slug'] for s in self.config['stations']}
            self.config['synced_default_slugs'] = [
                d['slug'] for d in DEFAULT_STATIONS if d['slug'] in current_slugs
            ]

        self.save()

    def save(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
        except Exception as e:
            log_debug(f"CONFIG SAVE FAILED: {e}")

class MPVRemote:
    """
    Controls mpv over its JSON IPC socket (--input-ipc-server).

    NOTE: mpv does NOT execute slave-mode text commands written to a bare
    stdin pipe. That only works if mpv is explicitly told to treat stdin
    (or a fifo) as a command source. Without that, everything written to
    process.stdin is silently discarded -- which is why audio never played.
    The JSON IPC socket is the supported, non-deprecated way to do this.
    """
    def __init__(self):
        self.socket_path = f"/tmp/lofi_cli_mpv_{os.getpid()}.sock"
        self.process = None
        self.sock = None
        self.mpv_available = True  # flips to False if mpv itself can't be found/started

        # Real, IPC-confirmed playback state - 'idle' | 'resolving' | 'playing' | 'error'.
        # This used to not exist at all: play_selected() just assumed success the
        # instant the loadfile command was *sent*, so a stream that mpv silently
        # failed to resolve (blocked/rate-limited by the provider, bad URL, etc.)
        # showed "Streaming" forever with no audio. mpv's IPC socket already reports
        # exactly what's happening via events (start-file/playback-restart/end-file);
        # _event_reader below listens for them so this state is always the truth,
        # not an assumption.
        self.playback_state = 'idle'
        self.last_error = None
        self.start_process()

    def start_process(self):
        try:
            if os.path.exists(self.socket_path):
                os.remove(self.socket_path)

            log_debug("Initializing MPV process with IPC socket...")
            self.process = subprocess.Popen(
                [
                    'mpv', '--no-video', '--idle',
                    '--no-terminal',  # don't let mpv fight curses for the tty
                    f'--input-ipc-server={self.socket_path}',
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # line-buffered, so log lines show up promptly
            )
            # mpv's own stdout/stderr (extractor errors, warnings, etc.) used to
            # go straight to DEVNULL - completely invisible. Read them on daemon
            # threads into the same debug log everything else uses, so a failed
            # stream shows *why* it failed instead of just silently not playing.
            threading.Thread(target=self._pipe_reader, args=(self.process.stdout, "MPV-OUT"), daemon=True).start()
            threading.Thread(target=self._pipe_reader, args=(self.process.stderr, "MPV-ERR"), daemon=True).start()
            log_debug("MPV process spawned. Waiting for IPC socket to appear...")
            self._connect_socket()
        except FileNotFoundError:
            self.mpv_available = False
            log_debug("CRITICAL ERROR: 'mpv' executable not found in PATH!")
        except Exception as e:
            self.mpv_available = False
            log_debug(f"CRITICAL ERROR starting MPV: {str(e)}")

    def _pipe_reader(self, pipe, prefix):
        """Runs on a daemon thread for the lifetime of one mpv process, reading
        its stdout or stderr line-by-line and pushing each into the shared
        debug log. Exits cleanly on EOF (mpv exited) or if the pipe is
        replaced/closed out from under it during a self-heal restart."""
        try:
            for line in iter(pipe.readline, ''):
                line = line.rstrip()
                if line:
                    log_debug(f"{prefix}: {line}")
        except (ValueError, OSError):
            pass  # pipe closed while we were mid-read; nothing to do
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    def _connect_socket(self):
        # Give mpv a moment to create the socket file before we dial it.
        for _ in range(50):  # ~5 seconds total
            if os.path.exists(self.socket_path):
                try:
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.settimeout(2)
                    s.connect(self.socket_path)
                    # The 2s timeout above only bounds the connect() call itself.
                    # Left in place, it also applies to every subsequent recv() -
                    # so the event reader's blocking read would raise
                    # socket.timeout after 2s of mpv silence (e.g. idle, waiting
                    # for you to hit play) and die silently, caught by its own
                    # broad except. That's what caused playback_state to get
                    # stuck on "resolving" even once audio was actually
                    # flowing: nothing was left listening for the
                    # playback-restart event. Reset to blocking now that we're
                    # connected.
                    s.settimeout(None)
                    self.sock = s
                    log_debug("Connected to MPV IPC socket.")
                    threading.Thread(target=self._event_reader, args=(s,), daemon=True).start()
                    return
                except Exception as e:
                    log_debug(f"IPC connect attempt failed: {e}")
            time.sleep(0.1)
        log_debug("CRITICAL ERROR: Timed out waiting for MPV IPC socket.")

    def _event_reader(self, sock):
        """Runs on a daemon thread for the lifetime of one IPC connection,
        reading mpv's JSON event stream and updating self.playback_state to
        whatever mpv is *actually* doing - not what we hope it's doing. mpv
        pushes these events unprompted on every connected client, no
        subscription needed. Exits cleanly when the socket closes (mpv quit,
        or a reconnect replaced it - see send_command)."""
        try:
            f = sock.makefile('r', encoding='utf-8', newline='\n')
        except Exception as e:
            log_debug(f"MPV-EVENT: failed to wrap socket for reading: {e}")
            return
        try:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._handle_ipc_message(msg)
        except (OSError, ValueError) as e:
            # This used to swallow socket.timeout here with zero logging,
            # which is exactly what let the settimeout(2) bug above go
            # unnoticed - the thread would just vanish. Now it says so.
            log_debug(f"MPV-EVENT: reader thread exiting due to {type(e).__name__}: {e}")
        finally:
            log_debug("MPV-EVENT: reader thread stopped.")
            try:
                f.close()
            except Exception:
                pass

    def _handle_ipc_message(self, msg):
        event = msg.get("event")
        if event is None:
            return  # a command reply, not an event - nothing to react to here
        if event == "start-file":
            # A new load was requested. We already set 'resolving' locally the
            # moment play() was called, so this just confirms mpv picked it up.
            self.playback_state = "resolving"
        elif event == "playback-restart":
            # This fires when audio/video actually starts flowing - the one
            # signal that means "yes, this is genuinely playing," as opposed
            # to merely having sent mpv a command.
            self.playback_state = "playing"
            self.last_error = None
            log_debug("MPV-EVENT: playback-restart (audio confirmed flowing)")
        elif event == "end-file":
            reason = msg.get("reason")
            if reason == "error":
                err = msg.get("file_error") or "unknown mpv error"
                self.playback_state = "error"
                self.last_error = err
                log_debug(f"MPV-EVENT: end-file, reason=error - {err}")
            elif reason in ("eof", "stop"):
                # 'loadfile ... replace' emits end-file(stop) for the outgoing
                # track before start-file for the new one. If we've already
                # optimistically marked 'resolving' for a new track, don't
                # flicker back to idle in between - only go idle if nothing
                # new is in flight.
                if self.playback_state != "resolving":
                    self.playback_state = "idle"
                log_debug(f"MPV-EVENT: end-file, reason={reason}")
        elif event == "idle":
            if self.playback_state != "resolving":
                self.playback_state = "idle"

    def send_command(self, command_list):
        # Self-healing: If MPV crashed for any reason, reboot it.
        if self.process and self.process.poll() is not None:
            log_debug("MPV process died unexpectedly! Restarting it automatically...")
            self.playback_state = "error"
            self.last_error = "mpv process crashed and had to be restarted"
            self.sock = None
            self.start_process()

        if not self.sock:
            log_debug(f"MPV-CMD SKIPPED (no socket yet): {command_list}")
            return

        payload = json.dumps({"command": command_list}) + "\n"
        try:
            log_debug(f"MPV-CMD: {payload.strip()}")
            self.sock.sendall(payload.encode('utf-8'))
        except Exception as e:
            log_debug(f"MPV-CMD FAILED: {str(e)}; will try to reconnect...")
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
            self._connect_socket()

    def play(self, url):
        # Optimistically mark 'resolving' immediately, synchronously, before
        # the command even hits the socket - this closes the race where an
        # end-file(stop) event for the *previous* track could otherwise land
        # after we send but before mpv processes the new load, and get
        # misread as "nothing is playing."
        self.playback_state = "resolving"
        self.last_error = None
        self.send_command(["loadfile", url, "replace"])

    def stop(self):
        self.send_command(["stop"])
        self.playback_state = "idle"
        self.last_error = None

    def set_volume(self, vol):
        self.send_command(["set_property", "volume", vol])

    def toggle_pause(self, is_paused):
        self.send_command(["set_property", "pause", bool(is_paused)])

    def quit(self):
        if self.process:
            self.send_command(["quit"])
            time.sleep(0.2)
            try:
                self.process.terminate()
            except Exception:
                pass
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except Exception:
                pass

class LofiApp:
    def __init__(self, stdscr):
        self.root = stdscr          # the real, full physical terminal window
        self.stdscr = None          # the capped/centered canvas everything draws onto
        self.create_canvas()
        log_debug("App Booting Up...")
        self.config_mgr = ConfigManager()
        self.cfg = self.config_mgr.config

        self.theme_registry = load_theme_registry(self.cfg.get('theme_dir'))
        self.theme = resolve_theme(self.cfg.get('theme', 'classic'), self.theme_registry)

        # Exact-color state (see resolve_color_component()): which hex
        # colors have already been given a real palette slot this run, so
        # switching themes back and forth reuses the same slot for the same
        # hex value instead of leaking a new one every time, and how many
        # of those slots are left to hand out. can_change_color() and
        # COLORS are read once here rather than on every call - they don't
        # change mid-session, and repeatedly asking curses is pointless work.
        self._can_change_color = None  # queried lazily on first use - see resolve_color_component()
        self._custom_color_slots = {}
        self._exact_color_warned = False

        self.mpv = MPVRemote()
        # Set initial volume after boot
        self.mpv.set_volume(self.cfg['volume'])

        self.stations = self.cfg['stations']
        self.folders = self.cfg['folders']
        self.filtered_stations = list(self.stations)
        self.selected_idx = 0
        self.scroll_offset = 0
        self.scroll_target = 0

        self.search_mode = False
        self.search_query = ""
        self.show_favorites_only = False
        self.current_folder = None  # None/"All" = no folder filter
        self.show_debug = False

        self.is_playing = False
        self.is_paused = False
        self.status_msg = "Idle"
        self.current_station = None
        self.sleep_timer_end = None

        # Right-pane workspace tabs: 1=Now Playing, 2=History, 3=Stats
        self.workspace_tab = 1
        self.history = self.cfg['history']
        self.current_history_entry = None  # dict in self.history for the active session

        # Transient on-screen notification (e.g. "Synced 2 new stations")
        self.toast_msg = None
        self.toast_until = 0
        self.volume_hud_until = 0

        # Add/Edit wizard + delete-confirmation state
        self.mode = None            # None | 'wizard' | 'confirm' | 'tools_menu' |
                                     # 'folder_picker' | 'folder_manage' | 'folder_name_input' |
                                     # 'help' | 'onboarding' | 'theme_picker' | 'readd_picker'
        self.wizard_action = None   # 'add' | 'edit'
        self.wizard_target_slug = None
        self.wizard_step = 0        # 0:url 1:name 2:channel 3:tag_select 4:new_tags 5:folder_select
        self.wizard_data = {}
        self.wizard_buffer = ""
        self.wizard_error = ""
        self.tag_list = []
        self.tag_checked = set()
        self.tag_cursor = 0
        self.wizard_folder_checked = set()

        # "Reuse existing value" picker overlay, usable on the Name/Channel text steps
        self.wizard_picker_open = False
        self.wizard_picker_options = []
        self.wizard_picker_cursor = 0

        self.confirm_kind = None    # 'delete_station' | 'delete_folder' | 'factory_reset'
        self.confirm_target = None
        self.delete_target_slug = None  # kept for backwards-compat readability

        self.tools_cursor = 0

        # "Re-add previously deleted defaults" picker (offered before Sync Defaults
        # when cfg['deleted_default_slugs'] is non-empty)
        self.readd_candidates = []
        self.readd_checked = set()
        self.readd_cursor = 0

        self.theme_picker_cursor = 0

        self.folder_picker_cursor = 0
        self.folder_manage_cursor = 0
        self.folder_name_action = None  # 'create' | 'rename'
        self.folder_name_target = None  # old name, when renaming
        self.folder_name_buffer = ""
        self.theme_dir_buffer = ""
        self.validator_results = []  # [(fname, raw_dict_or_None, [ThemeIssue, ...]), ...]
        self.validator_cursor = 0
        self.validator_detail_scroll = 0

        if not self.cfg.get('onboarded', True):
            self.mode = 'onboarding'

        self.setup_curses()

    def create_canvas(self):
        """(Re)build the drawing canvas: a window capped at MAX_CANVAS_W x
        MAX_CANVAS_H and centered in the physical terminal. Every draw_* method
        in this class already takes its window as self.stdscr (or reads
        self.stdscr.getmaxyx() directly), so swapping what self.stdscr points
        to is enough to re-scope the entire layout - no other draw code needs
        to change. Below the cap, canvas size == physical size, so nothing
        changes from before."""
        h, w = self.root.getmaxyx()
        canvas_h = min(h, MAX_CANVAS_H)
        canvas_w = min(w, MAX_CANVAS_W)
        y0 = max(0, (h - canvas_h) // 2)
        x0 = max(0, (w - canvas_w) // 2)
        try:
            canvas = curses.newwin(canvas_h, canvas_w, y0, x0)
        except curses.error:
            # Terminal too small/odd for a positioned window of this size -
            # fall back to using the full physical screen directly.
            canvas = curses.newwin(h, w, 0, 0)
        canvas.keypad(True)   # without this, arrow/function keys arrive as raw escape bytes
        canvas.nodelay(1)
        canvas.timeout(100)
        self.stdscr = canvas

    def handle_resize(self):
        """On KEY_RESIZE: clear the old canvas's footprint off the physical
        screen (it won't be overwritten if the new canvas is smaller or moves),
        then rebuild the canvas at the new centered position/size. The new
        canvas is a fresh curses window, so it doesn't have the theme's
        background painted on it yet - apply_theme() needs to run again to
        re-paint it via bkgd()."""
        curses.update_lines_cols()
        self.root.clear()
        self.root.refresh()
        self.create_canvas()
        self.apply_theme()

    def setup_curses(self):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        self.apply_theme()

    def apply_theme(self):
        """(Re)initialize the color-pair slots used throughout the app from the
        active theme. Pair numbers are stable (1=accent, 2=success, 3=warning,
        4=highlight, 5=label, 6=error, 7=text/background, 8=muted, 9=border,
        10=decorative) - every draw call in the app already references these
        by number, so changing what colors THEY point to is all a theme needs
        to do to re-skin the whole UI.

        Semantic naming: a theme can write colors using either the original
        names (accent/label/highlight - kept working forever, existing themes
        use these) or the more self-explanatory semantic names from the
        theme-engine spec (primary/secondary/selection, plus the new
        muted/border/decorative slots). Both resolve to the same pairs; if a
        theme somehow sets both, the semantic name wins since it's the more
        specific/intentional choice for a theme authored against the new
        schema.

        True background theming: curses can't repaint pair 0 (it's reserved
        for the terminal's own default colors), and a color pair's bg of -1
        means "see through to the terminal", not "see through to whatever
        background this app wants". So a theme's background only actually
        shows up if two things happen: (1) plain/unstyled text - which the app
        draws using attr 0, i.e. pair 0 - needs to go through a *different*,
        real pair instead, and (2) any cell nobody explicitly drew on (blank
        space) needs to be painted too. Pair 7 plus window.bkgd() handles both:
        bkgd() makes any cell drawn with attr 0 (which is what "no color"
        collapses to) render using pair 7's colors, and also fills every truly
        blank cell in the window with it."""
        colors = self.theme.get('colors', {})
        max_c = max(0, curses.COLORS - 1)

        def clamp(c):
            return c if c == -1 else max(0, min(c, max_c))

        def resolve(c):
            return clamp(self.resolve_color_component(c))

        def safe_init_pair(i, fg, bg, default_fg=-1, default_bg=-1):
            """Try the theme's actual fg/bg first. If that fails (an
            out-of-range slot for THIS terminal - which can happen even
            after clamp()/resolve_color_component(), since curses.COLORS
            being small enough that even a hardcoded default like
            curses.COLOR_MAGENTA doesn't fit is a real possibility, not
            hypothetical - only discovered by actually testing against a
            genuinely tiny-COLORS terminal), fall back to the role's own
            default. If even THAT fails, fall back to (-1, -1) - "terminal's
            own default colors" - which is guaranteed valid on any curses
            setup that's called use_default_colors() (setup_curses() always
            does), so this tier can't itself fail. Three tries, the last one
            unconditionally safe - never leaves a pair uninitialized."""
            try:
                curses.init_pair(i, fg, bg)
                return
            except (curses.error, ValueError):
                pass
            try:
                curses.init_pair(i, clamp(default_fg) if default_fg != -1 else -1,
                                     clamp(default_bg) if default_bg != -1 else -1)
                return
            except (curses.error, ValueError):
                pass
            try:
                curses.init_pair(i, -1, -1)
            except (curses.error, ValueError):
                pass  # truly nothing left to try - leave this pair whatever it last was rather than raise

        bg = resolve(colors.get('background', -1))
        fg = resolve(colors.get('foreground', -1))

        # (pair index, legacy name, semantic alias, default [fg, bg])
        SLOTS = [
            (1, 'accent',    'primary',    [curses.COLOR_CYAN, -1]),
            (2, 'success',   'success',    [curses.COLOR_GREEN, -1]),
            (3, 'warning',   'warning',    [curses.COLOR_YELLOW, -1]),
            (4, 'highlight', 'selection',  [curses.COLOR_BLACK, curses.COLOR_CYAN]),
            (5, 'label',     'secondary',  [curses.COLOR_MAGENTA, -1]),
            (6, 'error',     'error',      [curses.COLOR_RED, -1]),
            (8, 'muted',     'muted',      [fg, bg]),                          # de-emphasized text; defaults to plain text color until a theme opts in
            (9, 'border',    'border',     [fg, bg]),                          # panel borders/dividers; defaults to plain text color
            (10, 'decorative', 'decorative', colors.get('accent', [curses.COLOR_CYAN, -1])),  # ornamental flourishes; defaults to the accent color
        ]
        for i, legacy_name, semantic_name, default in SLOTS:
            value = colors.get(semantic_name)
            if value is None:
                value = colors.get(legacy_name, default)
            if is_color_component(value):
                # A bare value ("primary = '#58a6ff'") is shorthand for
                # "foreground only, no explicit background override" - the
                # overwhelmingly common case, and the validator has always
                # accepted this shape (it has no way to know a given color
                # key is "one of the paired ones" versus background/
                # foreground, which really are single values), so the
                # runtime needs to accept it too or a theme the validator
                # calls clean can still crash here.
                value = [value, -1]
            try:
                slot_fg, slot_bg = value
            except (TypeError, ValueError):
                # Anything else malformed (wrong-length list, a dict, None,
                # ...) - the validator should already have caught this in
                # a well-formed theme file, but a hand-edited or
                # externally-generated one could still reach here, and a
                # theme-loading crash over one bad color role is a much
                # worse failure mode than quietly using that role's default.
                log_debug(f"Theme color role couldn't be read as [fg, bg] or a single value ({value!r}) - using its default instead.")
                slot_fg, slot_bg = default
            slot_fg = resolve(slot_fg)
            slot_bg = resolve(slot_bg)
            # A slot that hasn't specified its own background (the normal
            # case) inherits the theme's overall background, so e.g. accent-
            # colored text sits on the same canvas as everything else instead
            # of poking through to the terminal's raw default. A slot that
            # *does* specify one (like "selection", whose whole point is a
            # contrasting highlight color) keeps its own explicit choice.
            if slot_bg == -1 and bg != -1:
                slot_bg = bg
            d_fg, d_bg = default
            safe_init_pair(i, slot_fg, slot_bg, d_fg, d_bg)

        safe_init_pair(7, fg, bg)
        try:
            self.stdscr.bkgd(' ', PAIR_TEXT)
        except curses.error:
            pass

    def resolve_color_component(self, value):
        """Turn one raw color value from theme['colors'] into an actual
        curses palette number ready for init_pair(). Plain ints (including
        -1, "terminal default") pass straight through unchanged - a total
        no-op for every theme written before hex colors existed. A hex
        string gets either a freshly-allocated exact-RGB palette slot (if
        this terminal supports curses.can_change_color()) or the closest
        standard-palette match otherwise - see the EXACT COLOR SUPPORT
        block near the top of the file for the full reasoning. Never
        raises: a malformed hex string logs once and resolves to -1
        (terminal default) rather than crashing theme loading over a typo.

        can_change_color() reporting True is NOT trustworthy on its own -
        some terminals advertise the capability via terminfo but silently
        no-op the actual init_color() request, leaving that palette slot
        showing whatever color it already had. The obvious mitigation is to
        verify the request actually landed by reading it back with
        curses.color_content() - but that doesn't work: color_content()
        just returns ncurses's own internal bookkeeping for what init_color()
        was last asked to set, not anything confirmed by the terminal. It
        was empirically checked (not assumed) that as long as init_color()
        doesn't raise, color_content() always reports back exactly the
        requested value, unconditionally - so no readback comparison can
        ever distinguish "the terminal actually redrew this slot" from
        "the terminal silently ignored the escape sequence and ncurses has
        no way to know." An earlier version of this function tried exactly
        that readback check and it never had any teeth.

        Given detection is a dead end, the mitigation here is to hedge
        instead: allocate the *already-closest-matching* standard-palette
        slot for a given hex color, not just the next free slot in
        sequence. On a terminal that genuinely honors init_color(), this
        makes no visual difference at all - the requested RGB gets applied
        either way, pixel-exact. On a terminal that silently ignores it,
        the slot was already the best available approximation before
        redefinition was even attempted, so the failure degrades to "close"
        instead of "some unrelated color" (the original bug: sequential
        allocation starting at slot 16 meant a lying terminal displayed
        whichever swatch happened to sit at 16, 17, 18... - in the standard
        cube, a pure blue ramp, regardless of what was actually requested).

        cfg['exact_color_mode'] is the one true escape hatch, since nothing
        above is verifiable: 'never' skips exact color entirely and always
        uses nearest-match, for a terminal where even the hedge isn't good
        enough. 'always' skips can_change_color() checks and just trusts
        the theme wants exact color. 'auto' (default) is everything above."""
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        rgb = parse_hex_color(value)
        if rgb is None:
            log_debug(f"Theme color value {value!r} isn't a valid palette number or hex color - using terminal default.")
            return -1
        r, g, b = rgb

        exact_mode = self.cfg.get('exact_color_mode', 'auto')
        if exact_mode not in ('auto', 'always', 'never'):
            exact_mode = 'auto'
        if exact_mode == 'never':
            return nearest_256_color(r, g, b)

        if self._can_change_color is None:
            if exact_mode == 'always':
                self._can_change_color = True
            else:
                try:
                    self._can_change_color = bool(curses.can_change_color())
                except Exception:
                    self._can_change_color = False
            log_debug(f"Terminal exact-color support: can_change_color()={self._can_change_color}, COLORS={curses.COLORS}, mode={exact_mode}.")

        if not self._can_change_color:
            return nearest_256_color(r, g, b)

        key = (r, g, b)
        if key in self._custom_color_slots:
            return self._custom_color_slots[key]

        try:
            max_slot = min(curses.COLORS, 256) - 1
        except Exception:
            max_slot = -1

        slot = nearest_256_color(r, g, b, max_slot=max_slot, exclude=self._custom_color_slots.values())
        if slot is not None and 0 <= slot <= max_slot:
            target = (r * 1000 // 255, g * 1000 // 255, b * 1000 // 255)
            try:
                curses.init_color(slot, *target)
                self._custom_color_slots[key] = slot
                return slot
            except (curses.error, ValueError) as e:
                # curses.init_color can raise either depending on
                # platform/ncurses build (a ValueError for an out-of-range
                # slot has been observed even when can_change_color() itself
                # reported True) - caught broadly on purpose so a color that
                # fails to allocate degrades to nearest-match instead of
                # crashing theme loading, which is the whole point of this
                # being a "foolproof" fallback rather than an optimistic one.
                log_debug(f"init_color() failed for #{r:02x}{g:02x}{b:02x} at slot {slot} ({e}) - falling back to nearest match.")
        elif not self._exact_color_warned:
            log_debug("Ran out of usable color slots for exact hex colors - any further hex colors this session fall back to nearest match.")
            self._exact_color_warned = True

        return nearest_256_color(r, g, b, max_slot=max_slot if max_slot >= 0 else None)

    def glyph(self, name, fallback=''):
        """Look up a themed glyph. Most themes just give a plain string and
        that's returned as-is - fully backward compatible. A glyph can
        instead be a small fallback-chain dict, e.g.
        {"nerd": "", "unicode": "🎵", "ascii": "[>]"}, so a theme built
        around Nerd Font icons doesn't turn into Unicode soup - or literal
        mojibake - on a terminal/font that can't render them. Resolution
        walks preferred -> unicode -> ascii from wherever cfg['glyph_mode']
        starts, so a theme only needs to define the tiers it actually cares
        about; anything it skips just falls through to the next one down.
        A *structural* dict like `tag_icons` (tag name -> glyph, not a
        fallback chain) is detected by its keys not looking like tier names,
        and is returned untouched."""
        value = self.theme.get('glyphs', {}).get(name, fallback)
        if isinstance(value, dict) and value and set(value.keys()) <= {'nerd', 'unicode', 'ascii'}:
            mode = self.cfg.get('glyph_mode', 'unicode')
            chain = {
                'nerd': ['nerd', 'unicode', 'ascii'],
                'unicode': ['unicode', 'ascii'],
                'ascii': ['ascii'],
            }.get(mode, ['unicode', 'ascii'])
            for tier in chain:
                if tier in value:
                    return value[tier]
            return fallback
        return value

    def label(self, name, fallback=''):
        """Like glyph(), but for actual UI copy - section headers, field
        labels, status words, the footer hint line. A theme can leave `labels`
        out entirely (as Classic does) and everything falls back to this
        fallback text, so existing themes are unaffected."""
        return self.theme.get('labels', {}).get(name, fallback)

    def resolve_ascii_font(self):
        """The font ascii_title (if enabled) should render with. theme['ascii_font']
        can be:
          - absent -> ASCII_FONTS['block'] (today's only look, unchanged)
          - a string -> looked up in ASCII_FONTS by name; an unknown name
            logs once and falls back to 'block' rather than crashing a
            theme over a typo
          - a table -> {"char_width": int, "char_height": int, "glyphs": {...}},
            a theme's own fully custom font, used as-is (validated ahead of
            time by validate_theme_dict() for anyone loading from a .toml
            file, but this resolver stays defensive regardless - a
            structurally broken custom font falls back to 'block' instead
            of throwing mid-render)
        Every font, builtin or custom, is expected to carry its own
        char_width/char_height and a glyphs dict - nothing downstream
        (render_ascii_word, station_list_start_row, draw()) assumes 3x5
        anymore; they all read these off whichever font comes back here."""
        value = self.theme.get('ascii_font')
        if value is None:
            return ASCII_FONTS['block']
        if isinstance(value, str):
            font = ASCII_FONTS.get(value)
            if font is None:
                log_debug(f"Theme sets ascii_font='{value}', which isn't a known font - falling back to 'block'.")
                return ASCII_FONTS['block']
            return font
        if isinstance(value, dict):
            glyphs = value.get('glyphs')
            height = value.get('char_height')
            if isinstance(glyphs, dict) and glyphs and isinstance(height, int) and height > 0:
                return {'char_width': value.get('char_width', 0), 'char_height': height, 'glyphs': glyphs}
            log_debug("Theme's custom ascii_font table is missing/malformed char_height or glyphs - falling back to 'block'.")
            return ASCII_FONTS['block']
        log_debug(f"Theme's ascii_font is a {type(value).__name__}, expected a font name or a custom font table - falling back to 'block'.")
        return ASCII_FONTS['block']

    def draw_shaded_ascii_row(self, y, x, row, max_width):
        """Draw one row of a render_ascii_word_raw() banner with real
        two-tone color instead of one flat color for the whole line: '█'
        runs (a glyph's main ink) get the theme's label color, '▓' runs (a
        glyph's own second tone - the way 'N'/'Q' in the 'block' font
        already use it for a bit of shading) get the theme's decorative
        color, and everything else (background/letter-gaps) is left alone -
        the screen was already erased this frame, nothing to paint there.
        Consecutive same-tier characters are drawn in one call each rather
        than character-by-character, so this costs one or two addstr calls
        per row in practice, not one per glyph column."""
        row = row[:max_width]
        i = 0
        n = len(row)
        while i < n:
            ch = row[i]
            j = i
            while j < n and row[j] == ch:
                j += 1
            if ch == '█':
                self.safe_addstr(self.stdscr, y, x + i, row[i:j], PAIR_LABEL | curses.A_BOLD)
            elif ch == '▓':
                self.safe_addstr(self.stdscr, y, x + i, row[i:j].replace('▓', '█'), PAIR_DECORATIVE | curses.A_BOLD)
            i = j

    DENSITY_LEVELS = ('compact', 'normal', 'spacious')

    def density(self):
        """Resolves to 'compact' | 'normal' | 'spacious'. cfg['density'] is an
        explicit user override (persists across themes); if the user hasn't
        set one, falls back to the active theme's own preferred density; if
        neither says anything, 'normal'. Layout code should treat this as a
        breathing-room preference only - it must never be the reason content
        gets clipped, since the responsive terminal-size fitting already in
        draw() takes priority over any aesthetic preference."""
        override = self.cfg.get('density')
        if override in self.DENSITY_LEVELS:
            return override
        theme_pref = self.theme.get('density')
        if theme_pref in self.DENSITY_LEVELS:
            return theme_pref
        return 'normal'

    def cycle_density(self):
        current = self.density()
        idx = self.DENSITY_LEVELS.index(current) if current in self.DENSITY_LEVELS else 1
        next_level = self.DENSITY_LEVELS[(idx + 1) % len(self.DENSITY_LEVELS)]
        self.cfg['density'] = next_level
        self.config_mgr.save()
        self.show_toast(f"Density: {next_level.capitalize()}")
        log_debug(f"Density set to '{next_level}'.")

    DIALOG_PADDING_BY_DENSITY = {'compact': 0, 'normal': 1, 'spacious': 2}

    def dialog_padding(self):
        """Extra rows/cols of breathing room inside every dialog box, driven
        by density() so it's one lever instead of a separate theme key.
        'compact' -> 0 (today's exact zero-padding look, unchanged).
        'normal' -> 1, 'spacious' -> 2. Every draw_box() caller grows its
        box_h/box_w by 2x this value and shifts its content start by this
        value, so the box always grows in lockstep with the padding it's
        asked to contain - never clips, never stretches the box without
        also making room inside it."""
        return self.DIALOG_PADDING_BY_DENSITY.get(self.density(), 1)

    def set_theme(self, name):
        self.theme = resolve_theme(name, self.theme_registry)
        self.cfg['theme'] = name
        self.apply_theme()
        self.config_mgr.save()

    def safe_addstr(self, win, y, x, text, color=0):
        max_y, max_x = win.getmaxyx()
        if 0 <= y < max_y and 0 <= x < max_x:
            win.addstr(y, x, text[:max_x - x - 1], color)

    def clip_text(self, text, width):
        """Fit `text` into an internal column exactly `width` cells wide.
        safe_addstr only protects the *outer* window edge - anything drawn
        into a narrower internal column (like the station list, bounded by
        the pane divider rather than the screen edge) will happily bleed
        straight through that divider into whatever's drawn next to it if
        it's not shortened first. Long text gets a trailing ellipsis; short
        text is returned unchanged (padding, if wanted, is the caller's job)."""
        if width <= 0:
            return ""
        if len(text) <= width:
            return text
        if width == 1:
            return "…"
        return text[:width - 1] + "…"

    def draw_hline(self, y, x, ch, n):
        """Draw a horizontal line of a custom (non-ACS) character. curses'
        native hline() only handles the built-in curses.ACS_* line-drawing
        constants correctly; fed an arbitrary Unicode character it silently
        truncates to the low byte (e.g. '═' U+2550 becomes 'P'). addstr with a
        repeated string doesn't have that problem."""
        try:
            self.stdscr.addstr(y, x, ch * n)
        except curses.error:
            pass

    def draw_vline(self, y, x, ch, n):
        """Vertical-line counterpart to draw_hline, for the same reason:
        curses' native vline() has the identical truncation bug for anything
        that isn't a curses.ACS_* constant."""
        try:
            for i in range(n):
                self.stdscr.addch(y + i, x, ch)
        except curses.error:
            pass

    def show_toast(self, msg, seconds=3):
        self.toast_msg = msg
        self.toast_until = time.time() + seconds
        log_debug(f"TOAST: {msg}")

    def get_playback_status(self):
        """Single source of truth for the status dot + label shown in both the
        header and the Now Playing tab, so the two can't drift out of sync.
        Driven entirely by self.mpv.playback_state, which is IPC-confirmed by
        mpv's own events (see MPVRemote._handle_ipc_message) - not by whether
        we merely *sent* a play command. That's the actual fix for the false
        "Streaming" status: previously this checked a hardcoded status_msg
        string that was set the instant play_selected() fired, regardless of
        whether mpv succeeded."""
        if not self.mpv.mpv_available:
            return (self.glyph('status_error', '✕'), PAIR_ERROR, self.label('status_word_unavailable', 'Unavailable'))

        state = self.mpv.playback_state

        if state == 'error':
            return (self.glyph('status_error', '✕'), PAIR_ERROR, self.label('status_word_error', 'Stream Unavailable'))

        if state == 'resolving':
            spinner = self.glyph('spinner', '◐◓◑◒')
            frame = spinner[int(time.time() * 6) % len(spinner)]
            return (frame, PAIR_WARNING, self.label('status_word_resolving', 'Resolving…'))

        if self.is_paused:
            return (self.glyph('status_paused', '●'), PAIR_WARNING, self.label('status_word_paused', 'Paused'))

        if state == 'playing':
            return (self.glyph('status_playing', '●'), PAIR_SUCCESS, self.label('status_word_playing', 'Streaming'))

        return (self.glyph('status_idle', '○'), PAIR_DEFAULT, self.status_msg or self.label('status_word_idle', 'Idle'))

    def get_icon_for_slug(self, slug):
        station = next((s for s in self.stations if s['slug'] == slug), None)
        return self.get_station_icon(station) if station else self.glyph('default_tag_icon', '♫')

    def get_icon_for_name(self, name):
        station = next((s for s in self.stations if s['name'] == name), None)
        return self.get_station_icon(station) if station else self.glyph('default_tag_icon', '♫')

    NOW_PLAYING_STYLES = ('dense', 'minimal')

    def now_playing_style(self):
        style = self.theme.get('now_playing_style')
        return style if style in self.NOW_PLAYING_STYLES else 'dense'

    SELECTION_STYLES = ('block', 'marker')

    def selection_style(self):
        """'block' (default, unchanged): the selected row gets a full-width
        highlight bar via PAIR_SELECTION, same as always. 'marker': no block,
        instead a glyph prefix (theme glyph 'selection_marker', default ▶)
        on the selected row only, with PAIR_SELECTION coloring just the text.
        Non-selected rows get matching blank-space padding so names still
        line up in either style."""
        style = self.theme.get('selection_style')
        return style if style in self.SELECTION_STYLES else 'block'

    TAB_STYLES = ('numbered', 'underlined')

    def tab_style(self):
        """'numbered' (default, unchanged): [1]Now Playing [2]History [3]Stats,
        active tab gets a full highlight block. 'underlined': the bracket
        numbers are dropped (the footer's [1-3] hint still covers the
        shortcut) and the active tab is marked with underline + accent color
        instead of a block, for a quieter look."""
        style = self.theme.get('tab_style')
        return style if style in self.TAB_STYLES else 'numbered'

    SECTION_HEADER_STYLES = ('plain', 'marker')

    def section_header_style(self):
        style = self.theme.get('section_header_style')
        return style if style in self.SECTION_HEADER_STYLES else 'plain'

    def draw_section_header(self, y, x, text, avail_width):
        """Centralized rendering for the app's internal section headers
        (Context, Recent Sessions, Session Summary, Listening Time, Most
        Played) so a theme's choice applies everywhere at once instead of
        each call site deciding for itself. 'plain': bold label text,
        unchanged from before. 'marker': same text prefixed with a glyph
        (theme glyph 'section_marker', default ◆) - adds visual weight
        without spending an extra row, unlike an underline rule would."""
        if self.section_header_style() == 'marker':
            marker = self.glyph('section_marker', '◆')
            text = f"{marker} {text}"
        self.safe_addstr(self.stdscr, y, x, self.clip_text(text, avail_width), PAIR_LABEL | curses.A_BOLD)

    METADATA_STYLES = ('aligned', 'inline')

    def metadata_style(self):
        """Controls the Context pane's field layout specifically (the other
        metadata-shaped displays - Session Summary, Stats - keep their
        existing aligned layout for now; extending this to them is a
        possible future increment, not done here to keep this one
        contained). 'aligned' (default, unchanged): 7 separate 'Label :
        value' rows. 'inline': the same information condensed into 3
        combined lines with no label prefixes - a genuinely different, more
        compact presentation, not just re-wrapped text."""
        style = self.theme.get('metadata_style')
        return style if style in self.METADATA_STYLES else 'aligned'

    EMPTY_STATE_STYLES = ('plain', 'decorative')

    def empty_state_style(self):
        style = self.theme.get('empty_state_style')
        return style if style in self.EMPTY_STATE_STYLES else 'plain'

    def draw_empty_state(self, y, x0, width, message):
        """Centralized rendering for the app's various 'nothing here' states
        (empty station list, empty folder, no search results, no history, no
        stats yet, no station selected) so a theme's choice applies
        everywhere at once. 'plain' (default, unchanged): centered message
        text only. 'decorative': the message wrapped in a small flourish
        using the theme's decorative glyph (default ♫), e.g.
        '── ♫ No results ♫ ──' - matching the design note that decoration
        should disappear before information does: this never hides or
        shortens the message, it only adds ornament around it."""
        if self.empty_state_style() == 'decorative':
            deco = self.glyph('empty_state_deco', '♫')
            message = f"── {deco} {message} {deco} ──"
        clipped = self.clip_text(message, max(0, width - 2))
        x = x0 + max(0, (width - len(clipped)) // 2)
        self.safe_addstr(self.stdscr, y, x, clipped, PAIR_MUTED)

    def compute_now_playing_layout(self, right_w, compact=False):
        """The exact layout draw_now_playing_tab uses - what row its info
        block starts on, and the list of (text, style) rows it needs - shared
        so draw() can measure how much vertical room this tab *actually*
        wants (idle state needs much less than a playing state with sleep
        timer + mpv warning both showing) instead of always reserving a fixed
        share of the screen for it regardless of content.

        `compact=True` strips everything here that's decoration rather than
        data - the idle-state ASCII art and the blank spacer lines - so that
        on a genuinely small terminal, *those* get dropped before any actual
        field (Mode, Volume, Tags...) does. Dropping decoration first and
        data last is the whole fix; the previous version measured content
        height but still included the decorative rows in that measurement,
        so a tight terminal ended up truncating real fields while blank
        padding and idle art were still eating rows above them.

        This is the 'dense' now_playing_style - the full metadata table.
        See compute_now_playing_layout_minimal for the 'minimal' alternative."""
        if self.current_station:
            if compact:
                art_y = 2
                info_y = art_y + 2  # icon row + name row, no blank gap
            else:
                art_y = 3
                info_y = art_y + 4
        else:
            if compact:
                art_y = 2  # idle art skipped entirely - it's pure decoration
                info_y = art_y
            else:
                art_y = 2 + len(self.theme.get('idle_art', ASCII_ART))
                info_y = art_y + 2

        rows = []
        if self.current_station:
            rows.append((f"{self.label('lbl_channel', 'Channel')} : {self.current_station['channel']}", PAIR_LABEL | curses.A_BOLD))
            rows.append((f"{self.label('lbl_tags', 'Tags')}    : {', '.join(self.current_station['tags'])}", 0))
            if self.current_history_entry:
                started_str = time.strftime('%H:%M', time.localtime(self.current_history_entry['started_ts']))
                elapsed = time.time() - self.current_history_entry['started_ts']
                rows.append((f"{self.label('lbl_started', 'Started')} : {started_str}  ·  {self.label('lbl_listening', 'Listening')} {self.format_duration(elapsed)}", 0))
        else:
            rows.append((self.label('now_playing_none', 'Now Playing : None'), PAIR_WARNING))

        if not compact:
            rows.append((None, None))  # blank line
        dot, dot_color, status_label = self.get_playback_status()
        rows.append((f"{self.label('lbl_status', 'Status')}  : {dot} {status_label}", dot_color | curses.A_BOLD))
        hud_active = bool(self.volume_hud_until and time.time() < self.volume_hud_until)
        if hud_active:
            if not compact:
                rows.append((None, None))
        else:
            vol_bar_fill = self.cfg['volume'] // 5
            fill_ch, empty_ch = self.glyph('volume_fill', '#'), self.glyph('volume_empty', '-')
            vol_bar = f"[{fill_ch * vol_bar_fill}{empty_ch * (20 - vol_bar_fill)}] {self.cfg['volume']}%"
            rows.append((f"{self.label('lbl_volume', 'Volume')}  : {vol_bar}", 0))

        if self.mpv.playback_state == 'error' and self.mpv.last_error:
            if not compact:
                rows.append((None, None))
            rows.append((f"{self.label('stream_error', '⚠ Stream Error')} : {self.mpv.last_error}", PAIR_ERROR | curses.A_BOLD))

        if not self.mpv.mpv_available:
            if not compact:
                rows.append((None, None))
            rows.append((self.label('mpv_unavailable', '⚠ mpv not found in PATH - install mpv to enable playback'), PAIR_ERROR | curses.A_BOLD))

        if self.sleep_timer_end:
            rem = int(self.sleep_timer_end - time.time())
            mins, secs = divmod(rem, 60)
            if not compact:
                rows.append((None, None))
            rows.append((f"{self.label('lbl_sleep_timer', 'Sleep Timer')} : {mins:02d}:{secs:02d}", PAIR_WARNING))

        return art_y, info_y, rows

    def compute_now_playing_layout_minimal(self, right_w, compact=False):
        """'minimal' now_playing_style: just the station name/icon and status
        - no metadata table, no idle art. The metadata this drops (channel,
        tags, played-time stats) isn't lost, it's one glance down in the
        Context pane for whatever's highlighted - so minimal themes trade a
        quick glance for a much quieter Now Playing tab, not for missing
        information. Genuine alerts (stream error, mpv missing, sleep timer)
        still show, since those are functional, not decorative.

        Same (art_y, info_y, rows) shape as compute_now_playing_layout so
        both styles are interchangeable to their callers - here `rows` holds
        already-centered (text, style) lines rather than 'Label : value'
        fields."""
        art_y = 2
        info_y = art_y + (1 if compact else 2)

        rows = []
        if self.current_station:
            rows.append((self.current_station['name'], PAIR_SUCCESS | curses.A_BOLD))
        else:
            rows.append((self.label('now_playing_none', 'Now Playing: None'), PAIR_WARNING))

        if not compact:
            rows.append((None, None))
        dot, dot_color, status_label = self.get_playback_status()
        rows.append((f"{dot} {status_label.upper()}", dot_color | curses.A_BOLD))

        if self.mpv.playback_state == 'error' and self.mpv.last_error:
            if not compact:
                rows.append((None, None))
            rows.append((f"{self.label('stream_error', '⚠ Stream Error')}: {self.mpv.last_error}", PAIR_ERROR | curses.A_BOLD))

        if not self.mpv.mpv_available:
            if not compact:
                rows.append((None, None))
            rows.append((self.label('mpv_unavailable', '⚠ mpv not found in PATH'), PAIR_ERROR | curses.A_BOLD))

        if self.sleep_timer_end:
            rem = int(self.sleep_timer_end - time.time())
            mins, secs = divmod(rem, 60)
            if not compact:
                rows.append((None, None))
            rows.append((f"{self.label('lbl_sleep_timer', 'Sleep Timer')}: {mins:02d}:{secs:02d}", PAIR_WARNING))

        return art_y, info_y, rows

    def now_playing_content_height(self, right_w, compact=False):
        """The last absolute row the Now Playing tab actually needs to draw
        into right now - not how many rows it's been given. Used to size the
        top/bottom split around real content instead of a fixed percentage.
        Dispatches on now_playing_style() so the sizing algorithm in draw()
        never has to know which style is active."""
        if self.now_playing_style() == 'minimal':
            _, info_y, rows = self.compute_now_playing_layout_minimal(right_w, compact=compact)
        else:
            _, info_y, rows = self.compute_now_playing_layout(right_w, compact=compact)
        return info_y + len(rows) - 1

    def draw_now_playing_tab(self, left_w, right_w, max_row, compact=False):
        if self.now_playing_style() == 'minimal':
            self.draw_now_playing_tab_minimal(left_w, right_w, max_row, compact=compact)
            return

        art_y, info_y, rows = self.compute_now_playing_layout(right_w, compact=compact)
        if self.current_station:
            icon = self.get_station_icon(self.current_station)
            icon_row = 2 if compact else 3
            self.safe_addstr(self.stdscr, icon_row, left_w + (right_w - 2) // 2, icon, PAIR_ACCENT)
            name_line = self.current_station['name']
            name_row = 3 if compact else 5
            self.safe_addstr(self.stdscr, name_row, left_w + max(2, (right_w - len(name_line)) // 2), name_line, PAIR_SUCCESS | curses.A_BOLD)
        elif not compact:
            y = 2
            for line in self.theme.get('idle_art', ASCII_ART):
                if y > max_row:
                    break
                self.safe_addstr(self.stdscr, y, left_w + (right_w - len(line)) // 2, line, PAIR_ACCENT)
                y += 1

        y = info_y
        row_avail = max(0, right_w - 5)
        for text, style in rows:
            if y > max_row:
                break
            if text is not None:
                self.safe_addstr(self.stdscr, y, left_w + 4, self.clip_text(text, row_avail), style)
            y += 1

    def draw_now_playing_tab_minimal(self, left_w, right_w, max_row, compact=False):
        art_y, info_y, rows = self.compute_now_playing_layout_minimal(right_w, compact=compact)
        if self.current_station and art_y <= max_row:
            icon = self.get_station_icon(self.current_station)
            self.safe_addstr(self.stdscr, art_y, left_w + (right_w - len(icon)) // 2, icon, PAIR_ACCENT)

        y = info_y
        row_avail = max(0, right_w - 4)
        for text, style in rows:
            if y > max_row:
                break
            if text is not None:
                clipped = self.clip_text(text, row_avail)
                x = left_w + max(2, (right_w - len(clipped)) // 2)
                self.safe_addstr(self.stdscr, y, x, clipped, style)
            y += 1

    def draw_history_tab(self, left_w, right_w, max_row):
        y = 3
        self.draw_section_header(y, left_w + 2, self.label('recent_sessions', 'Recent Sessions'), right_w - 3)
        y += 2
        if not self.history:
            self.draw_empty_state(y, left_w + 2, right_w - 3, self.label('no_history', '(nothing played yet)'))
            return

        now = time.time()
        SUMMARY_ROWS = 7  # separator + title + up to 4 stat lines + breathing room
        max_rows = max(0, max_row - y - SUMMARY_ROWS)
        recent = list(reversed(self.history[-max_rows:])) if max_rows > 0 else []
        row_avail = max(0, right_w - 3)
        for entry in recent:
            ended = entry.get('ended_ts') or now
            dur = ended - entry['started_ts']
            tag = " (ongoing)" if entry.get('ended_ts') is None else ""
            icon = self.get_icon_for_slug(entry.get('slug'))
            line = f"{icon} {entry['name']} - {self.format_duration(dur)}{tag}"
            style = PAIR_SUCCESS if entry.get('ended_ts') is None else PAIR_DEFAULT
            self.safe_addstr(self.stdscr, y, left_w + 2, self.clip_text(line, row_avail), style)
            y += 1

        # Fill the remaining space with a summary instead of leaving it blank.
        if y + 6 > max_row:
            return
        y += 1
        self.draw_hline(y, left_w + 2, '─', max(0, right_w - 4))
        y += 2

        total_sessions = len(self.history)
        total_time = sum((e.get('ended_ts') or now) - e['started_ts'] for e in self.history)
        avg_time = total_time / total_sessions if total_sessions else 0
        longest = max(self.history, key=lambda e: (e.get('ended_ts') or now) - e['started_ts'])
        longest_dur = (longest.get('ended_ts') or now) - longest['started_ts']
        longest_name = self.clip_text(longest['name'], max(0, right_w - 24))

        self.draw_section_header(y, left_w + 2, self.label('session_summary', 'Session Summary'), right_w - 3)
        y += 2
        summary_rows = [
            f"{self.label('lbl_total_sessions', 'Total Sessions')} : {total_sessions}",
            f"{self.label('lbl_total_time', 'Total Time')}     : {self.format_duration(total_time)}",
            f"{self.label('lbl_avg_session', 'Avg Session')}    : {self.format_duration(avg_time)}",
            f"{self.label('lbl_longest', 'Longest')}        : {longest_name} ({self.format_duration(longest_dur)})",
        ]
        row_avail = max(0, right_w - 5)
        for line in summary_rows:
            if y > max_row:
                break
            self.safe_addstr(self.stdscr, y, left_w + 4, self.clip_text(line, row_avail))
            y += 1

    def draw_stats_tab(self, left_w, right_w, max_row):
        today, total, top = self.compute_stats()
        y = 3
        row_avail = max(0, right_w - 5)
        self.draw_section_header(y, left_w + 2, self.label('listening_time', 'Listening Time'), row_avail)
        y += 2
        self.safe_addstr(self.stdscr, y, left_w + 4, self.clip_text(f"{self.label('lbl_today', 'Today')}    : {self.format_duration(today)}", row_avail))
        y += 1
        self.safe_addstr(self.stdscr, y, left_w + 4, self.clip_text(f"{self.label('lbl_all_time', 'All Time')} : {self.format_duration(total)}", row_avail))
        y += 3
        if y > max_row:
            return
        self.draw_section_header(y, left_w + 2, self.label('most_played', 'Most Played'), row_avail)
        y += 2
        if not top:
            if y <= max_row:
                self.draw_empty_state(y, left_w + 2, right_w - 3, self.label('no_stats_data', '(no data yet)'))
            return
        for name, secs in top:
            if y > max_row:
                break
            icon = self.get_icon_for_name(name)
            line = f"{icon} {name} - {self.format_duration(secs)}"
            self.safe_addstr(self.stdscr, y, left_w + 4, self.clip_text(line, row_avail))
            y += 1

    def format_relative_time(self, ts):
        diff = time.time() - ts
        if diff < 60:
            return "just now"
        if diff < 3600:
            return f"{int(diff // 60)}m ago"
        if diff < 86400:
            return f"{int(diff // 3600)}h ago"
        return f"{int(diff // 86400)}d ago"

    def get_station_history_stats(self, slug):
        now = time.time()
        entries = [e for e in self.history if e.get('slug') == slug]
        count = len(entries)
        total = sum((e.get('ended_ts') or now) - e['started_ts'] for e in entries)
        last_ts = max((e.get('ended_ts') or e['started_ts']) for e in entries) if entries else None
        return count, total, last_ts

    def context_pane_content_height(self, compact=False):
        """Rows the Context pane needs for its fields (or the short 'no
        station selected' message) - same idea as now_playing_content_height,
        used to size the split around real content instead of a fixed
        percentage. Field count depends on metadata_style(): 7 for 'aligned',
        3 for 'inline'."""
        if not self.filtered_stations:
            return 3  # header + blank + message
        field_rows = 3 if self.metadata_style() == 'inline' else 7
        return (1 if compact else 4) + field_rows

    def draw_context_pane(self, left_w, right_w, y0, max_row, compact=False):
        if y0 > max_row:
            return
        station = self.filtered_stations[self.selected_idx] if self.filtered_stations else None
        row_avail = max(0, right_w - 5)

        if compact and station:
            # Combine "Context" + station name onto one line instead of
            # header, blank, name, blank (4 rows of which 2 are just
            # spacing) - the whole point of compact mode is that blank
            # padding goes before any real field does.
            icon = self.get_station_icon(station)
            header = f"{self.label('context_header', 'Context')}: {icon} {station['name']}"
            self.draw_section_header(y0, left_w + 2, header, right_w - 3)
            y = y0 + 1
        else:
            self.draw_section_header(y0, left_w + 2, self.label('context_header', 'Context'), right_w - 3)
            y = y0 + 2
            if not station or y > max_row:
                if y <= max_row:
                    self.draw_empty_state(y, left_w + 2, right_w - 3, self.label('no_station_selected', '(no station selected)'))
                return
            icon = self.get_station_icon(station)
            header = f"{icon} {station['name']}"
            self.safe_addstr(self.stdscr, y, left_w + 4, self.clip_text(header, row_avail), PAIR_SUCCESS | curses.A_BOLD)
            y += 2

        if not station or y > max_row:
            return

        member_folders = sorted(fname for fname, slugs in self.folders.items() if station['slug'] in slugs)
        folder_str = ", ".join(member_folders) if member_folders else "(none)"
        is_fav = station['slug'] in self.cfg['favorites']
        count, total, last_ts = self.get_station_history_stats(station['slug'])

        if self.metadata_style() == 'inline':
            # Same information as 'aligned' below, condensed into 3 combined
            # lines with no label prefixes - a genuinely different, more
            # compact presentation rather than just re-wrapped text.
            tags_str = ', '.join(station['tags'])
            line1 = f"{station['channel']} · {tags_str}" if tags_str else station['channel']
            fav_bit = f" · {self.glyph('favorite', '★')} {self.label('lbl_favorite', 'Favorite')}" if is_fav else ""
            line2 = f"{self.label('lbl_folders', 'Folders')}: {folder_str}{fav_bit}"
            if count:
                played_bit = f"{self.label('lbl_played', 'Played')} {count}× · {self.format_duration(total)}"
                last_bit = f" · {self.format_relative_time(last_ts)}" if last_ts else ""
            else:
                played_bit = self.label('no_stats_data', '(not played yet)')
                last_bit = ""
            line3 = f"{played_bit}{last_bit}"
            rows = [line1, line2, line3]
        else:
            rows = [
                f"{self.label('lbl_channel', 'Channel')}     : {station['channel']}",
                f"{self.label('lbl_folders', 'Folders')}     : {folder_str}",
                f"{self.label('lbl_tags', 'Tags')}        : {', '.join(station['tags'])}",
                f"{self.label('lbl_favorite', 'Favorite')}    : {'★ Yes' if is_fav else 'No'}",
                f"{self.label('lbl_played', 'Played')}      : {count} time{'s' if count != 1 else ''}",
                f"{self.label('lbl_total_time', 'Total Time')}  : {self.format_duration(total) if count else '-'}",
                f"{self.label('lbl_last_played', 'Last Played')} : {self.format_relative_time(last_ts) if last_ts else 'Never'}",
            ]
        for line in rows:
            if y > max_row:
                break
            self.safe_addstr(self.stdscr, y, left_w + 4, self.clip_text(line, row_avail))
            y += 1

    def station_list_start_row(self):
        """Row the station list starts on - normally right after the 1-line
        pane title (row 3, matching the app's original layout), but pushed
        down to make room when the active theme renders that title as a
        multi-row ASCII banner instead. Shared by draw() and adjust_scroll()
        so the two can't drift out of sync about how many rows are visible.

        Density then nudges that by +-1: 'compact' reclaims a row for the
        list, 'spacious' adds one extra blank row of breathing room under the
        title. Clamped to a floor of 2 so a compact ASCII-title theme can't
        push the list up into the title banner itself."""
        if not self.theme.get('ascii_title', False):
            base = 3
        else:
            row = 1 + self.resolve_ascii_font()['char_height']
            if self.current_folder and self.current_folder != "All":
                row += 1  # the "· FolderName" qualifier line under the banner
            base = row + 1  # one blank breathing-room row before the list

        density_offset = {'compact': -1, 'normal': 0, 'spacious': 1}[self.density()]
        return max(2, base + density_offset)

    def get_footer_controls(self, avail_width):
        """Pick the widest footer-hint tier that actually fits, so a narrow
        terminal sheds the least-essential hints first instead of just
        getting cut off mid-command and silently losing [?]Help / [q]Quit -
        which is exactly what plain truncation was doing before this."""
        tiers = [
            self.label('footer_controls', "[Enter]Play/Pause [1-3]View [a]Add [e]Edit [x]Del [o]Folder [O]Manage [m]Menu [f/F]Favs [s]Search [?]Help [q]Quit"),
            self.label('footer_controls_medium', "[Enter]Play/Pause [a/e/x]Add/Edit/Del [o/O]Folders [m]Menu [f/F]Favs [?]Help [q]Quit"),
            self.label('footer_controls_compact', "[Enter]Play/Pause [m]Menu [?]Help [q]Quit"),
        ]
        for tier in tiers:
            if len(tier) <= avail_width:
                return tier
        return self.clip_text(tiers[-1], avail_width)

    def draw(self):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        if h < 15 or w < 60:
            self.stdscr.addstr(0, 0, "Terminal too small!")
            self.stdscr.refresh()
            return

        left_w = w // 3
        right_w = w - left_w
        b = self.theme['_border_chars']

        self.draw_vline(1, left_w, b['v'], h - 2)
        self.draw_vline(1, 0, b['v'], h - 2)
        self.draw_vline(1, w - 1, b['v'], h - 2)

        # Top border, with the title and a live status indicator embedded in it.
        self.draw_hline(0, 0, b['h'], w)
        try:
            self.stdscr.addch(0, left_w, b['t_down'])
        except curses.error:
            pass

        header_text = f" {self.glyph('app_icon', '🎵 Lofi Stream CLI')} "
        self.safe_addstr(self.stdscr, 0, (w - len(header_text)) // 2, header_text, PAIR_ACCENT | curses.A_BOLD)

        dot, dot_color, status_label = self.get_playback_status()
        status_text = f" {dot} {status_label.upper()} "
        self.safe_addstr(self.stdscr, 0, max(0, w - len(status_text) - 2), status_text, dot_color | curses.A_BOLD)

        try:
            self.stdscr.addch(0, 0, b['tl'])
            self.stdscr.addch(0, w - 1, b['tr'])
        except curses.error:
            pass

        title_word = self.label('title_favorites', 'Favorites') if self.show_favorites_only else self.label('title_stations', 'Stations')
        list_start_row = self.station_list_start_row()
        banner_avail = max(0, left_w - 3)
        if self.theme.get('ascii_title', False):
            font = self.resolve_ascii_font()
            banner_lines = render_ascii_word_raw(title_word, font=font)
            for i, line in enumerate(banner_lines):
                self.draw_shaded_ascii_row(1 + i, 2, line, banner_avail)
            if self.current_folder and self.current_folder != "All":
                self.safe_addstr(self.stdscr, 1 + font['char_height'], 2, self.clip_text(f"· {self.current_folder}", banner_avail), PAIR_LABEL | curses.A_BOLD)
        else:
            title_bits = [title_word]
            if self.current_folder and self.current_folder != "All":
                title_bits.append(f"· {self.current_folder}")
            title = self.clip_text(" " + " ".join(title_bits) + " ", banner_avail + 1)
            self.safe_addstr(self.stdscr, 1, 2, title, PAIR_LABEL | curses.A_BOLD)

        max_display = h - 2 - list_start_row
        if not self.filtered_stations:
            if self.search_query:
                base = self.label('no_search_results', 'No results')
                message = f'{base} for "{self.search_query}"'
            elif self.current_folder and self.current_folder != "All":
                message = self.label('empty_folder', 'This folder is empty')
            else:
                message = self.label('no_stations', 'No stations yet')
            if max_display > 0:
                self.draw_empty_state(list_start_row + max_display // 2, 1, left_w - 2, message)
            return
        sel_style = self.selection_style()
        marker = self.glyph('selection_marker', '▶') if sel_style == 'marker' else None
        for i in range(max_display):
            idx = self.scroll_offset + i
            if idx >= len(self.filtered_stations):
                break

            station = self.filtered_stations[idx]
            is_fav = self.glyph('favorite', '★') if station['slug'] in self.cfg['favorites'] else " "
            is_now_playing = bool(self.current_station and station['slug'] == self.current_station['slug'])
            is_selected = idx == self.selected_idx

            display_name = f"{is_fav} {station['name']}"
            if marker is not None:
                display_name = (f"{marker} " if is_selected else "  ") + display_name

            if is_selected:
                if sel_style == 'marker':
                    style = PAIR_SELECTION | curses.A_BOLD
                else:
                    style = PAIR_SELECTION | (curses.A_BOLD if is_now_playing else 0)
            elif is_now_playing:
                pulse_on = self.is_playing and self.theme.get('pulse', True) and (int(time.time() * 2) % 2 == 0)
                style = PAIR_SUCCESS | (curses.A_BOLD if pulse_on else 0)
            else:
                style = PAIR_DEFAULT
            padded_name = self.clip_text(display_name, left_w - 2).ljust(left_w - 2)
            self.safe_addstr(self.stdscr, list_start_row + i, 1, padded_name, style)

        # --- RIGHT PANE ---
        if self.show_debug:
            self.safe_addstr(self.stdscr, 1, left_w + 2, self.label('debug_header', '=== LIVE DEBUG LOGS ==='), PAIR_WARNING | curses.A_BOLD)
            # The debug overlay is independent of the left pane's title height -
            # it always starts right under its own header, 2 rows down.
            debug_max_display = h - 5
            display_logs = DEBUG_LOGS[-debug_max_display:]
            for i, log_str in enumerate(display_logs):
                is_flagged = any(kw in log_str.upper() for kw in ("CRITICAL", "ERROR", "EXCEPTION", "MPV-ERR", "WARN"))
                color = PAIR_ERROR if is_flagged else PAIR_DEFAULT
                self.safe_addstr(self.stdscr, 3 + i, left_w + 2, log_str, color)
        else:
            tabs = [
                (1, self.label('tab_now_playing', 'Now Playing')),
                (2, self.label('tab_history', 'History')),
                (3, self.label('tab_stats', 'Stats')),
            ]
            tstyle = self.tab_style()
            tx = left_w + 2
            for num, label in tabs:
                active = self.workspace_tab == num
                if tstyle == 'underlined':
                    text = f" {label} "
                    style = (PAIR_ACCENT | curses.A_BOLD | curses.A_UNDERLINE) if active else PAIR_DEFAULT
                else:
                    text = f"[{num}]{label} "
                    style = (PAIR_SELECTION | curses.A_BOLD) if active else PAIR_DEFAULT
                self.safe_addstr(self.stdscr, 1, tx, text, style)
                tx += len(text) + 1

            # Split the right pane: top = workspace tabs, bottom = Context
            # (details of whatever's *highlighted*, which may differ from what's playing).
            top_start = 2
            bottom_limit = h - 3  # last row above the footer separator
            usable_span = bottom_limit - top_start + 1
            DIVIDER_ROWS = 1

            if self.workspace_tab == 1:
                # Try progressively less spacious combinations until one fits:
                # both spacious (nicest) -> Now Playing spacious/Context
                # compact -> both compact (no data lost, just less breathing
                # room) -> give up and let the existing per-row truncation
                # handle it. Deciding each section's compactness
                # independently means a mid-sized terminal doesn't get stuck
                # looking cramped just because the *combination* of both
                # sections' full layouts didn't fit.
                n_full = self.now_playing_content_height(right_w) - top_start + 1
                n_compact = self.now_playing_content_height(right_w, compact=True) - top_start + 1
                c_full = self.context_pane_content_height(compact=False)
                c_compact = self.context_pane_content_height(compact=True)

                for compact_np, n_h, compact_ctx, c_h in [
                    (False, n_full, False, c_full),
                    (False, n_full, True, c_compact),
                    (True, n_compact, True, c_compact),
                ]:
                    if n_h + DIVIDER_ROWS + c_h <= usable_span:
                        break
                else:
                    compact_np, n_h, compact_ctx = True, n_compact, True

                compact = compact_np  # used for draw_now_playing_tab below
                top_h = n_h + (1 if not compact_np else 0)  # a little breathing room only when spacious
                top_h = max(3, min(top_h, usable_span - DIVIDER_ROWS - 3))
            else:
                # History/Stats are open-ended lists - more room always shows
                # more content, so the old proportional split still applies.
                compact = False
                compact_ctx = False
                CONTEXT_MIN = 6
                top_h = max(8, int(usable_span * 0.55))
                top_h = min(top_h, usable_span - CONTEXT_MIN)

            if top_h < 3 or usable_span - top_h < 3:
                # Not enough room to split usefully; give it all to the workspace tab.
                top_max_row = bottom_limit
                divider_row = None
            else:
                divider_row = top_start + top_h
                top_max_row = divider_row - 1

            if self.workspace_tab == 2:
                self.draw_history_tab(left_w, right_w, top_max_row)
            elif self.workspace_tab == 3:
                self.draw_stats_tab(left_w, right_w, top_max_row)
            else:
                self.draw_now_playing_tab(left_w, right_w, top_max_row, compact=compact)

            if divider_row is not None:
                self.draw_hline(divider_row, left_w + 1, b['h'], max(0, right_w - 1))
                try:
                    self.stdscr.addch(divider_row, w - 1, b['t_right'])
                except curses.error:
                    pass
                self.draw_context_pane(left_w, right_w, divider_row + 1, bottom_limit, compact=compact_ctx)

        self.draw_hline(h - 2, 0, b['h'], w)
        try:
            self.stdscr.addch(h - 2, 0, b['bl'])
            self.stdscr.addch(h - 2, w - 1, b['br'])
            self.stdscr.addch(h - 2, left_w, b['t_up'])
        except curses.error:
            pass
        if self.search_mode:
            self.safe_addstr(self.stdscr, h - 1, 1, f"{self.label('search_prompt', 'Search')}: {self.search_query}_", PAIR_WARNING)
        else:
            controls = self.get_footer_controls(w - 2)
            self.safe_addstr(self.stdscr, h - 1, 1, controls, PAIR_MUTED)

        if self.toast_msg and time.time() < self.toast_until:
            self.safe_addstr(self.stdscr, 1, w - len(self.toast_msg) - 3, f" {self.toast_msg} ", PAIR_SUCCESS | curses.A_BOLD)
        elif self.toast_msg:
            self.toast_msg = None

        if self.volume_hud_until and time.time() < self.volume_hud_until:
            vol = self.cfg['volume']
            fill = vol // 5
            hud_fill, hud_empty = self.glyph('hud_fill', '█'), self.glyph('hud_empty', '░')
            bar = f"🔊 [{hud_fill * fill}{hud_empty * (20 - fill)}] {vol}%"
            self.safe_addstr(self.stdscr, 1, max(1, (w - len(bar)) // 2), f" {bar} ", PAIR_SUCCESS | curses.A_BOLD)
        elif self.volume_hud_until:
            self.volume_hud_until = 0

        if self.mode == 'wizard':
            self.draw_wizard()
        elif self.mode == 'confirm':
            self.draw_confirm()
        elif self.mode == 'tools_menu':
            self.draw_tools_menu()
        elif self.mode == 'folder_picker':
            self.draw_folder_picker()
        elif self.mode == 'folder_manage':
            self.draw_folder_manage()
        elif self.mode == 'folder_name_input':
            self.draw_folder_name_input()
        elif self.mode == 'theme_dir_input':
            self.draw_theme_dir_input()
        elif self.mode == 'theme_validator':
            self.draw_theme_validator()
        elif self.mode == 'theme_validator_detail':
            self.draw_theme_validator_detail()
        elif self.mode == 'help':
            self.draw_help()
        elif self.mode == 'onboarding':
            self.draw_onboarding()
        elif self.mode == 'theme_picker':
            self.draw_theme_picker()
        elif self.mode == 'readd_picker':
            self.draw_readd_picker()

        self.stdscr.refresh()

    DIALOG_TITLE_ALIGNS = ('left', 'center')

    def dialog_title_align(self):
        align = self.theme.get('dialog_title_align')
        return align if align in self.DIALOG_TITLE_ALIGNS else 'left'

    def draw_box(self, y0, x0, height, width, title=""):
        """Draws a themed bordered box and returns the inner (y, x) origin.

        Note on scope: this controls border style (already themeable via
        border_style/_border_chars) and title alignment. Content padding is
        the caller's responsibility, driven by dialog_padding() - each
        caller grows its own box_h/box_w by 2x the padding before calling
        this, then adds the padding to the returned (iy, ix) before drawing
        content, so the box always grows in lockstep with what it needs to
        contain (never clips, never adds dead space without a matching size
        increase). See any draw_*() dialog method for the pattern."""
        win_h, win_w = self.stdscr.getmaxyx()
        y0 = max(0, min(y0, win_h - height))
        x0 = max(0, min(x0, win_w - width))
        b = self.theme['_border_chars']
        try:
            for i in range(height):
                self.safe_addstr(self.stdscr, y0 + i, x0, " " * width, PAIR_DEFAULT | curses.A_REVERSE)
            self.stdscr.attron(PAIR_ACCENT)
            for i in range(height):
                self.safe_addstr(self.stdscr, y0 + i, x0, b['v'], PAIR_ACCENT)
                self.safe_addstr(self.stdscr, y0 + i, x0 + width - 1, b['v'], PAIR_ACCENT)
            self.draw_hline(y0, x0, b['h'], width)
            self.draw_hline(y0 + height - 1, x0, b['h'], width)
            self.stdscr.addch(y0, x0, b['tl'])
            self.stdscr.addch(y0, x0 + width - 1, b['tr'])
            self.stdscr.addch(y0 + height - 1, x0, b['bl'])
            self.stdscr.addch(y0 + height - 1, x0 + width - 1, b['br'])
            self.stdscr.attroff(PAIR_ACCENT)
        except curses.error:
            pass
        if title:
            text = f" {title} "
            if self.dialog_title_align() == 'center':
                tx = x0 + max(2, (width - len(text)) // 2)
            else:
                tx = x0 + 2
            self.safe_addstr(self.stdscr, y0, tx, text, PAIR_WARNING | curses.A_BOLD)
        return y0 + 1, x0 + 2

    def draw_wizard(self):
        if self.wizard_picker_open:
            self.draw_wizard_reuse_picker()
            return

        h, w = self.stdscr.getmaxyx()
        box_w = min(70, w - 4)
        box_h = 10
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        action_label = "Add New Station" if self.wizard_action == 'add' else "Edit Station"
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, action_label)
        iy += pad
        ix += pad
        TOTAL = 6

        if self.wizard_step == 0:
            label, hint = "URL", "Direct video/stream URL"
        elif self.wizard_step == 1:
            label, hint = "Name", "Display name for this station  ·  [Tab] Reuse existing"
        elif self.wizard_step == 2:
            label, hint = "Channel", "Optional - defaults to 'Custom'  ·  [Tab] Reuse existing"
        else:
            label, hint = None, None

        if label:
            self.safe_addstr(self.stdscr, iy, ix, f"Step {self.wizard_step + 1}/{TOTAL}: {label}", PAIR_LABEL | curses.A_BOLD)
            self.safe_addstr(self.stdscr, iy + 1, ix, hint, PAIR_DEFAULT)
            self.safe_addstr(self.stdscr, iy + 3, ix, f"> {self.wizard_buffer}_", PAIR_SUCCESS)
            if self.wizard_error:
                self.safe_addstr(self.stdscr, iy + 5, ix, self.wizard_error, PAIR_ERROR | curses.A_BOLD)
            self.safe_addstr(self.stdscr, iy + box_h - 3, ix, "[Enter] Next   [Esc] Cancel", PAIR_WARNING)

        elif self.wizard_step == 3:
            self.safe_addstr(self.stdscr, iy, ix, f"Step 4/{TOTAL}: Tags (select existing)", PAIR_LABEL | curses.A_BOLD)
            list_h = box_h - 6
            start = max(0, min(self.tag_cursor - list_h // 2, max(0, len(self.tag_list) - list_h)))
            if not self.tag_list:
                self.safe_addstr(self.stdscr, iy + 2, ix, "(no existing tags yet)", PAIR_DEFAULT)
            for i in range(list_h):
                idx = start + i
                if idx >= len(self.tag_list):
                    break
                tag = self.tag_list[idx]
                box = "[x]" if tag in self.tag_checked else "[ ]"
                style = PAIR_SELECTION if idx == self.tag_cursor else PAIR_DEFAULT
                self.safe_addstr(self.stdscr, iy + 1 + i, ix, self.clip_text(f"{box} {tag}", box_w - 6).ljust(box_w - 6), style)
            self.safe_addstr(self.stdscr, iy + box_h - 3, ix, "[Space]Toggle [Up/Dn]Move [Enter]Next [Esc]Cancel", PAIR_WARNING)

        elif self.wizard_step == 4:
            self.safe_addstr(self.stdscr, iy, ix, f"Step 5/{TOTAL}: Add new tags", PAIR_LABEL | curses.A_BOLD)
            self.safe_addstr(self.stdscr, iy + 1, ix, "Comma-separated, optional (e.g. chill, night)", PAIR_DEFAULT)
            self.safe_addstr(self.stdscr, iy + 3, ix, f"> {self.wizard_buffer}_", PAIR_SUCCESS)
            if self.wizard_error:
                self.safe_addstr(self.stdscr, iy + 5, ix, self.wizard_error, PAIR_ERROR | curses.A_BOLD)
            self.safe_addstr(self.stdscr, iy + box_h - 3, ix, "[Enter] Next   [Esc] Cancel", PAIR_WARNING)

        elif self.wizard_step == 5:
            self.safe_addstr(self.stdscr, iy, ix, f"Step 6/{TOTAL}: Folders (which lists include this?)", PAIR_LABEL | curses.A_BOLD)
            folder_names = sorted(self.folders.keys())
            list_h = box_h - 6
            start = max(0, min(self.tag_cursor - list_h // 2, max(0, len(folder_names) - list_h)))
            if not folder_names:
                self.safe_addstr(self.stdscr, iy + 2, ix, "(no folders yet - press [O] later to create some)", PAIR_DEFAULT)
            for i in range(list_h):
                idx = start + i
                if idx >= len(folder_names):
                    break
                fname = folder_names[idx]
                box = "[x]" if fname in self.wizard_folder_checked else "[ ]"
                style = PAIR_SELECTION if idx == self.tag_cursor else PAIR_DEFAULT
                self.safe_addstr(self.stdscr, iy + 1 + i, ix, self.clip_text(f"{box} {fname}", box_w - 6).ljust(box_w - 6), style)
            self.safe_addstr(self.stdscr, iy + box_h - 3, ix, "[Space]Toggle [Up/Dn]Move [Enter]Save Station [Esc]Cancel", PAIR_WARNING)

    def draw_wizard_reuse_picker(self):
        h, w = self.stdscr.getmaxyx()
        field_label = "Name" if self.wizard_step == 1 else "Channel"
        options = self.wizard_picker_options
        box_w = min(60, w - 4)
        box_h = min(len(options), h - 8) + 4
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, f"Reuse existing {field_label}")
        iy += pad
        ix += pad
        list_h = box_h - 3
        start = max(0, min(self.wizard_picker_cursor - list_h // 2, max(0, len(options) - list_h)))
        for i in range(list_h):
            idx = start + i
            if idx >= len(options):
                break
            style = PAIR_SELECTION if idx == self.wizard_picker_cursor else PAIR_DEFAULT
            self.safe_addstr(self.stdscr, iy + i, ix, self.clip_text(options[idx], box_w - 6).ljust(box_w - 6), style)
        self.safe_addstr(self.stdscr, iy + box_h - 2, ix, "[Up/Dn]Move [Enter]Use [Esc]Back", PAIR_WARNING)

    def draw_confirm(self):
        h, w = self.stdscr.getmaxyx()
        box_w = min(64, w - 4)
        box_h = 7
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, "Confirm")
        iy += pad
        ix += pad

        if self.confirm_kind == 'delete_station':
            station = next((s for s in self.stations if s['slug'] == self.confirm_target), None)
            name = station['name'] if station else "this station"
            self.safe_addstr(self.stdscr, iy + 1, ix, f"Delete '{name}'?", PAIR_ERROR | curses.A_BOLD)
        elif self.confirm_kind == 'delete_folder':
            self.safe_addstr(self.stdscr, iy + 1, ix, f"Delete folder '{self.confirm_target}'?", PAIR_ERROR | curses.A_BOLD)
            self.safe_addstr(self.stdscr, iy + 2, ix, "Stations stay - only this folder tag is removed.", PAIR_DEFAULT)
        elif self.confirm_kind == 'factory_reset':
            self.safe_addstr(self.stdscr, iy + 1, ix, "Erase ALL custom stations, folders,", PAIR_ERROR | curses.A_BOLD)
            self.safe_addstr(self.stdscr, iy + 2, ix, "favorites, and edits? This cannot be undone.", PAIR_ERROR | curses.A_BOLD)
        elif self.confirm_kind == 'readd_defaults_prompt':
            n = len(self.cfg.get('deleted_default_slugs', []))
            plural = "s" if n != 1 else ""
            self.safe_addstr(self.stdscr, iy + 1, ix, f"Found {n} previously deleted default station{plural}.", PAIR_LABEL | curses.A_BOLD)
            self.safe_addstr(self.stdscr, iy + 2, ix, "Re-add before syncing new defaults?", PAIR_DEFAULT)

        self.safe_addstr(self.stdscr, iy + box_h - 3, ix, "[y] Yes   [n/Esc] Cancel", PAIR_WARNING)

    def draw_tools_menu(self):
        h, w = self.stdscr.getmaxyx()
        options = self.get_tools_options()
        box_w = min(66, w - 4)
        box_h = len(options) + 4
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, "Tools")
        iy += pad
        ix += pad
        for i, opt in enumerate(options):
            style = PAIR_SELECTION if i == self.tools_cursor else PAIR_DEFAULT
            self.safe_addstr(self.stdscr, iy + i, ix, self.clip_text(opt, box_w - 6).ljust(box_w - 6), style)
        self.safe_addstr(self.stdscr, iy + box_h - 2, ix, "[Up/Dn]Move [Enter]Select [Esc]Close", PAIR_WARNING)

    def draw_folder_picker(self):
        h, w = self.stdscr.getmaxyx()
        options = ["All Stations (no filter)"] + sorted(self.folders.keys())
        box_w = min(50, w - 4)
        box_h = min(len(options), h - 6) + 4
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, "Filter by Folder")
        iy += pad
        ix += pad
        list_h = box_h - 3
        start = max(0, min(self.folder_picker_cursor - list_h // 2, max(0, len(options) - list_h)))
        for i in range(list_h):
            idx = start + i
            if idx >= len(options):
                break
            style = PAIR_SELECTION if idx == self.folder_picker_cursor else PAIR_DEFAULT
            marker = "> " if (options[idx] == (self.current_folder or "All Stations (no filter)")) else "  "
            self.safe_addstr(self.stdscr, iy + i, ix, self.clip_text(f"{marker}{options[idx]}", box_w - 6).ljust(box_w - 6), style)
        self.safe_addstr(self.stdscr, iy + box_h - 2, ix, "[Up/Dn]Move [Enter]Select [Esc]Close", PAIR_WARNING)

    def draw_folder_manage(self):
        h, w = self.stdscr.getmaxyx()
        names = sorted(self.folders.keys())
        box_w = min(56, w - 4)
        box_h = min(max(len(names), 1), h - 8) + 5
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, "Manage Folders")
        iy += pad
        ix += pad
        list_h = box_h - 4
        if not names:
            self.draw_empty_state(iy, ix, box_w - 6, self.label('no_folders_yet', '(no folders yet)'))
        start = max(0, min(self.folder_manage_cursor - list_h // 2, max(0, len(names) - list_h)))
        for i in range(list_h):
            idx = start + i
            if idx >= len(names):
                break
            fname = names[idx]
            count = len(self.folders.get(fname, []))
            style = PAIR_SELECTION if idx == self.folder_manage_cursor else PAIR_DEFAULT
            self.safe_addstr(self.stdscr, iy + i, ix, self.clip_text(f"{fname} ({count})", box_w - 6).ljust(box_w - 6), style)
        self.safe_addstr(self.stdscr, iy + box_h - 2, ix, "[n]New [r]Rename [x]Delete [Esc]Close", PAIR_WARNING)

    def draw_readd_picker(self):
        h, w = self.stdscr.getmaxyx()
        box_w = min(70, w - 4)
        box_h = min(max(len(self.readd_candidates), 1), h - 8) + 5
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, "Re-add Deleted Defaults")
        iy += pad
        ix += pad
        list_h = box_h - 4
        if not self.readd_candidates:
            self.draw_empty_state(iy, ix, box_w - 6, self.label('no_readd_candidates', '(none)'))
        start = max(0, min(self.readd_cursor - list_h // 2, max(0, len(self.readd_candidates) - list_h)))
        for i in range(list_h):
            idx = start + i
            if idx >= len(self.readd_candidates):
                break
            station = self.readd_candidates[idx]
            box = "[x]" if station['slug'] in self.readd_checked else "[ ]"
            style = PAIR_SELECTION if idx == self.readd_cursor else PAIR_DEFAULT
            line = f"{box} {station['name']} - {station['channel']}"
            self.safe_addstr(self.stdscr, iy + i, ix, self.clip_text(line, box_w - 6).ljust(box_w - 6), style)
        self.safe_addstr(self.stdscr, iy + box_h - 2, ix, "[Space]Toggle [a]All/None [Enter]Re-add [Esc]Skip", PAIR_WARNING)

    def draw_folder_name_input(self):
        h, w = self.stdscr.getmaxyx()
        box_w = min(56, w - 4)
        box_h = 6
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        title = "New Folder" if self.folder_name_action == 'create' else "Rename Folder"
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, title)
        iy += pad
        ix += pad
        self.safe_addstr(self.stdscr, iy, ix, "Folder name:", PAIR_LABEL | curses.A_BOLD)
        self.safe_addstr(self.stdscr, iy + 1, ix, f"> {self.folder_name_buffer}_", PAIR_SUCCESS)
        self.safe_addstr(self.stdscr, iy + box_h - 3, ix, "[Enter] Save   [Esc] Cancel", PAIR_WARNING)

    def effective_theme_dir(self):
        """The theme directory actually in use - cfg['theme_dir'] if the
        person has set one, else the built-in default. Used both to label
        the Tools menu entry and to pre-fill the input dialog, so what's
        shown always matches what load_theme_registry() will actually scan."""
        return self.cfg.get('theme_dir') or THEMES_DIR_DEFAULT

    def draw_theme_dir_input(self):
        h, w = self.stdscr.getmaxyx()
        box_w = min(76, w - 4)
        box_h = 7
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, "Theme Directory")
        iy += pad
        ix += pad
        self.safe_addstr(self.stdscr, iy, ix, "Directory to scan for .toml theme files:", PAIR_LABEL | curses.A_BOLD)
        buf_display = self.clip_text(self.theme_dir_buffer, box_w - 6)
        self.safe_addstr(self.stdscr, iy + 1, ix, f"> {buf_display}_", PAIR_SUCCESS)
        self.safe_addstr(self.stdscr, iy + 2, ix, "Leave empty to reset to the default.", PAIR_MUTED)
        self.safe_addstr(self.stdscr, iy + box_h - 3, ix, "[Enter] Save   [Esc] Cancel", PAIR_WARNING)

    def open_theme_dir_input(self):
        current = self.cfg.get('theme_dir')
        self.theme_dir_buffer = current if current else ""
        self.mode = 'theme_dir_input'

    def handle_theme_dir_input(self, key):
        if key == 27:
            self.mode = None
            return
        if key in (8, 127, curses.KEY_BACKSPACE):
            self.theme_dir_buffer = self.theme_dir_buffer[:-1]
            return
        if 32 <= key <= 126:
            self.theme_dir_buffer += chr(key)
            return
        if key in (10, 13):
            raw_path = self.theme_dir_buffer.strip()
            if not raw_path:
                self.cfg['theme_dir'] = None
                self.config_mgr.save()
                self.reload_theme_registry()
                self.show_toast(f"Theme directory reset to default ({THEMES_DIR_DEFAULT}).")
                self.mode = None
                return
            path = os.path.expanduser(raw_path)
            try:
                os.makedirs(path, exist_ok=True)
            except OSError as e:
                log_debug(f"Couldn't create/access theme directory '{path}': {e}")
                self.show_toast(f"Can't use '{path}': {e.strerror or e}")
                return  # stay in the dialog so they can fix the path
            self.cfg['theme_dir'] = path
            self.config_mgr.save()
            self.reload_theme_registry()
            self.show_toast(f"Theme directory set to {path}.")
            self.mode = None

    def reload_theme_registry(self):
        """Re-scans both theme sources (legacy JSON + the .toml directory)
        from the currently-configured location and re-resolves the active
        theme against the fresh registry - used after changing theme_dir,
        so a directory switch takes effect immediately instead of needing
        an app restart."""
        self.theme_registry = load_theme_registry(self.cfg.get('theme_dir'))
        self.theme = resolve_theme(self.cfg.get('theme', 'classic'), self.theme_registry)
        self.apply_theme()

    # --- Theme validator ---

    def open_theme_validator(self):
        self.validator_results = validate_theme_directory(
            self.effective_theme_dir(), known_theme_names=set(self.theme_registry.keys()))
        self.validator_cursor = 0
        self.mode = 'theme_validator'

    def _validator_summary(self, issues):
        if issues is None:
            return "?", PAIR_DEFAULT
        errors = [i for i in issues if i.severity == 'error']
        warnings = [i for i in issues if i.severity == 'warning']
        infos = [i for i in issues if i.severity == 'info']
        if not errors and not warnings and not infos:
            return "✓ clean", PAIR_SUCCESS
        if not errors and not warnings:
            # info-only: still worth a glance, but not a problem - don't
            # color it like one, and don't call it "clean" when there's
            # something to actually go read.
            return f"{len(infos)} note{'s' if len(infos) != 1 else ''}", PAIR_ACCENT
        bits = []
        if errors:
            bits.append(f"{len(errors)} error{'s' if len(errors) != 1 else ''}")
        if warnings:
            bits.append(f"{len(warnings)} warning{'s' if len(warnings) != 1 else ''}")
        if infos:
            bits.append(f"{len(infos)} note{'s' if len(infos) != 1 else ''}")
        return ", ".join(bits), (PAIR_ERROR if errors else PAIR_WARNING)

    def draw_theme_validator(self):
        h, w = self.stdscr.getmaxyx()
        box_w = min(74, w - 4)
        box_h = min(max(len(self.validator_results), 1), h - 10) + 5
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, "Theme Validator")
        iy += pad
        ix += pad

        self.safe_addstr(self.stdscr, iy, ix, self.clip_text(f"Scanning: {self.effective_theme_dir()}", box_w - 6), PAIR_MUTED)
        list_start = iy + 2
        list_h = box_h - 5

        if not self.validator_results:
            self.draw_empty_state(list_start, ix, box_w - 6, "(no .toml theme files found here)")
        else:
            start = max(0, min(self.validator_cursor - list_h // 2, max(0, len(self.validator_results) - list_h)))
            for row in range(list_h):
                idx = start + row
                if idx >= len(self.validator_results):
                    break
                fname, raw, issues = self.validator_results[idx]
                summary, summary_style = self._validator_summary(issues)
                fixable = raw is not None and any(i.autofix for i in issues)
                marker = "> " if idx == self.validator_cursor else "  "
                fix_hint = " [f: auto-fix]" if fixable else ""
                line = f"{marker}{fname} - {summary}{fix_hint}"
                style = PAIR_SELECTION if idx == self.validator_cursor else summary_style
                self.safe_addstr(self.stdscr, list_start + row, ix, self.clip_text(line, box_w - 6).ljust(box_w - 6), style)

        self.safe_addstr(self.stdscr, iy + box_h - 2, ix, "[Up/Dn]Move [Enter]Details [f]Auto-fix [r]Rescan [Esc]Close", PAIR_WARNING)

    def handle_theme_validator_input(self, key):
        n = len(self.validator_results)
        if key == 27:
            self.mode = None
        elif key in (curses.KEY_UP, ord('k')):
            if self.validator_cursor > 0:
                self.validator_cursor -= 1
        elif key in (curses.KEY_DOWN, ord('j')):
            if self.validator_cursor < n - 1:
                self.validator_cursor += 1
        elif key == ord('r'):
            self.open_theme_validator()
            self.show_toast("Re-scanned theme directory.")
        elif key in (10, 13):
            if n:
                self.validator_detail_scroll = 0
                self.mode = 'theme_validator_detail'
        elif key == ord('f'):
            if n:
                self.apply_validator_autofix(self.validator_cursor)

    def apply_validator_autofix(self, index):
        """Auto-fix every fixable issue in one theme file and refresh
        both the on-screen results and the live registry, so the effect
        (and any remaining, non-fixable issues) show immediately."""
        fname, raw, issues = self.validator_results[index]
        fixable = [i for i in issues if i.autofix]
        if raw is None:
            self.show_toast(f"{fname}: can't auto-fix a file that doesn't parse as TOML.")
            return
        if not fixable:
            self.show_toast(f"{fname}: nothing auto-fixable here.")
            return
        try:
            fixed, applied = autofix_theme_file(self.effective_theme_dir(), fname, raw, issues)
        except OSError as e:
            log_debug(f"Auto-fix failed for {fname}: {e}")
            self.show_toast(f"Couldn't write {fname}: {e.strerror or e}")
            return
        new_issues = validate_theme_dict(fixed, known_theme_names=set(self.theme_registry.keys()))
        self.validator_results[index] = (fname, fixed, new_issues)
        self.reload_theme_registry()
        self.show_toast(f"{fname}: fixed {len(applied)} issue(s) (backup saved as {fname}.bak).")

    def draw_theme_validator_detail(self):
        h, w = self.stdscr.getmaxyx()
        fname, raw, issues = self.validator_results[self.validator_cursor]
        box_w = min(78, w - 4)
        box_h = min(max(len(issues), 1), h - 10) + 5
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, fname)
        iy += pad
        ix += pad

        row_avail = box_w - 6
        list_h = box_h - 4
        if not issues:
            self.draw_empty_state(iy, ix, row_avail, "(no issues - this file is clean)")
        else:
            # Word-wrap each issue onto as many lines as it needs, then
            # scroll the flattened line list - a single long message
            # shouldn't get silently clipped to one row.
            flat_lines = []
            SEVERITY_TAGS = {'error': ('ERROR', PAIR_ERROR), 'warning': ('WARN ', PAIR_WARNING), 'info': ('NOTE ', PAIR_ACCENT)}
            for issue in issues:
                tag, tag_style = SEVERITY_TAGS.get(issue.severity, ('?    ', PAIR_DEFAULT))
                fix_tag = " [fixable]" if issue.autofix else ""
                header = f"[{tag}] {issue.path or '(root)'}{fix_tag}"
                flat_lines.append((header, tag_style))
                for wrapped in textwrap.wrap(issue.message, max(10, row_avail - 2)):
                    flat_lines.append((f"  {wrapped}", PAIR_DEFAULT))
                flat_lines.append(("", PAIR_DEFAULT))

            max_scroll = max(0, len(flat_lines) - list_h)
            self.validator_detail_scroll = max(0, min(self.validator_detail_scroll, max_scroll))
            for row in range(list_h):
                idx = self.validator_detail_scroll + row
                if idx >= len(flat_lines):
                    break
                text, style = flat_lines[idx]
                self.safe_addstr(self.stdscr, iy + row, ix, self.clip_text(text, row_avail), style)

        fixable = raw is not None and any(i.autofix for i in issues)
        hint = "[Up/Dn]Scroll " + ("[f]Auto-fix " if fixable else "") + "[Esc]Back"
        self.safe_addstr(self.stdscr, iy + box_h - 2, ix, hint, PAIR_WARNING)

    def handle_theme_validator_detail_input(self, key):
        if key == 27:
            self.mode = 'theme_validator'
        elif key in (curses.KEY_UP, ord('k')):
            self.validator_detail_scroll = max(0, self.validator_detail_scroll - 1)
        elif key in (curses.KEY_DOWN, ord('j')):
            self.validator_detail_scroll += 1
        elif key == ord('f'):
            self.apply_validator_autofix(self.validator_cursor)
            self.validator_detail_scroll = 0

    def draw_help(self):
        h, w = self.stdscr.getmaxyx()
        lines = [
            ("PLAYBACK", PAIR_LABEL | curses.A_BOLD),
            ("  Enter  Play / Pause  r  Random        p  Pause / Resume", 0),
            ("  =/-    Volume +/-    t  Sleep timer (30m, toggle)", 0),
            ("", 0),
            ("LIBRARY", PAIR_LABEL | curses.A_BOLD),
            ("  Up/Dn (j/k)  Move    f  Toggle favorite   F  Favorites only", 0),
            ("  s or /  Search       a  Add   e  Edit   x  Delete", 0),
            ("", 0),
            ("ORGANIZE", PAIR_LABEL | curses.A_BOLD),
            ("  o  Filter by folder    O  Manage folders    m  Tools menu", 0),
            ("", 0),
            ("VIEW", PAIR_LABEL | curses.A_BOLD),
            ("  1/2/3  Now Playing / History / Stats    d  Debug logs", 0),
            ("", 0),
            ("q  Quit", PAIR_ERROR | curses.A_BOLD),
        ]
        box_w = min(66, w - 4)
        box_h = len(lines) + 4
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, "Keyboard Shortcuts")
        iy += pad
        ix += pad
        for i, (text, style) in enumerate(lines):
            if text:
                self.safe_addstr(self.stdscr, iy + i, ix, text, style)
        self.safe_addstr(self.stdscr, iy + box_h - 2, ix, "Press any key to close", PAIR_WARNING)

    def draw_onboarding(self):
        h, w = self.stdscr.getmaxyx()
        lines = [
            ("Welcome! A few essentials to get moving:", curses.A_BOLD),
            ("", 0),
            ("  Up/Down (or j/k)   Move through stations", 0),
            ("  Enter              Play the selected station", 0),
            ("                     (Enter again to pause / resume)", 0),
            ("  f                  Favorite it   ·   s or /   Search", 0),
            ("  ?                  Full shortcut list, any time", 0),
            ("  q                  Quit", 0),
        ]
        box_w = min(64, w - 4)
        box_h = len(lines) + 4
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, "Lofi Stream CLI")
        iy += pad
        ix += pad
        for i, (text, style) in enumerate(lines):
            if text:
                self.safe_addstr(self.stdscr, iy + i, ix, text, style)
        self.safe_addstr(self.stdscr, iy + box_h - 2, ix, "Press any key to begin", PAIR_SUCCESS | curses.A_BOLD)

    def fuzzy_score(self, query, text):
        """Score `text` against `query`. Returns None if `query`'s characters
        don't all appear in `text` in order (no match at all). Otherwise
        returns a score where higher = better, tiered so that:
          1) an exact contiguous substring match always outranks
          2) a scattered subsequence match (e.g. "lfjz" finding "LoFi JaZz"),
        and within each tier, matches nearer the start / more tightly
        clustered score higher. This needs no external library and is cheap
        enough to run over the whole station list on every keystroke."""
        if not query:
            return 0
        idx = text.find(query)
        if idx != -1:
            return 1000 - idx
        qi = 0
        positions = []
        for ti, ch in enumerate(text):
            if qi < len(query) and ch == query[qi]:
                positions.append(ti)
                qi += 1
        if qi < len(query):
            return None
        span = positions[-1] - positions[0] + 1
        return 500 - span - positions[0]

    def update_filter(self):
        self.filtered_stations = list(self.stations)
        if self.show_favorites_only:
            self.filtered_stations = [s for s in self.filtered_stations if s['slug'] in self.cfg['favorites']]

        if self.current_folder and self.current_folder != "All":
            folder_slugs = set(self.folders.get(self.current_folder, []))
            self.filtered_stations = [s for s in self.filtered_stations if s['slug'] in folder_slugs]

        if self.search_query:
            q = self.search_query.lower()
            scored = []
            for s in self.filtered_stations:
                haystack = f"{s['name']} {s['channel']} {' '.join(s['tags'])}".lower()
                score = self.fuzzy_score(q, haystack)
                if score is not None:
                    scored.append((score, s))
            scored.sort(key=lambda pair: pair[0], reverse=True)
            self.filtered_stations = [s for _, s in scored]

        self.selected_idx = min(self.selected_idx, max(0, len(self.filtered_stations) - 1))
        self.adjust_scroll()

    def adjust_scroll(self):
        h, _ = self.stdscr.getmaxyx()
        max_display = h - 2 - self.station_list_start_row()
        new_target = self.scroll_target
        if self.selected_idx < self.scroll_offset:
            new_target = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + max_display:
            new_target = self.selected_idx - max_display + 1
        self.scroll_target = new_target
        if new_target != self.scroll_offset:
            self.animate_scroll_to(new_target)

    def animate_scroll_to(self, target):
        """Step the visible window toward `target` over a couple of quick redraws
        instead of snapping instantly, so moving past the edge of the list reads
        as a scroll rather than a jump cut. Bounded to a handful of frames so it
        never adds noticeable input lag, even for a big jump (e.g. after a filter
        change moves the selection far from where it was)."""
        start = self.scroll_offset
        diff = target - start
        if diff == 0:
            return
        steps = min(3, abs(diff))
        for i in range(1, steps + 1):
            self.scroll_offset = start + round(diff * i / steps)
            self.draw()
            time.sleep(0.02)
        self.scroll_offset = target

    def _finish_history_entry(self):
        if self.current_history_entry and self.current_history_entry.get('ended_ts') is None:
            self.current_history_entry['ended_ts'] = time.time()

    def _toggle_pause(self):
        """Shared by the 'p' key and Enter-on-the-active-station: pause/resume
        in place via mpv's pause property, without touching the loaded file."""
        if self.is_playing:
            self.is_paused = not self.is_paused
            self.mpv.toggle_pause(self.is_paused)

    def play_selected(self):
        if not self.filtered_stations: return
        self._finish_history_entry()
        self.current_station = self.filtered_stations[self.selected_idx]

        log_debug(f"Sending raw URL to MPV: '{self.current_station['url']}'")

        # We send the RAW YouTube URL directly to MPV. MPV invokes its native ytdl backend
        # flawlessly without blocking Python or mis-matching connection headers!
        self.mpv.play(self.current_station['url'])

        self.is_playing = True
        self.is_paused = False
        # status_msg is no longer used to fake a "Streaming" state here - the
        # actual label comes from get_playback_status(), which reflects
        # mpv.playback_state as confirmed by mpv's own IPC events.
        self.status_msg = ""

        entry = {
            "name": self.current_station['name'],
            "channel": self.current_station['channel'],
            "slug": self.current_station['slug'],
            "started_ts": time.time(),
            "ended_ts": None,
        }
        self.history.append(entry)
        if len(self.history) > 200:
            self.history = self.history[-200:]
        self.current_history_entry = entry

        self.cfg['last_station'] = self.current_station['slug']
        self.cfg['history'] = self.history
        self.config_mgr.save()
        log_debug(f"Stream request sent successfully for '{self.current_station['name']}'.")

    def get_station_icon(self, station):
        tag_icon_map = self.theme.get('glyphs', {}).get('tag_icons', DEFAULT_TAG_ICONS)
        for tag in station.get('tags', []):
            if tag in tag_icon_map:
                return tag_icon_map[tag]
        return self.glyph('default_tag_icon', '♫')

    def format_duration(self, seconds):
        seconds = max(0, int(seconds))
        h, rem = divmod(seconds, 3600)
        m, _ = divmod(rem, 60)
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m"
        return "<1m"

    def compute_stats(self):
        now = time.time()
        lt = time.localtime(now)
        today_start = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
        total_today = 0.0
        total_all = 0.0
        per_station = {}
        for entry in self.history:
            started = entry['started_ts']
            ended = entry.get('ended_ts') or now
            dur = max(0.0, ended - started)
            total_all += dur
            if ended > today_start:
                eff_start = max(started, today_start)
                total_today += max(0.0, ended - eff_start)
            per_station[entry['name']] = per_station.get(entry['name'], 0.0) + dur
        top = sorted(per_station.items(), key=lambda kv: -kv[1])[:5]
        return total_today, total_all, top

    def generate_slug(self, name, exclude_slug=None):
        base = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or "station"
        existing = {s['slug'] for s in self.stations if s['slug'] != exclude_slug}
        slug = base
        n = 2
        while slug in existing:
            slug = f"{base}-{n}"
            n += 1
        return slug

    def start_add_wizard(self):
        self.mode = 'wizard'
        self.wizard_action = 'add'
        self.wizard_target_slug = None
        self.wizard_step = 0
        self.wizard_data = {"url": "", "name": "", "channel": "", "tags": []}
        self.wizard_buffer = ""
        self.wizard_error = ""
        self.wizard_picker_open = False
        log_debug("Opened Add Station wizard.")

    def start_edit_wizard(self):
        if not self.filtered_stations:
            return
        station = self.filtered_stations[self.selected_idx]
        self.mode = 'wizard'
        self.wizard_action = 'edit'
        self.wizard_target_slug = station['slug']
        self.wizard_step = 0
        self.wizard_data = {
            "url": station['url'],
            "name": station['name'],
            "channel": station['channel'],
            "tags": list(station['tags']),
        }
        self.wizard_buffer = self.wizard_data['url']
        self.wizard_error = ""
        self.wizard_picker_open = False
        log_debug(f"Opened Edit wizard for '{station['name']}'.")

    def cancel_wizard(self):
        log_debug("Wizard cancelled.")
        self.mode = None
        self.wizard_action = None
        self.wizard_target_slug = None
        self.wizard_data = {}
        self.wizard_buffer = ""
        self.wizard_error = ""
        self.wizard_folder_checked = set()
        self.wizard_picker_open = False

    def _enter_tag_select_step(self):
        self.tag_list = sorted(set(t for s in self.stations for t in s['tags']))
        self.tag_checked = set(self.wizard_data.get('tags', []))
        self.tag_cursor = 0
        self.wizard_step = 3
        self.wizard_error = ""

    def _enter_folder_select_step(self):
        if self.wizard_action == 'edit' and self.wizard_target_slug:
            self.wizard_folder_checked = {
                fname for fname, slugs in self.folders.items() if self.wizard_target_slug in slugs
            }
        elif "Default" in self.folders:
            self.wizard_folder_checked = {"Default"}
        else:
            self.wizard_folder_checked = set()
        self.tag_cursor = 0  # reused as the folder-list cursor for this step
        self.wizard_step = 5
        self.wizard_error = ""

    def advance_wizard_text_step(self):
        """Called on Enter while on a plain text-entry step (0, 1, 2, or 4)."""
        if self.wizard_step == 0:
            if not self.wizard_buffer.strip():
                self.wizard_error = "URL cannot be empty."
                return
            self.wizard_data['url'] = self.wizard_buffer.strip()
            self.wizard_step = 1
            self.wizard_buffer = self.wizard_data['name']
            self.wizard_error = ""
        elif self.wizard_step == 1:
            if not self.wizard_buffer.strip():
                self.wizard_error = "Name cannot be empty."
                return
            self.wizard_data['name'] = self.wizard_buffer.strip()
            self.wizard_step = 2
            self.wizard_buffer = self.wizard_data['channel']
            self.wizard_error = ""
        elif self.wizard_step == 2:
            self.wizard_data['channel'] = self.wizard_buffer.strip() or "Custom"
            self._enter_tag_select_step()
        elif self.wizard_step == 4:
            extra = [t.strip().lower() for t in self.wizard_buffer.split(',') if t.strip()]
            for t in extra:
                if t not in self.wizard_data['tags']:
                    self.wizard_data['tags'].append(t)
            self._enter_folder_select_step()

    def finalize_wizard(self):
        tags = self.wizard_data['tags'] if self.wizard_data['tags'] else ["custom"]
        if self.wizard_action == 'add':
            slug = self.generate_slug(self.wizard_data['name'])
            new_station = {
                "slug": slug,
                "channel": self.wizard_data['channel'],
                "name": self.wizard_data['name'],
                "url": self.wizard_data['url'],
                "tags": tags,
            }
            self.stations.append(new_station)
            log_debug(f"Added new station '{new_station['name']}' ({slug}).")
        else:
            slug = self.wizard_target_slug
            for s in self.stations:
                if s['slug'] == slug:
                    s['channel'] = self.wizard_data['channel']
                    s['name'] = self.wizard_data['name']
                    s['url'] = self.wizard_data['url']
                    s['tags'] = tags
                    log_debug(f"Updated station '{s['name']}' ({s['slug']}).")
                    if self.current_station and self.current_station['slug'] == s['slug']:
                        self.current_station = s
                    break

        # Sync folder membership: add to checked folders, remove from unchecked ones.
        for fname, slugs in self.folders.items():
            if fname in self.wizard_folder_checked:
                if slug not in slugs:
                    slugs.append(slug)
            else:
                if slug in slugs:
                    slugs.remove(slug)

        self.cfg['stations'] = self.stations
        self.cfg['folders'] = self.folders
        self.config_mgr.save()
        self.update_filter()
        self.cancel_wizard()

    def handle_wizard_input(self, key):
        if self.wizard_picker_open:
            self._handle_wizard_picker_input(key)
            return

        if key == 27:  # Esc
            self.cancel_wizard()
            return

        if self.wizard_step == 3:  # tag select
            if key in (curses.KEY_UP, ord('k')):
                if self.tag_cursor > 0:
                    self.tag_cursor -= 1
            elif key in (curses.KEY_DOWN, ord('j')):
                if self.tag_cursor < len(self.tag_list) - 1:
                    self.tag_cursor += 1
            elif key == ord(' '):
                if self.tag_list:
                    tag = self.tag_list[self.tag_cursor]
                    if tag in self.tag_checked:
                        self.tag_checked.remove(tag)
                    else:
                        self.tag_checked.add(tag)
            elif key in (10, 13):
                self.wizard_data['tags'] = sorted(self.tag_checked)
                self.wizard_step = 4
                self.wizard_buffer = ""
                self.wizard_error = ""
            return

        if self.wizard_step == 5:  # folder select
            folder_names = sorted(self.folders.keys())
            if key in (curses.KEY_UP, ord('k')):
                if self.tag_cursor > 0:
                    self.tag_cursor -= 1
            elif key in (curses.KEY_DOWN, ord('j')):
                if self.tag_cursor < len(folder_names) - 1:
                    self.tag_cursor += 1
            elif key == ord(' '):
                if folder_names:
                    fname = folder_names[self.tag_cursor]
                    if fname in self.wizard_folder_checked:
                        self.wizard_folder_checked.remove(fname)
                    else:
                        self.wizard_folder_checked.add(fname)
            elif key in (10, 13):
                self.finalize_wizard()
            return

        # Plain text-entry steps (0:URL, 1:Name, 2:Channel, 4:new tags)
        if key == 9 and self.wizard_step in (1, 2):  # Tab: reuse an existing value
            self._open_wizard_picker()
            return
        if key in (10, 13):
            self.advance_wizard_text_step()
        elif key in (8, 127, curses.KEY_BACKSPACE):
            self.wizard_buffer = self.wizard_buffer[:-1]
        elif 32 <= key <= 126:
            self.wizard_buffer += chr(key)

    def _open_wizard_picker(self):
        field = 'name' if self.wizard_step == 1 else 'channel'
        # Exclude the value currently being edited so it's not offered back to itself.
        exclude = self.wizard_target_slug
        values = sorted(set(
            s[field] for s in self.stations
            if s.get(field) and s['slug'] != exclude
        ))
        if not values:
            self.show_toast("No existing values to reuse yet.")
            return
        self.wizard_picker_options = values
        self.wizard_picker_cursor = 0
        self.wizard_picker_open = True

    def _handle_wizard_picker_input(self, key):
        if key == 27:  # Esc closes just the picker, not the whole wizard
            self.wizard_picker_open = False
        elif key in (curses.KEY_UP, ord('k')):
            if self.wizard_picker_cursor > 0:
                self.wizard_picker_cursor -= 1
        elif key in (curses.KEY_DOWN, ord('j')):
            if self.wizard_picker_cursor < len(self.wizard_picker_options) - 1:
                self.wizard_picker_cursor += 1
        elif key in (10, 13):
            self.wizard_buffer = self.wizard_picker_options[self.wizard_picker_cursor]
            self.wizard_picker_open = False

    # --- Deletion (stations & folders) + factory reset, all via one confirm flow ---

    def start_delete_confirm(self):
        if not self.filtered_stations:
            return
        self.confirm_kind = 'delete_station'
        self.confirm_target = self.filtered_stations[self.selected_idx]['slug']
        self.mode = 'confirm'

    def start_factory_reset_confirm(self):
        self.confirm_kind = 'factory_reset'
        self.confirm_target = None
        self.mode = 'confirm'

    def start_delete_folder_confirm(self, folder_name):
        self.confirm_kind = 'delete_folder'
        self.confirm_target = folder_name
        self.mode = 'confirm'

    def execute_confirm(self):
        if self.confirm_kind == 'delete_station':
            self._delete_station(self.confirm_target)
        elif self.confirm_kind == 'delete_folder':
            self._delete_folder(self.confirm_target)
        elif self.confirm_kind == 'factory_reset':
            self._factory_reset()
        elif self.confirm_kind == 'readd_defaults_prompt':
            self.confirm_kind = None
            self.confirm_target = None
            self.open_readd_picker()
            return
        self.mode = None
        self.confirm_kind = None
        self.confirm_target = None

    def _delete_station(self, slug):
        station = next((s for s in self.stations if s['slug'] == slug), None)
        if not station:
            return
        if self.current_station and self.current_station['slug'] == slug:
            self.mpv.stop()
            self._finish_history_entry()
            self.current_station = None
            self.is_playing = False
            self.is_paused = False
            self.status_msg = "Idle"
        self.stations.remove(station)
        if slug in self.cfg['favorites']:
            self.cfg['favorites'].remove(slug)
        for slugs in self.folders.values():
            if slug in slugs:
                slugs.remove(slug)
        if any(d['slug'] == slug for d in DEFAULT_STATIONS):
            deleted_list = self.cfg.setdefault('deleted_default_slugs', [])
            if slug not in deleted_list:
                deleted_list.append(slug)
        self.cfg['stations'] = self.stations
        self.cfg['folders'] = self.folders
        self.config_mgr.save()
        self.update_filter()
        self.show_toast(f"Deleted '{station['name']}'.")
        log_debug(f"Deleted station '{station['name']}' ({slug}).")

    def _delete_folder(self, folder_name):
        if folder_name in self.folders:
            del self.folders[folder_name]
            if self.current_folder == folder_name:
                self.current_folder = None
            self.cfg['folders'] = self.folders
            self.config_mgr.save()
            self.update_filter()
            self.show_toast(f"Deleted folder '{folder_name}'.")
            log_debug(f"Deleted folder '{folder_name}'.")
            self.folder_manage_cursor = max(0, self.folder_manage_cursor - 1)

    def _factory_reset(self):
        if self.is_playing:
            self.mpv.stop()
        self.stations = copy.deepcopy(DEFAULT_STATIONS)
        self.folders = {"Default": [s['slug'] for s in self.stations]}
        self.history = []
        self.current_history_entry = None
        self.cfg['stations'] = self.stations
        self.cfg['folders'] = self.folders
        self.cfg['favorites'] = []
        self.cfg['last_station'] = None
        self.cfg['synced_default_slugs'] = [s['slug'] for s in DEFAULT_STATIONS]
        self.cfg['deleted_default_slugs'] = []
        self.cfg['history'] = self.history
        self.config_mgr.save()

        self.current_folder = None
        self.show_favorites_only = False
        self.search_query = ""
        self.search_mode = False
        self.current_station = None
        self.is_playing = False
        self.is_paused = False
        self.status_msg = "Idle"
        self.workspace_tab = 1
        self.update_filter()
        self.show_toast("Factory reset complete.")
        log_debug("Factory reset performed.")

    # --- Tools menu: sync defaults / factory reset ---

    def open_tools_menu(self):
        self.mode = 'tools_menu'
        self.tools_cursor = 0

    def get_tools_options(self):
        mode_label = {"unicode": "Unicode", "ascii": "ASCII", "nerd": "Nerd Font"}.get(self.cfg.get('glyph_mode', 'unicode'), 'Unicode')
        return [
            "Sync Defaults (add any new built-in stations)",
            "Switch Theme",
            f"Glyph Mode: {mode_label} (Enter to cycle)",
            f"Density: {self.density().capitalize()} (Enter to cycle)",
            f"Theme Directory: {self.effective_theme_dir()} (Enter to change)",
            "Validate Theme Files",
            "Factory Reset (erase everything, start fresh)",
        ]

    def cycle_glyph_mode(self):
        order = ["unicode", "ascii", "nerd"]
        current = self.cfg.get('glyph_mode', 'unicode')
        next_mode = order[(order.index(current) + 1) % len(order)] if current in order else "unicode"
        self.cfg['glyph_mode'] = next_mode
        self.config_mgr.save()
        self.show_toast(f"Glyph mode: {next_mode}")

    def _sync_new_defaults(self):
        """Core of Sync Defaults: adds any built-in stations not yet introduced
        to this user's library. Returns the list of newly added names. No
        toast - callers combine this with other outcomes (e.g. re-adding
        deleted defaults) into a single message."""
        existing_slugs = {s['slug'] for s in self.stations}
        synced = set(self.cfg.get('synced_default_slugs', []))
        added_names = []
        for d in DEFAULT_STATIONS:
            if d['slug'] in synced:
                continue
            if d['slug'] not in existing_slugs:
                new_station = copy.deepcopy(d)
                self.stations.append(new_station)
                self.folders.setdefault("Default", []).append(new_station['slug'])
                added_names.append(new_station['name'])
            synced.add(d['slug'])

        self.cfg['synced_default_slugs'] = sorted(synced)
        self.cfg['stations'] = self.stations
        self.cfg['folders'] = self.folders
        self.config_mgr.save()
        self.update_filter()
        if added_names:
            log_debug(f"Sync Defaults added: {', '.join(added_names)}")
        return added_names

    def sync_defaults(self):
        """Tools-menu entry point when there's nothing to offer re-adding
        (or the user declined it) - just syncs new built-ins and toasts."""
        added_names = self._sync_new_defaults()
        if added_names:
            self.show_toast(f"Synced {len(added_names)} new station(s).")
        else:
            self.show_toast("Already up to date.")
            log_debug("Sync Defaults: nothing new to add.")

    def open_readd_picker(self):
        deleted_set = set(self.cfg.get('deleted_default_slugs', []))
        # Preserve DEFAULT_STATIONS' own ordering (channel-grouped) rather than
        # the order stations happened to be deleted in.
        self.readd_candidates = [d for d in DEFAULT_STATIONS if d['slug'] in deleted_set]
        self.readd_checked = set()
        self.readd_cursor = 0
        self.mode = 'readd_picker'
        log_debug(f"Opened re-add picker with {len(self.readd_candidates)} candidate(s).")

    def _readd_selected_defaults(self):
        """Re-adds the checked stations from the re-add picker. Returns the
        list of newly added names. No toast - see sync_defaults note above."""
        if not self.readd_checked:
            return []
        existing_slugs = {s['slug'] for s in self.stations}
        by_slug = {d['slug']: d for d in DEFAULT_STATIONS}
        deleted_list = self.cfg.setdefault('deleted_default_slugs', [])
        added_names = []
        for slug in self.readd_checked:
            if slug in existing_slugs:
                continue
            d = by_slug.get(slug)
            if not d:
                continue
            new_station = copy.deepcopy(d)
            self.stations.append(new_station)
            self.folders.setdefault("Default", []).append(slug)
            added_names.append(new_station['name'])
            if slug in deleted_list:
                deleted_list.remove(slug)

        self.cfg['stations'] = self.stations
        self.cfg['folders'] = self.folders
        self.cfg['deleted_default_slugs'] = deleted_list
        self.config_mgr.save()
        self.update_filter()
        if added_names:
            log_debug(f"Re-added previously deleted defaults: {', '.join(added_names)}")
        return added_names

    def finish_readd_and_sync(self, do_readd):
        """Shared tail for both picker paths (Enter with selections, or
        Esc/skip): optionally re-add checked defaults, then always run the
        normal new-defaults sync, then show one combined toast."""
        readded = self._readd_selected_defaults() if do_readd else []
        self.mode = None
        synced = self._sync_new_defaults()
        parts = []
        if readded:
            parts.append(f"Re-added {len(readded)}")
        if synced:
            parts.append(f"synced {len(synced)} new")
        self.show_toast((", ".join(parts) + ".") if parts else "Already up to date.")

    def handle_readd_picker_input(self, key):
        if key == 27:
            self.finish_readd_and_sync(do_readd=False)
        elif key in (curses.KEY_UP, ord('k')):
            if self.readd_cursor > 0:
                self.readd_cursor -= 1
        elif key in (curses.KEY_DOWN, ord('j')):
            if self.readd_cursor < len(self.readd_candidates) - 1:
                self.readd_cursor += 1
        elif key == ord(' '):
            if self.readd_candidates:
                slug = self.readd_candidates[self.readd_cursor]['slug']
                if slug in self.readd_checked:
                    self.readd_checked.discard(slug)
                else:
                    self.readd_checked.add(slug)
        elif key == ord('a'):
            if self.readd_checked and len(self.readd_checked) == len(self.readd_candidates):
                self.readd_checked = set()
            else:
                self.readd_checked = {s['slug'] for s in self.readd_candidates}
        elif key in (10, 13):
            self.finish_readd_and_sync(do_readd=True)

    def handle_tools_menu_input(self, key):
        options = self.get_tools_options()
        if key == 27:
            self.mode = None
        elif key in (curses.KEY_UP, ord('k')):
            if self.tools_cursor > 0:
                self.tools_cursor -= 1
        elif key in (curses.KEY_DOWN, ord('j')):
            if self.tools_cursor < len(options) - 1:
                self.tools_cursor += 1
        elif key in (10, 13):
            if self.tools_cursor == 0:
                self.mode = None
                if self.cfg.get('deleted_default_slugs'):
                    self.confirm_kind = 'readd_defaults_prompt'
                    self.confirm_target = None
                    self.mode = 'confirm'
                else:
                    self.sync_defaults()
            elif self.tools_cursor == 1:
                self.mode = None
                self.open_theme_picker()
            elif self.tools_cursor == 2:
                self.cycle_glyph_mode()  # stays open - it's a quick cycle, not a one-shot action
            elif self.tools_cursor == 3:
                self.cycle_density()  # stays open, same reasoning as glyph mode above
            elif self.tools_cursor == 4:
                self.mode = None
                self.open_theme_dir_input()
            elif self.tools_cursor == 5:
                self.mode = None
                self.open_theme_validator()
            elif self.tools_cursor == 6:
                self.mode = None
                self.start_factory_reset_confirm()

    # --- Theme picker ---

    def open_theme_picker(self):
        names = sorted(self.theme_registry.keys())
        current = self.cfg.get('theme', 'classic')
        self.theme_picker_cursor = names.index(current) if current in names else 0
        self.mode = 'theme_picker'

    def draw_theme_picker(self):
        h, w = self.stdscr.getmaxyx()
        names = sorted(self.theme_registry.keys())
        current = self.cfg.get('theme', 'classic')
        box_w = min(56, w - 4)
        box_h = min(len(names), h - 8) + 4
        pad = self.dialog_padding()
        y0 = (h - (box_h + 2 * pad)) // 2
        x0 = (w - (box_w + 2 * pad)) // 2
        iy, ix = self.draw_box(y0, x0, box_h + 2 * pad, box_w + 2 * pad, "Switch Theme")
        iy += pad
        ix += pad
        list_h = box_h - 3
        start = max(0, min(self.theme_picker_cursor - list_h // 2, max(0, len(names) - list_h)))
        for i in range(list_h):
            idx = start + i
            if idx >= len(names):
                break
            name = names[idx]
            label = self.theme_registry[name].get('meta', {}).get('name', name)
            marker = "> " if name == current else "  "
            style = PAIR_SELECTION if idx == self.theme_picker_cursor else PAIR_DEFAULT
            self.safe_addstr(self.stdscr, iy + i, ix, self.clip_text(f"{marker}{label}", box_w - 6).ljust(box_w - 6), style)
        self.safe_addstr(self.stdscr, iy + box_h - 2, ix, "[Up/Dn]Move [Enter]Apply [Esc]Close", PAIR_WARNING)

    def handle_theme_picker_input(self, key):
        names = sorted(self.theme_registry.keys())
        if key == 27:
            self.mode = None
        elif key in (curses.KEY_UP, ord('k')):
            if self.theme_picker_cursor > 0:
                self.theme_picker_cursor -= 1
        elif key in (curses.KEY_DOWN, ord('j')):
            if self.theme_picker_cursor < len(names) - 1:
                self.theme_picker_cursor += 1
        elif key in (10, 13):
            self.mode = None
            if names:
                chosen = names[self.theme_picker_cursor]
                self.set_theme(chosen)
                label = self.theme_registry[chosen].get('meta', {}).get('name', chosen)
                self.show_toast(f"Theme: {label}")

    # --- Folder picker (filter view) ---

    def open_folder_picker(self):
        options = ["All Stations (no filter)"] + sorted(self.folders.keys())
        current_label = self.current_folder or "All Stations (no filter)"
        self.folder_picker_cursor = options.index(current_label) if current_label in options else 0
        self.mode = 'folder_picker'

    def handle_folder_picker_input(self, key):
        options = ["All Stations (no filter)"] + sorted(self.folders.keys())
        if key == 27:
            self.mode = None
        elif key in (curses.KEY_UP, ord('k')):
            if self.folder_picker_cursor > 0:
                self.folder_picker_cursor -= 1
        elif key in (curses.KEY_DOWN, ord('j')):
            if self.folder_picker_cursor < len(options) - 1:
                self.folder_picker_cursor += 1
        elif key in (10, 13):
            choice = options[self.folder_picker_cursor]
            self.current_folder = None if choice == "All Stations (no filter)" else choice
            self.mode = None
            self.update_filter()

    # --- Folder management (create / rename / delete folders) ---

    def open_folder_manage(self):
        self.folder_manage_cursor = 0
        self.mode = 'folder_manage'

    def handle_folder_manage_input(self, key):
        names = sorted(self.folders.keys())
        if key == 27:
            self.mode = None
        elif key in (curses.KEY_UP, ord('k')):
            if self.folder_manage_cursor > 0:
                self.folder_manage_cursor -= 1
        elif key in (curses.KEY_DOWN, ord('j')):
            if self.folder_manage_cursor < len(names) - 1:
                self.folder_manage_cursor += 1
        elif key == ord('n'):
            self.folder_name_action = 'create'
            self.folder_name_target = None
            self.folder_name_buffer = ""
            self.mode = 'folder_name_input'
        elif key == ord('r'):
            if names:
                self.folder_name_action = 'rename'
                self.folder_name_target = names[self.folder_manage_cursor]
                self.folder_name_buffer = self.folder_name_target
                self.mode = 'folder_name_input'
        elif key == ord('x'):
            if names:
                self.start_delete_folder_confirm(names[self.folder_manage_cursor])

    def handle_folder_name_input(self, key):
        if key == 27:
            self.mode = 'folder_manage'
            return
        if key in (8, 127, curses.KEY_BACKSPACE):
            self.folder_name_buffer = self.folder_name_buffer[:-1]
            return
        if 32 <= key <= 126:
            self.folder_name_buffer += chr(key)
            return
        if key in (10, 13):
            name = self.folder_name_buffer.strip()
            if not name:
                self.mode = 'folder_manage'
                return
            if self.folder_name_action == 'create':
                if name not in self.folders:
                    self.folders[name] = []
                    self.show_toast(f"Created folder '{name}'.")
                else:
                    self.show_toast(f"Folder '{name}' already exists.")
            else:  # rename
                old = self.folder_name_target
                if name != old and name not in self.folders:
                    self.folders[name] = self.folders.pop(old)
                    if self.current_folder == old:
                        self.current_folder = name
                    self.show_toast(f"Renamed '{old}' to '{name}'.")
                elif name in self.folders and name != old:
                    self.show_toast(f"Folder '{name}' already exists.")
            self.cfg['folders'] = self.folders
            self.config_mgr.save()
            self.mode = 'folder_manage'

    def handle_input(self):
        try:
            key = self.stdscr.getch()
        except curses.error:
            return True

        if key == -1:
            return True

        if key == curses.KEY_RESIZE:
            self.handle_resize()
            return True

        if self.mode == 'onboarding':
            self.cfg['onboarded'] = True
            self.config_mgr.save()
            self.mode = None
            return True

        if self.mode == 'help':
            self.mode = None
            return True

        if self.mode == 'wizard':
            self.handle_wizard_input(key)
            return True

        if self.mode == 'confirm':
            if key in (ord('y'), ord('Y')):
                self.execute_confirm()
            elif key in (ord('n'), ord('N'), 27):
                declined_readd = self.confirm_kind == 'readd_defaults_prompt'
                self.mode = None
                self.confirm_kind = None
                self.confirm_target = None
                if declined_readd:
                    self.sync_defaults()
            return True

        if self.mode == 'tools_menu':
            self.handle_tools_menu_input(key)
            return True

        if self.mode == 'folder_picker':
            self.handle_folder_picker_input(key)
            return True

        if self.mode == 'folder_manage':
            self.handle_folder_manage_input(key)
            return True

        if self.mode == 'folder_name_input':
            self.handle_folder_name_input(key)
            return True

        if self.mode == 'theme_dir_input':
            self.handle_theme_dir_input(key)
            return True

        if self.mode == 'theme_validator':
            self.handle_theme_validator_input(key)
            return True

        if self.mode == 'theme_validator_detail':
            self.handle_theme_validator_detail_input(key)
            return True

        if self.mode == 'theme_picker':
            self.handle_theme_picker_input(key)
            return True

        if self.mode == 'readd_picker':
            self.handle_readd_picker_input(key)
            return True

        if self.search_mode:
            if key in (10, 13):
                self.search_mode = False
            elif key == 27:
                self.search_mode = False
                self.search_query = ""
                self.update_filter()
            elif key in (8, 127, curses.KEY_BACKSPACE):
                self.search_query = self.search_query[:-1]
                self.update_filter()
            elif 32 <= key <= 126:
                self.search_query += chr(key)
                self.update_filter()
            return True

        if key == ord('q'):
            log_debug("Quit requested by user.")
            return False
        elif key in (curses.KEY_UP, ord('k')):
            if self.selected_idx > 0:
                self.selected_idx -= 1
                self.adjust_scroll()
        elif key in (curses.KEY_DOWN, ord('j')):
            if self.selected_idx < len(self.filtered_stations) - 1:
                self.selected_idx += 1
                self.adjust_scroll()
        elif key in (10, 13):
            # Enter on the station that's already loaded pauses/resumes it in
            # place, same as 'p' - it used to unconditionally call
            # play_selected() even for the currently-playing station, which
            # re-sent loadfile and restarted the stream from scratch (hence
            # flashing back to "Loading" instead of pausing). Enter on any
            # *other* station still plays it as normal.
            if (self.is_playing and self.current_station and self.filtered_stations
                    and self.selected_idx < len(self.filtered_stations)
                    and self.filtered_stations[self.selected_idx]['slug'] == self.current_station['slug']):
                self._toggle_pause()
            else:
                self.play_selected()
        elif key == ord('r'):
            if self.filtered_stations:
                self.selected_idx = random.randint(0, len(self.filtered_stations) - 1)
                self.adjust_scroll()
                self.play_selected()
        elif key == ord('f'):
            if self.filtered_stations:
                slug = self.filtered_stations[self.selected_idx]['slug']
                if slug in self.cfg['favorites']:
                    self.cfg['favorites'].remove(slug)
                else:
                    self.cfg['favorites'].append(slug)
                self.config_mgr.save()
        elif key == ord('F'):
            self.show_favorites_only = not self.show_favorites_only
            self.update_filter()
        elif key == ord('s') or key == ord('/'):
            self.search_mode = True
        elif key == ord('a'):
            self.start_add_wizard()
        elif key == ord('e'):
            self.start_edit_wizard()
        elif key == ord('x'):
            self.start_delete_confirm()
        elif key == ord('o'):
            self.open_folder_picker()
        elif key == ord('O'):
            self.open_folder_manage()
        elif key == ord('m'):
            self.open_tools_menu()
        elif key == ord('?'):
            self.mode = 'help'
        elif key in (ord('1'), ord('2'), ord('3')):
            self.workspace_tab = int(chr(key))
        elif key == ord('d'):
            self.show_debug = not self.show_debug
        elif key == ord('p'):
            self._toggle_pause()
        elif key == ord('='):
            self.cfg['volume'] = min(100, self.cfg['volume'] + 5)
            self.mpv.set_volume(self.cfg['volume'])
            self.volume_hud_until = time.time() + 1.2
            self.config_mgr.save()
        elif key == ord('-'):
            self.cfg['volume'] = max(0, self.cfg['volume'] - 5)
            self.mpv.set_volume(self.cfg['volume'])
            self.volume_hud_until = time.time() + 1.2
            self.config_mgr.save()
        elif key == ord('t'):
            if self.sleep_timer_end:
                self.sleep_timer_end = None
            else:
                self.sleep_timer_end = time.time() + (30 * 60)

        return True

    def run(self):
        if self.cfg['last_station']:
            for i, s in enumerate(self.stations):
                if s['slug'] == self.cfg['last_station']:
                    self.selected_idx = i
                    self.adjust_scroll()
                    break

        running = True
        while running:
            if self.sleep_timer_end and time.time() > self.sleep_timer_end:
                self.mpv.stop()
                self._finish_history_entry()
                self.is_playing = False
                self.sleep_timer_end = None
                self.status_msg = "Sleep timer ended"

            self.draw()
            running = self.handle_input()

        self._finish_history_entry()
        self.cfg['history'] = self.history
        self.config_mgr.save()
        self.mpv.quit()

def main(stdscr):
    init_pair_constants()
    app = LofiApp(stdscr)
    app.run()

if __name__ == "__main__":
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass  # fall back to whatever the environment gives us rather than crashing over this
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"App Crashed! Fatal Error: {e}")
        sys.exit(1)
