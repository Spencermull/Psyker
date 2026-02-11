"""Interactive Psyker Bash CLI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Callable, Dict, Iterable, TextIO

from .errors import (
    AccessError,
    DialectError,
    ExecError,
    PermissionError,
    PsykerError,
    SandboxError,
    SyntaxError,
)
from .runtime import RuntimeState
from .sandbox import Sandbox


CommandHandler = Callable[[list[str]], int]


@dataclass(frozen=True)
class CommandDef:
    handler: CommandHandler
    usage: str
    description: str


class PsykerCLI:
    def __init__(self, runtime: RuntimeState, out: TextIO | None = None, err: TextIO | None = None) -> None:
        self.runtime = runtime
        self.out = out or sys.stdout
        self.err = err or sys.stderr
        self.commands: Dict[str, CommandDef] = {}
        self.last_exit_code = 0
        self._register_commands()

    def run_repl(self) -> int:
        while True:
            try:
                line = input("psyker> ")
            except EOFError:
                self._println("")
                return self.last_exit_code
            code = self.execute_line(line)
            self.last_exit_code = code
            if code == 0 and line.strip().lower() in {"exit", "quit"}:
                return 0

    def execute_line(self, line: str) -> int:
        text = line.strip()
        if not text:
            return 0
        try:
            parts = shlex.split(text)
        except ValueError as exc:
            self._eprintln(f"error[CliParse]: {exc}")
            return 1
        if not parts:
            return 0

        verb = parts[0]
        args = parts[1:]
        command = self.commands.get(verb)
        if command is None:
            self._eprintln(f"error[CliCommand]: unknown command '{verb}'")
            return 1

        try:
            return command.handler(args)
        except PsykerError as exc:
            self._eprintln(exc.to_diagnostic())
            return map_error_to_exit_code(exc)
        except Exception as exc:  # pragma: no cover - defensive catch
            self._eprintln(f"error[GeneralError]: {exc}")
            return 1

    def _register_commands(self) -> None:
        self._register("ls", self._cmd_ls, "ls workers|agents|tasks", "List loaded definitions.")
        self._register(
            "stx",
            self._cmd_stx,
            "stx worker|agent|task <name> [--output table|json]",
            "Inspect one loaded definition.",
        )
        self._register("load", self._cmd_load, "load <path>", "Load a .psy/.psya/.psyw file.")
        self._register("run", self._cmd_run, "run <agent> <task>", "Run a task through an agent.")
        self._register("open", self._cmd_open, "open <path>", "Print file contents from sandbox workspace.")
        self._register("mkfile", self._cmd_mkfile, "mkfile <path>", "Create a file in sandbox workspace.")
        self._register("mkdir", self._cmd_mkdir, "mkdir <path>", "Create a directory in sandbox workspace.")
        self._register("ps", self._cmd_ps, 'ps "<powershell command>"', "Run a PowerShell command in sandbox workspace.")
        self._register("cmd", self._cmd_cmd, 'cmd "<cmd command>"', "Run a cmd command in sandbox workspace.")
        self._register("help", self._cmd_help, "help [command]", "Show command help.")
        self._register("exit", self._cmd_exit, "exit", "Exit the REPL.")
        self._register("quit", self._cmd_exit, "quit", "Exit the REPL.")

    def _register(self, verb: str, handler: CommandHandler, usage: str, description: str) -> None:
        self.commands[verb] = CommandDef(handler=handler, usage=usage, description=description)

    def _cmd_ls(self, args: list[str]) -> int:
        if len(args) != 1 or args[0] not in {"workers", "agents", "tasks"}:
            raise PsykerError("Usage: ls workers|agents|tasks")
        target = args[0]
        if target == "workers":
            rows = [
                [name, "worker", str(len(worker.allows))]
                for name, worker in sorted(self.runtime.workers.items())
            ]
            self._println(_render_table(["name", "type", "capabilities"], rows))
            return 0
        if target == "agents":
            rows = []
            for name, agent in sorted(self.runtime.agents.items()):
                count = sum(item.count for item in agent.uses)
                rows.append([name, "agent", str(count)])
            self._println(_render_table(["name", "type", "worker_instances"], rows))
            return 0
        rows = []
        for name, task in sorted(self.runtime.tasks.items()):
            rows.append([name, "task", str(len(task.statements))])
        self._println(_render_table(["name", "type", "statements"], rows))
        return 0

    def _cmd_stx(self, args: list[str]) -> int:
        if len(args) < 2:
            raise PsykerError("Usage: stx worker|agent|task <name> [--output table|json]")
        kind = args[0]
        name = args[1]
        output = "table"
        if len(args) > 2:
            if len(args) != 4 or args[2] != "--output" or args[3] not in {"table", "json"}:
                raise PsykerError("Usage: stx worker|agent|task <name> [--output table|json]")
            output = args[3]

        data = self._inspect_object(kind, name)
        if output == "json":
            self._println(json.dumps(data, indent=2, sort_keys=True, default=str))
            return 0

        rows = [[key, _format_value(value)] for key, value in data.items()]
        self._println(_render_table(["field", "value"], rows))
        return 0

    def _inspect_object(self, kind: str, name: str) -> dict:
        if kind == "worker":
            worker = self.runtime.workers.get(name)
            if worker is None:
                raise PsykerError(f"Unknown worker '{name}'")
            return asdict(worker)
        if kind == "agent":
            agent = self.runtime.agents.get(name)
            if agent is None:
                raise PsykerError(f"Unknown agent '{name}'")
            return asdict(agent)
        if kind == "task":
            task = self.runtime.tasks.get(name)
            if task is None:
                raise PsykerError(f"Unknown task '{name}'")
            return asdict(task)
        raise PsykerError("stx target must be one of: worker, agent, task")

    def _cmd_load(self, args: list[str]) -> int:
        if len(args) != 1:
            raise PsykerError("Usage: load <path>")
        path = Path(args[0])
        if path.suffix.lower() not in {".psy", ".psya", ".psyw"}:
            raise DialectError(
                f"Unsupported file extension '{path.suffix}'",
                hint="Use .psy, .psya, or .psyw.",
            )
        self.runtime.load_file(path)
        self._println(f"loaded: {path}")
        return 0

    def _cmd_run(self, args: list[str]) -> int:
        if len(args) != 2:
            raise PsykerError("Usage: run <agent> <task>")
        result = self.runtime.run_task(args[0], args[1])
        if result.stdout:
            self._println(result.stdout.rstrip("\n"))
        if result.stderr:
            self._eprintln(result.stderr.rstrip("\n"))
        self._println(f"status={result.status_code} agent={result.agent} worker={result.worker} task={result.task}")
        return result.status_code

    def _cmd_open(self, args: list[str]) -> int:
        if len(args) != 1:
            raise PsykerError("Usage: open <path>")
        target = self.runtime.sandbox.resolve_in_workspace(args[0])
        if not target.exists() or not target.is_file():
            raise ExecError(f"File not found: {target}")
        self._println(target.read_text(encoding="utf-8"))
        return 0

    def _cmd_mkfile(self, args: list[str]) -> int:
        if len(args) != 1:
            raise PsykerError("Usage: mkfile <path>")
        target = self.runtime.sandbox.resolve_in_workspace(args[0])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch(exist_ok=True)
        self._println(f"created file: {target}")
        return 0

    def _cmd_mkdir(self, args: list[str]) -> int:
        if len(args) != 1:
            raise PsykerError("Usage: mkdir <path>")
        target = self.runtime.sandbox.resolve_in_workspace(args[0])
        target.mkdir(parents=True, exist_ok=True)
        self._println(f"created dir: {target}")
        return 0

    def _cmd_ps(self, args: list[str]) -> int:
        if len(args) != 1:
            raise PsykerError('Usage: ps "<powershell command>"')
        return self._run_cli_exec(["powershell", "-NoProfile", "-Command", args[0]])

    def _cmd_cmd(self, args: list[str]) -> int:
        if len(args) != 1:
            raise PsykerError('Usage: cmd "<cmd command>"')
        return self._run_cli_exec(["cmd", "/c", args[0]])

    def _run_cli_exec(self, command: list[str]) -> int:
        cwd = self.runtime.sandbox.workspace
        cwd.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
        except OSError as exc:
            raise ExecError(f"Failed to execute '{command[0]}': {exc}") from exc
        if proc.stdout:
            self._println(proc.stdout.rstrip("\n"))
        if proc.stderr:
            self._eprintln(proc.stderr.rstrip("\n"))
        if proc.returncode != 0:
            raise ExecError(f"Command failed with exit code {proc.returncode}")
        return 0

    def _cmd_help(self, args: list[str]) -> int:
        if len(args) > 1:
            raise PsykerError("Usage: help [command]")
        if len(args) == 1:
            command = self.commands.get(args[0])
            if command is None:
                raise PsykerError(f"Unknown command '{args[0]}'")
            self._println(f"{args[0]}: {command.description}\nusage: {command.usage}")
            return 0
        rows = []
        for name in sorted(self.commands):
            command = self.commands[name]
            rows.append([name, command.usage, command.description])
        self._println(_render_table(["command", "usage", "description"], rows))
        return 0

    def _cmd_exit(self, args: list[str]) -> int:
        if args:
            raise PsykerError("Usage: exit")
        return 0

    def _println(self, text: str) -> None:
        self.out.write(text + "\n")
        self.out.flush()

    def _eprintln(self, text: str) -> None:
        self.err.write(text + "\n")
        self.err.flush()


def map_error_to_exit_code(exc: Exception) -> int:
    if isinstance(exc, (SyntaxError, DialectError)):
        return 2
    if isinstance(exc, (AccessError, PermissionError)):
        return 3
    if isinstance(exc, SandboxError):
        return 4
    if isinstance(exc, ExecError):
        return 5
    return 1


def create_default_cli(out: TextIO | None = None, err: TextIO | None = None) -> PsykerCLI:
    runtime = RuntimeState(sandbox=Sandbox.create_default())
    return PsykerCLI(runtime=runtime, out=out, err=err)


def _render_table(headers: list[str], rows: Iterable[list[str]]) -> str:
    materialized = [list(row) for row in rows]
    if not materialized:
        return "(empty)"
    widths = [len(h) for h in headers]
    for row in materialized:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(str(value)))
    header = " | ".join(headers[idx].ljust(widths[idx]) for idx in range(len(headers)))
    divider = "-+-".join("-" * widths[idx] for idx in range(len(headers)))
    body = "\n".join(
        " | ".join(str(row[idx]).ljust(widths[idx]) for idx in range(len(headers)))
        for row in materialized
    )
    return f"{header}\n{divider}\n{body}"


def _format_value(value: object) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    if value is None:
        return "null"
    return str(value)
