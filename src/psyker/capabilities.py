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
    "host.open",
)

WORKER_CAPABILITIES: tuple[str, ...] = TASK_OPERATIONS

TASK_PATH_OPS: frozenset[str] = frozenset(
    {
        "fs.open",
        "fs.create",
        "fs.delete",
        "fs.list",
        "fs.mkdir",
        "host.open",
    }
)

TASK_STRING_OPS: frozenset[str] = frozenset({"exec.ps", "exec.cmd"})

TASK_PATH_PLUS_STRING_OPS: frozenset[str] = frozenset({"fs.write", "fs.update", "fs.append"})

# Command-string patterns blocked by exec.ps / exec.cmd in SANDBOX mode (case-insensitive).
EXEC_SANDBOX_BLOCKED: tuple[str, ...] = (
    r"C:\Windows\System32",
    r"C:\Windows\SysWOW64",
    "%SystemRoot%",
    "%WINDIR%",
    "HKEY_LOCAL_MACHINE",
    "HKEY_CURRENT_USER",
    "HKEY_CLASSES_ROOT",
    "HKEY_USERS",
    "HKEY_CURRENT_CONFIG",
    "HKLM:",
    "HKCU:",
)
