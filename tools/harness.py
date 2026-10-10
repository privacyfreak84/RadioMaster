"""Run lofi.py in a real pseudo-terminal, feed it keystrokes, and read back
what it actually rendered (characters + colors) through `pyte`.

This is the project's standard way to reproduce and verify anything visual -
see PROJECT_REFERENCE.md ("Testing approach"). Needs `pip install pyte`.
mpv isn't required: tools/fake_mpv/mpv stands in for it (opens the IPC socket,
answers commands, emits start-file / playback-restart on loadfile).

    python3 tools/harness.py ' ' '\\n'        # dismiss onboarding, play station 1, print screen
"""
import fcntl, json, os, pty, select, struct, sys, tempfile, termios, time
import pyte

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_APP = os.path.join(os.path.dirname(TOOLS_DIR), "lofi.py")


def run(keys=(), cols=191, rows=41, theme="cendre", home=None, settle=1.2, pre_cfg=None, app=DEFAULT_APP):
    """Spawn `app` in a cols x rows pty with a throwaway HOME, send `keys`
    (a list of strings; each is written then given 0.6s to render), and
    return (text_lines, pyte_screen, home).

    The first run in a fresh HOME shows the onboarding screen, which eats
    the first keypress - so most scenarios start with ' ' to dismiss it."""
    home = home or tempfile.mkdtemp(prefix="lofihome_")
    cfg = {"theme": theme, "onboarded": True}
    if pre_cfg:
        cfg.update(pre_cfg)
    with open(os.path.join(home, ".lofi_cli.json"), "w") as f:
        json.dump(cfg, f)
    env = dict(os.environ, HOME=home, TERM="xterm-256color", LANG="C.UTF-8", LC_ALL="C.UTF-8",
               PATH=os.path.join(TOOLS_DIR, "fake_mpv") + os.pathsep + os.environ["PATH"])
    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe(sys.executable, [sys.executable, app], env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    screen = pyte.Screen(cols, rows)
    stream = pyte.ByteStream(screen)

    def pump(t):
        end = time.time() + t
        while time.time() < end:
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                try:
                    data = os.read(fd, 65536)
                except OSError:
                    return
                if not data:
                    return
                stream.feed(data)

    pump(settle)
    for k in keys:
        os.write(fd, k.encode() if isinstance(k, str) else k)
        pump(0.6)
    pump(0.4)
    lines = ["".join(screen.buffer[y][x].data for x in range(cols)).rstrip() for y in range(rows)]
    try:
        os.write(fd, b"q")
        pump(0.3)
        os.kill(pid, 9)
    except Exception:
        pass
    try:
        os.waitpid(pid, 0)
    except Exception:
        pass
    return lines, screen, home


if __name__ == "__main__":
    keys = [k.encode().decode("unicode_escape") for k in sys.argv[1:]]
    lines, _, _ = run(keys)
    for i, l in enumerate(lines):
        print(f"{i:2d}|{l}")
