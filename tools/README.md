# tools/

Development tooling for RadioMaster. Not needed to run the app.

- `harness.py` - run `lofi.py` in a real pty and read back what it rendered (needs `pip install pyte`).
- `fake_mpv/mpv` - stub `mpv` the harness puts on `PATH`, so playback states can be tested without mpv installed.
- `compare_apps.py` - render two versions of `lofi.py` through ~200 scenarios and report any screen that differs. Use it before and after any layout/rendering change:

```
git show HEAD:lofi.py > /tmp/lofi_before.py
python3 tools/compare_apps.py /tmp/lofi_before.py lofi.py
```

See PROJECT_REFERENCE.md, "Testing approach".
