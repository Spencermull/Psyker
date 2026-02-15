"""Frozen entrypoint for PsykerGUI.exe. Forces --gui mode."""

from __future__ import annotations

import sys

# Ensure GUI mode when double-clicked or run without args
if "--gui" not in sys.argv:
    sys.argv.insert(1, "--gui")

from psyker.entry import run

if __name__ == "__main__":
    raise SystemExit(run())
