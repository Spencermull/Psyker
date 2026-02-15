"""I/O abstraction for CLI and GUI. Enables both to drive Psyker commands."""

from __future__ import annotations

import re
import sys
from typing import Protocol


ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences for non-TTY output (e.g. GUI)."""
    return ANSI_PATTERN.sub("", text)


class IOAdapter(Protocol):
    """Protocol for CLI and GUI I/O. Both provide an adapter."""

    def write(self, text: str) -> None:
        """Write normal output (newline appended by caller if needed)."""
        ...

    def write_error(self, text: str) -> None:
        """Write error output."""
        ...

    def read_line(self, prompt: str = "") -> str | None:
        """Read one line of input. Optional prompt. Returns None on EOF."""
        ...

    @property
    def supports_colors(self) -> bool:
        """Whether output supports ANSI colors (False for GUI)."""
        ...


class TextIOAdapter:
    """CLI adapter: wraps stdout/stderr and input()."""

    def __init__(
        self,
        out=None,
        err=None,
        read_fn=None,
    ) -> None:
        self._out = out or sys.stdout
        self._err = err or sys.stderr
        # Resolve input at call time so tests can patch builtins.input
        self._read_fn = read_fn if read_fn is not None else (lambda p: __import__("builtins").input(p))

    def write(self, text: str) -> None:
        self._out.write(text + "\n")
        self._out.flush()

    def write_error(self, text: str) -> None:
        self._err.write(text + "\n")
        self._err.flush()

    def read_line(self, prompt: str = "") -> str | None:
        try:
            return self._read_fn(prompt)
        except EOFError:
            return None

    @property
    def supports_colors(self) -> bool:
        return bool(getattr(self._out, "isatty", lambda: False)())
