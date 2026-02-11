from __future__ import annotations

"""
Frozen entrypoint for PyInstaller-built Psyker.exe.

This avoids package-relative imports from src/psyker/__main__.py by importing
the installed package normally and delegating to psyker.entry.run().
"""

from psyker.entry import run


if __name__ == "__main__":
    raise SystemExit(run())

