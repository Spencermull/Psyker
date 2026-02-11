"""Sandbox root, path checks, and logging."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil

from .errors import SandboxError


def default_sandbox_root() -> Path:
    env_root = os.environ.get("PSYKER_SANDBOX_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    home = Path.home()
    return (home / "psyker_sandbox").resolve()


@dataclass
class Sandbox:
    root: Path

    @classmethod
    def create_default(cls) -> "Sandbox":
        sandbox = cls(default_sandbox_root())
        sandbox.ensure_layout()
        return sandbox

    @property
    def workspace(self) -> Path:
        return self.root / "workspace"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def tmp(self) -> Path:
        return self.root / "tmp"

    @property
    def log_file(self) -> Path:
        return self.logs / "psyker.log"

    def ensure_layout(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
        self.tmp.mkdir(parents=True, exist_ok=True)

    def resolve_under_root(self, path_value: str) -> Path:
        self.ensure_layout()
        candidate = Path(path_value)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.root / candidate).resolve()
        self._assert_inside_root(resolved)
        return resolved

    def resolve_in_workspace(self, path_value: str) -> Path:
        self.ensure_layout()
        candidate = Path(path_value)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.workspace / candidate).resolve()
        self._assert_inside_root(resolved)
        return resolved

    def reset(self, clear_logs: bool = False) -> None:
        self.ensure_layout()
        for directory in (self.workspace, self.tmp):
            if directory.exists():
                shutil.rmtree(directory)
            directory.mkdir(parents=True, exist_ok=True)
        if clear_logs and self.logs.exists():
            shutil.rmtree(self.logs)
            self.logs.mkdir(parents=True, exist_ok=True)

    def log(self, agent: str, worker: str, operation: str, status: str) -> None:
        self.ensure_layout()
        timestamp = datetime.now(timezone.utc).isoformat()
        line = f"{timestamp}\tagent={agent}\tworker={worker}\top={operation}\tstatus={status}\n"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.write_text(
            (self.log_file.read_text(encoding="utf-8") if self.log_file.exists() else "") + line,
            encoding="utf-8",
        )

    def _assert_inside_root(self, resolved: Path) -> None:
        root_resolved = self.root.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError as exc:
            raise SandboxError(
                f"Path '{resolved}' is outside sandbox root '{root_resolved}'",
                hint="Use a path inside the sandbox.",
            ) from exc

        if resolved.exists():
            real = resolved.resolve()
            try:
                real.relative_to(root_resolved)
            except ValueError as exc:
                raise SandboxError(
                    f"Symlink target '{real}' escapes sandbox root '{root_resolved}'",
                    hint="Use paths that resolve inside the sandbox root.",
                ) from exc

