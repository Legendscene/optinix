"""Keep child processes from flashing a console window on Windows.

The app ships as a windowed (``console=False``) PyInstaller build, so it owns
no console of its own. Every ``tasklist`` / ``reg`` / ``wmic`` / ``powershell``
call the optimizers make therefore allocates a *new* console — which Windows
paints on screen. On a page like Startup or Services that is dozens of black
windows flickering over the UI.

``CREATE_NO_WINDOW`` suppresses the console while still letting us capture
stdout/stderr, which is what the callers already do. Rather than edit ~240
call sites, patch ``subprocess.Popen.__init__`` once at startup: ``run``,
``check_output`` and ``call`` all route through ``Popen``.

Callers that explicitly ask for a console or their own process group keep
their flags untouched — some of them (launching a game, a driver installer)
want a real window.
"""

from __future__ import annotations

import os
import subprocess

_installed = False


def install() -> None:
    """Patch ``subprocess.Popen`` on Windows. Safe to call more than once."""
    global _installed
    if _installed or os.name != "nt":
        return
    _installed = True

    hide = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    explicit = (
        getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
        | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    )

    original = subprocess.Popen.__init__

    def patched_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        flags = kwargs.get("creationflags", 0) or 0
        if not flags & explicit:
            kwargs["creationflags"] = flags | hide
        return original(self, *args, **kwargs)

    subprocess.Popen.__init__ = patched_init  # type: ignore[method-assign]
