"""Error types and diagnostic rendering for PSYKER."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class SourceSpan:
    path: Optional[Path]
    line: int
    column: int


class PsykerError(Exception):
    """Base error with optional source location."""

    error_type = "PsykerError"

    def __init__(self, message: str, span: Optional[SourceSpan] = None, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.span = span
        self.hint = hint

    def to_diagnostic(self) -> str:
        location = ""
        if self.span and self.span.path:
            location = f"\n  --> {self.span.path}:{self.span.line}:{self.span.column}"
        hint = f"\n  hint: {self.hint}" if self.hint else ""
        return f"error[{self.error_type}]: {self.message}{location}{hint}"


class SyntaxError(PsykerError):
    error_type = "SyntaxError"


class DialectError(PsykerError):
    error_type = "DialectError"


class ReferenceError(PsykerError):
    error_type = "ReferenceError"


class PermissionError(PsykerError):
    error_type = "PermissionError"


class AccessError(PermissionError):
    error_type = "AccessError"


class SandboxError(PsykerError):
    error_type = "SandboxError"


class ExecError(PsykerError):
    error_type = "ExecError"

