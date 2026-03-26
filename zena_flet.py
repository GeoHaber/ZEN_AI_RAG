#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
**DEPRECATED** — Use ``app.py`` instead.

zena_flet.py was the original Flet UI.  It has been superseded by app.py
which uses the shared UIBackend protocol and has full feature parity with
the NiceGUI frontend (zena.py).

To migrate, simply run::

    python app.py               # or:  flet run app.py

This file is kept only for backward compatibility and will be removed in a
future release.
"""

import warnings as _w
_w.warn(
    "zena_flet.py is deprecated — use app.py instead. "
    "Run:  python app.py  or  flet run app.py",
    DeprecationWarning,
    stacklevel=1,
)

# ── Legacy entry point: forward to app.py ─────────────────────────────────────
if __name__ == "__main__":
    import subprocess
    import sys
    raise SystemExit(subprocess.call([sys.executable, "app.py"]))

