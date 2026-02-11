"""Executable-friendly Psyker entry layer."""

from __future__ import annotations

from .cli import create_default_cli


def run() -> int:
    """Create the default runtime and launch the REPL."""
    cli = create_default_cli()
    return cli.run_repl()
