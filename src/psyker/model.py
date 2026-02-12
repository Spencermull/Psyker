"""AST and runtime model objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional


@dataclass(frozen=True)
class AccessBlock:
    agents: tuple[str, ...] = ()
    workers: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskStmt:
    op: Literal["fs.open", "fs.create", "exec.ps", "exec.cmd"]
    arg: str
    line: int
    column: int


@dataclass(frozen=True)
class TaskDef:
    name: str
    access: Optional[AccessBlock]
    statements: tuple[TaskStmt, ...]
    source_path: Optional[Path]


@dataclass(frozen=True)
class WorkerAllow:
    capability: str
    arg: Optional[str]
    line: int
    column: int


@dataclass(frozen=True)
class WorkerDef:
    name: str
    sandbox: Optional[str]
    cwd: Optional[str]
    allows: tuple[WorkerAllow, ...]
    source_path: Optional[Path]


@dataclass(frozen=True)
class AgentUse:
    worker_name: str
    count: int
    line: int
    column: int


@dataclass(frozen=True)
class AgentDef:
    name: str
    uses: tuple[AgentUse, ...]
    source_path: Optional[Path]


@dataclass(frozen=True)
class TaskDocument:
    tasks: tuple[TaskDef, ...] = ()


@dataclass(frozen=True)
class WorkerDocument:
    worker: WorkerDef


@dataclass(frozen=True)
class AgentDocument:
    agent: AgentDef

