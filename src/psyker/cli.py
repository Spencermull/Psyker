"""Interactive Psyker Bash CLI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Callable, Dict, Iterable, TextIO

from . import __version__
from .io_layer import IOAdapter, TextIOAdapter
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
WELCOME_LINE = f"Psyker v{__version__} - DSL runtime for terminal automation"
WELCOME_BYLINE = "By Spencer Muller"
PSYKER_BANNER_ASCII = (
    "   ____  _____ __  __ _____ ______ ",
    "  / __ \\/ ___/\\ \\/ / / ___// ____/",
    " / /_/ /\\__ \\  \\  /  \\__ \\/ __/   ",
    "/ ____/___/ /  / /  ___/ / /___   ",
    "/_/    /____/  /_/  /____/_____/  ",
)
ANSI_RESET = "\033[0m"
ANSI_BLUE = "\033[34m"
ANSI_RED = "\033[31m"
ANSI_BRIGHT_BLUE = "\033[94m"
ANSI_CYAN = "\033[96m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
FLAG_PATTERN = re.compile(r"--[a-zA-Z0-9-]+")
PROMPT_TEXT = "PSYKER> "

try:  # optional; enables live highlighting while typing
    from prompt_toolkit import prompt as _pt_prompt
    from prompt_toolkit.document import Document as _pt_Document
    from prompt_toolkit.lexers import Lexer as _pt_Lexer
    from prompt_toolkit.styles import Style as _pt_Style
except Exception:  # pragma: no cover - optional dependency
    _pt_prompt = None
    _pt_Document = None
    _pt_Lexer = None
    _pt_Style = None


@dataclass(frozen=True)
class CommandDef:
    handler: CommandHandler
    usage: str
    description: str


class _PsykerInputLexer:  # prompt_toolkit lexer (duck-typed)
    def __init__(self, commands: set[str]) -> None:
        self._commands = commands

    def lex_document(self, document: "_pt_Document"):  # type: ignore[name-defined]
        text = document.text

        def get_line(_line_number: int) -> list[tuple[str, str]]:
            if not text:
                return []
            parts: list[tuple[str, str]] = []

            # First token (verb) in blue
            m = re.match(r"^\s*(\S+)", text)
            if m:
                start, end = m.span(1)
                prefix = text[:start]
                verb = text[start:end]
                rest = text[end:]
                if prefix:
                    parts.append(("", prefix))
                style = "class:command" if verb in self._commands else ""
                parts.append((style, verb))
                text_to_scan = rest
            else:
                text_to_scan = text

            # Flags (--) in red, everything else default.
            idx = 0
            for fm in FLAG_PATTERN.finditer(text_to_scan):
                if fm.start() > idx:
                    parts.append(("", text_to_scan[idx : fm.start()]))
                parts.append(("class:flag", fm.group(0)))
                idx = fm.end()
            if idx < len(text_to_scan):
                parts.append(("", text_to_scan[idx:]))

            return parts

        return get_line


class PsykerCLI:
    def __init__(
        self,
        runtime: RuntimeState,
        out: TextIO | None = None,
        err: TextIO | None = None,
        io: IOAdapter | None = None,
        verbose: bool = False,
    ) -> None:
        self.runtime = runtime
        self._io = io if io is not None else TextIOAdapter(out=out, err=err)
        self.verbose = verbose
        self._cancel_requested = False
        self.runtime.set_cancel_check(self.is_cancel_requested)
        self.commands: Dict[str, CommandDef] = {}
        self.last_exit_code = 0
        self._register_commands()

    def run_repl(self) -> int:
        self._print_startup_banner()
        self._vprintln(
            f"sandbox root={self.runtime.sandbox.root} workspace={self.runtime.sandbox.workspace}"
        )

        use_prompt_toolkit = (
            _pt_prompt is not None
            and _pt_Style is not None
            and self._io.supports_colors
            and self._stream_is_tty(sys.stdin)
        )

        pt_style = None
        pt_lexer = None
        pt_prompt: object = PROMPT_TEXT
        if use_prompt_toolkit:
            pt_style = _pt_Style.from_dict(
                {
                    "prompt": "ansibrightblue bold",
                    "command": "ansibrightblue bold",
                    "flag": "ansired bold",
                    "": "#c7d5e0",
                }
            )
            pt_lexer = _PsykerInputLexer(set(self.commands.keys()))
            pt_prompt = [("class:prompt", PROMPT_TEXT)]

        while True:
            try:
                if use_prompt_toolkit:
                    try:
                        line = _pt_prompt(  # type: ignore[misc]
                            pt_prompt,
                            style=pt_style,
                            lexer=pt_lexer,
                            include_default_pygments_style=False,
                        )
                    except EOFError:
                        raise
                    except Exception:
                        use_prompt_toolkit = False
                        line = self._io.read_line(PROMPT_TEXT)
                else:
                    line = self._io.read_line(PROMPT_TEXT)
                if line is None:
                    self._io.write("")
                    return self.last_exit_code
                line = line or ""
            except EOFError:
                self._io.write("")
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
        self._register(
            "load",
            self._cmd_load,
            "load <path> | load --dir <path>",
            "Load a .psy/.psya/.psyw file or all such files in a directory.",
        )
        self._register("run", self._cmd_run, "run <agent> <task>", "Run a task through an agent.")
        self._register("open", self._cmd_open, "open <path>", "Print file contents from sandbox workspace.")
        self._register("mkfile", self._cmd_mkfile, "mkfile <path>", "Create a file in sandbox workspace.")
        self._register("mkdir", self._cmd_mkdir, "mkdir <path>", "Create a directory in sandbox workspace.")
        self._register("ps", self._cmd_ps, 'ps "<powershell command>"', "Run a PowerShell command in sandbox workspace.")
        self._register("cmd", self._cmd_cmd, 'cmd "<cmd command>"', "Run a cmd command in sandbox workspace.")
        self._register(
            "sandbox",
            self._cmd_sandbox,
            "sandbox reset [--logs|--clear-logs]",
            "Reset sandbox workspace/tmp (optionally logs).",
        )
        self._register(
            "help",
            self._cmd_help,
            "help [--cmds|--version|--about|<command>]",
            "Show command help and Psyker metadata.",
        )
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
        if len(args) == 1:
            self._load_single_file(Path(args[0]))
            return 0
        if len(args) == 2 and args[0] == "--dir":
            self._load_directory(Path(args[1]))
            return 0
        raise PsykerError("Usage: load <path> | load --dir <path>")

    def _load_single_file(self, path: Path) -> None:
        if path.suffix.lower() not in {".psy", ".psya", ".psyw"}:
            raise DialectError(
                f"Unsupported file extension '{path.suffix}'",
                hint="Use .psy, .psya, or .psyw.",
            )
        self._vprintln(f"load path={path.expanduser().resolve(strict=False)}")
        self.runtime.load_file(path)
        self._println(f"loaded: {path}")

    def _load_directory(self, directory: Path) -> None:
        # Preserve lexical path form so "loaded: <path>" lines match user input
        # instead of a fully canonicalized resolve() form that can differ on CI.
        root = directory.expanduser()
        if not root.exists() or not root.is_dir():
            raise PsykerError(f"Directory not found: {directory}")

        order = {".psyw": 0, ".psya": 1, ".psy": 2}
        files = [
            path
            for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in order
        ]
        files.sort(key=lambda path: (order[path.suffix.lower()], path.name.lower()))

        for path in files:
            self._load_single_file(path)

    def _cmd_run(self, args: list[str]) -> int:
        if len(args) != 2:
            raise PsykerError("Usage: run <agent> <task>")
        self.clear_cancel()
        self._vprintln(f"run agent={args[0]} task={args[1]}")
        try:
            result = self.runtime.run_task(args[0], args[1])
        except ExecError as exc:
            if exc.message.lower().startswith("task cancelled by user"):
                self._println("task cancelled")
                return 130
            raise
        if result.stdout:
            self._println(result.stdout.rstrip("\n"))
        if result.stderr:
            self._eprintln(result.stderr.rstrip("\n"))
        self._vprintln(f"run result status={result.status_code} worker={result.worker}")
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

    def _cmd_sandbox(self, args: list[str]) -> int:
        if not args or args[0] != "reset":
            raise PsykerError("Usage: sandbox reset [--logs|--clear-logs]")
        clear_logs = False
        if len(args) == 2:
            if args[1] not in {"--logs", "--clear-logs"}:
                raise PsykerError("Usage: sandbox reset [--logs|--clear-logs]")
            clear_logs = True
        elif len(args) > 2:
            raise PsykerError("Usage: sandbox reset [--logs|--clear-logs]")
        self.runtime.sandbox.reset(clear_logs=clear_logs)
        if clear_logs:
            self._println("sandbox reset: workspace, tmp, and logs cleared")
        else:
            self._println("sandbox reset: workspace and tmp cleared")
        return 0

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
            raise PsykerError("Usage: help [--cmds|--version|--about|<command>]")
        if len(args) == 1 and args[0] == "--cmds":
            rows = []
            for name in sorted(self.commands):
                command = self.commands[name]
                rows.append([self._color_command(name), self._color_flags(command.usage), command.description])
            self._println(_render_table(["command", "usage", "description"], rows))
            return 0
        if len(args) == 1 and args[0] == "--version":
            self._println(f"Psyker v{__version__}")
            return 0
        if len(args) == 1 and args[0] == "--about":
            self._println(f"{WELCOME_LINE}\n{WELCOME_BYLINE}")
            return 0
        if len(args) == 1:
            if args[0].startswith("--"):
                raise PsykerError(
                    f"Unknown help option '{args[0]}'. Use: help [--cmds|--version|--about|<command>]"
                )
            command = self.commands.get(args[0])
            if command is None:
                raise PsykerError(f"Unknown command '{args[0]}'")
            name = self._color_command(args[0])
            usage = self._color_flags(command.usage)
            self._println(f"{name}: {command.description}\nusage: {usage}")
            return 0
        rows = []
        for name in sorted(self.commands):
            command = self.commands[name]
            rows.append([self._color_command(name), self._color_flags(command.usage), command.description])
        self._println(_render_table(["command", "usage", "description"], rows))
        return 0

    def _cmd_exit(self, args: list[str]) -> int:
        if args:
            raise PsykerError("Usage: exit")
        return 0

    def _print_startup_banner(self) -> None:
        self._println(self._color_banner_line(WELCOME_LINE, color=ANSI_BRIGHT_BLUE, bold=True))
        self._println(self._color_banner_line(WELCOME_BYLINE, color=ANSI_CYAN))

        if self._colors_enabled():
            self._println(self._color_banner_line("[metro] bundling psychic shell...", color=ANSI_BLUE, dim=True))
            self._println(self._color_banner_line("[metro] calibrating hex-eye matrix...", color=ANSI_BLUE, dim=True))

        tones = (ANSI_BRIGHT_BLUE, ANSI_BLUE, ANSI_CYAN, ANSI_BLUE, ANSI_BRIGHT_BLUE)
        center_line = len(PSYKER_BANNER_ASCII) // 2
        for idx, line in enumerate(PSYKER_BANNER_ASCII):
            tone = tones[idx % len(tones)]
            emph = idx in {0, center_line, len(PSYKER_BANNER_ASCII) - 1}
            self._println(self._color_banner_line(line, color=tone, bold=emph))

        if self._colors_enabled():
            self._println(self._color_banner_line("[metro] psychic mesh online", color=ANSI_CYAN, dim=True))
        self._println("")

    def _println(self, text: str) -> None:
        self._io.write(text)

    def _eprintln(self, text: str) -> None:
        self._io.write_error(text)

    def _vprintln(self, text: str) -> None:
        if self.verbose:
            self._eprintln(f"[verbose] {text}")

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def clear_cancel(self) -> None:
        self._cancel_requested = False

    def is_cancel_requested(self) -> bool:
        return self._cancel_requested

    def _stream_is_tty(self, stream: object) -> bool:
        return bool(getattr(stream, "isatty", lambda: False)())

    def _colors_enabled(self) -> bool:
        return self._io.supports_colors

    def _color_command(self, text: str) -> str:
        if not self._colors_enabled():
            return text
        return f"{ANSI_BLUE}{text}{ANSI_RESET}"

    def _color_flags(self, text: str) -> str:
        if not self._colors_enabled():
            return text
        return FLAG_PATTERN.sub(lambda m: f"{ANSI_RED}{m.group(0)}{ANSI_RESET}", text)

    def _color_banner_line(self, text: str, color: str = ANSI_BLUE, bold: bool = False, dim: bool = False) -> str:
        if not self._colors_enabled():
            return text
        prefix = ""
        if dim:
            prefix += ANSI_DIM
        if bold:
            prefix += ANSI_BOLD
        prefix += color
        return f"{prefix}{text}{ANSI_RESET}"


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


def create_default_cli(
    out: TextIO | None = None,
    err: TextIO | None = None,
    *,
    verbose: bool = False,
) -> PsykerCLI:
    runtime = RuntimeState(sandbox=Sandbox.create_default())
    return PsykerCLI(runtime=runtime, out=out, err=err, verbose=verbose)


def _render_table(headers: list[str], rows: Iterable[list[str]]) -> str:
    materialized = [list(row) for row in rows]
    if not materialized:
        return "(empty)"
    widths = [_visible_len(h) for h in headers]
    for row in materialized:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], _visible_len(str(value)))
    header = " | ".join(_ljust_visible(headers[idx], widths[idx]) for idx in range(len(headers)))
    divider = "-+-".join("-" * widths[idx] for idx in range(len(headers)))
    body = "\n".join(
        " | ".join(_ljust_visible(str(row[idx]), widths[idx]) for idx in range(len(headers)))
        for row in materialized
    )
    return f"{header}\n{divider}\n{body}"


def _format_value(value: object) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    if value is None:
        return "null"
    return str(value)


def _visible_len(text: str) -> int:
    return len(ANSI_PATTERN.sub("", text))


def _ljust_visible(text: str, width: int) -> str:
    pad = max(width - _visible_len(text), 0)
    return text + (" " * pad)
