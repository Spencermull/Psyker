"""Executable-friendly Psyker entry layer."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from . import __version__
from .cli import create_default_cli
from .sandbox import Sandbox
from .update_check import start_async_update_check


def _ensure_launch_working_directory(sandbox: Sandbox) -> None:
    """Preserve terminal cwd when available, otherwise use sandbox workspace."""
    try:
        cwd = Path.cwd()
    except OSError:
        cwd = None
    if cwd is not None and cwd.exists():
        return
    os.chdir(sandbox.workspace)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="psyker")
    parser.add_argument("--gui", action="store_true", help="Launch GUI instead of CLI")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable troubleshooting logs to stderr",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show Psyker version and exit",
    )
    parser.add_argument(
        "--check-updates",
        action="store_true",
        help="Check once at startup for a newer Psyker version",
    )
    parser.add_argument(
        "--script",
        metavar="FILE",
        help="Load a .psy/.psya/.psyw file before starting (can be repeated)",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--run",
        metavar="AGENT:TASK",
        help="Run a task non-interactively after loading scripts (format: agent:task). Can be repeated.",
        action="append",
        default=[],
    )
    args, _ = parser.parse_known_args()
    return args


def run_gui(*, verbose: bool = False, check_updates: bool = False) -> int:
    """Launch the native desktop GUI. Stub until GUI is implemented."""
    # Lazy-import to avoid loading Qt when running CLI-only
    try:
        from .gui import run_gui_impl
        return run_gui_impl(check_updates=check_updates)
    except ImportError:
        # GUI deps not installed or import failed; fall back to CLI with message
        cli = create_default_cli(verbose=verbose)
        _ensure_launch_working_directory(cli.runtime.sandbox)
        if check_updates:
            start_async_update_check(__version__, cli._io.write_error)
        try:
            cli._io.write_error("GUI dependencies not installed. Run: pip install psyker[gui]")
        except Exception:
            pass  # stderr may be None in frozen GUI context
        return cli.run_repl()


def run() -> int:
    """Create the default runtime and launch REPL or GUI based on args."""
    args = _parse_args()
    if args.version:
        print(f"Psyker v{__version__}")
        return 0
    if args.gui:
        return run_gui(verbose=args.verbose, check_updates=args.check_updates)

    cli = create_default_cli(verbose=args.verbose)
    _ensure_launch_working_directory(cli.runtime.sandbox)
    if args.check_updates:
        start_async_update_check(__version__, cli._io.write_error)

    # Load any --script files in order
    for script_path in getattr(args, "script", []):
        code = cli.execute_line(f'load "{script_path}"')
        if code != 0:
            return code

    # If --run targets provided, execute non-interactively and exit
    if getattr(args, "run", []):
        last_code = 0
        for run_target in getattr(args, "run", []):
            if ":" not in run_target:
                cli._io.write_error(f"error[CliArgs]: --run expects 'agent:task', got '{run_target}'")
                return 1
            agent, task = run_target.split(":", 1)
            last_code = cli.execute_line(f"run {agent} {task}")
            if last_code != 0:
                return last_code
        return last_code

    return cli.run_repl()
