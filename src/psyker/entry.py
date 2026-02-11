"""Executable-friendly Psyker entry layer."""

from __future__ import annotations

import os
from pathlib import Path

from .cli import create_default_cli
from .sandbox import Sandbox


def _ensure_launch_working_directory(sandbox: Sandbox) -> None:
    """Preserve terminal cwd when available, otherwise use sandbox workspace."""
    try:
        cwd = Path.cwd()
    except OSError:
        cwd = None
    if cwd is not None and cwd.exists():
        return
    os.chdir(sandbox.workspace)


def run() -> int:
    """Create the default runtime and launch the REPL."""
    cli = create_default_cli()
    _ensure_launch_working_directory(cli.runtime.sandbox)
    return cli.run_repl()
