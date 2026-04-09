"""Capability and task-operation registry."""

from __future__ import annotations

TASK_OPERATIONS: tuple[str, ...] = (
    "fs.open",
    "fs.create",
    "fs.write",
    "fs.update",
    "fs.append",
    "fs.delete",
    "fs.list",
    "fs.mkdir",
    "exec.ps",
    "exec.cmd",
)

WORKER_CAPABILITIES: tuple[str, ...] = TASK_OPERATIONS

TASK_PATH_OPS: frozenset[str] = frozenset(
    {
        "fs.open",
        "fs.create",
        "fs.delete",
        "fs.list",
        "fs.mkdir",
    }
)

TASK_STRING_OPS: frozenset[str] = frozenset({"exec.ps", "exec.cmd"})

TASK_PATH_PLUS_STRING_OPS: frozenset[str] = frozenset({"fs.write", "fs.update", "fs.append"})
