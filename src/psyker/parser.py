"""Dialect-aware handwritten parser for PSYKER."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .errors import DialectError, SourceSpan, SyntaxError
from .lexer import tokenize_file
from .model import (
    AccessBlock,
    AgentDef,
    AgentDocument,
    AgentUse,
    TaskDef,
    TaskDocument,
    TaskStmt,
    WorkerAllow,
    WorkerDef,
    WorkerDocument,
)
from .token import Token

_TASK_OPS = {"fs.open", "fs.create", "exec.ps", "exec.cmd"}
_WORKER_CAPS = {"fs.open", "fs.create", "exec.ps", "exec.cmd"}

_TASK_ONLY = {"task", "@access", "agents", "workers"} | _TASK_OPS
_WORKER_ONLY = {"worker", "allow", "sandbox", "cwd"} | _WORKER_CAPS
_AGENT_ONLY = {"agent", "use", "count"}


def parse_path(path: Path) -> TaskDocument | WorkerDocument | AgentDocument:
    suffix = path.suffix.lower()
    parser = Parser(tokenize_file(path), path)
    if suffix == ".psy":
        return parser.parse_task_file()
    if suffix == ".psyw":
        return parser.parse_worker_file()
    if suffix == ".psya":
        return parser.parse_agent_file()
    raise DialectError(
        f"Unsupported file extension '{path.suffix}'",
        SourceSpan(path, 1, 1),
        hint="Use .psy, .psyw, or .psya.",
    )


class Parser:
    def __init__(self, tokens: list[Token], path: Path | None) -> None:
        self.tokens = tokens
        self.path = path
        self.index = 0

    def parse_task_file(self) -> TaskDocument:
        tasks: list[TaskDef] = []
        while not self._at_end():
            if self._match("COMMENT"):
                continue
            self._reject_cross_dialect({"worker", "agent"}, "task files (.psy)")
            tasks.append(self._parse_task_def())
        return TaskDocument(tasks=tuple(tasks))

    def parse_worker_file(self) -> WorkerDocument:
        self._skip_comments()
        self._reject_cross_dialect({"task", "agent", "@access"}, "worker files (.psyw)")
        worker = self._parse_worker_def()
        self._skip_comments()
        self._expect_kind("EOF")
        return WorkerDocument(worker=worker)

    def parse_agent_file(self) -> AgentDocument:
        self._skip_comments()
        self._reject_cross_dialect({"task", "worker", "@access"} | _TASK_OPS, "agent files (.psya)")
        agent = self._parse_agent_def()
        self._skip_comments()
        self._expect_kind("EOF")
        return AgentDocument(agent=agent)

    def _parse_task_def(self) -> TaskDef:
        access = None
        if self._match_keyword("@access"):
            access = self._parse_access_block()
        keyword = self._expect_keyword("task")
        name = self._expect_ident()
        self._expect_symbol("{")
        statements: list[TaskStmt] = []
        while not self._match_symbol("}"):
            self._skip_comments()
            if self._peek_value() == "}":
                self._advance()
                break
            self._reject_cross_dialect({"worker", "agent", "use", "allow", "sandbox", "cwd"}, "task files (.psy)")
            statements.append(self._parse_task_stmt())
            self._skip_comments()
        return TaskDef(name=name.value, access=access, statements=tuple(statements), source_path=self.path)

    def _parse_access_block(self) -> AccessBlock:
        self._expect_symbol("{")
        agents: tuple[str, ...] = ()
        workers: tuple[str, ...] = ()
        if self._peek_value() != "}":
            first_field = self._expect_keyword_any({"agents", "workers"})
            self._expect_symbol(":")
            first_values = self._parse_ident_list()
            if first_field.value == "agents":
                agents = first_values
            else:
                workers = first_values
            if self._match_symbol(","):
                second_field = self._expect_keyword_any({"agents", "workers"})
                if second_field.value == first_field.value:
                    raise SyntaxError(
                        f"Duplicate access field '{second_field.value}'",
                        self._span(second_field),
                        hint="Provide each access field once.",
                    )
                self._expect_symbol(":")
                second_values = self._parse_ident_list()
                if second_field.value == "agents":
                    agents = second_values
                else:
                    workers = second_values
        self._expect_symbol("}")
        return AccessBlock(agents=agents, workers=workers)

    def _parse_ident_list(self) -> tuple[str, ...]:
        self._expect_symbol("[")
        items: list[str] = []
        if self._peek_value() != "]":
            items.append(self._expect_ident().value)
            while self._match_symbol(","):
                items.append(self._expect_ident().value)
        self._expect_symbol("]")
        return tuple(items)

    def _parse_task_stmt(self) -> TaskStmt:
        op = self._expect_keyword_any(_TASK_OPS)
        arg = self._expect_path_or_string()
        self._expect_symbol(";")
        return TaskStmt(op=op.value, arg=arg.value, line=op.line, column=op.column)

    def _parse_worker_def(self) -> WorkerDef:
        self._expect_keyword("worker")
        name = self._expect_ident()
        self._expect_symbol("{")
        sandbox: Optional[str] = None
        cwd: Optional[str] = None
        allows: list[WorkerAllow] = []
        while not self._match_symbol("}"):
            self._skip_comments()
            if self._peek_value() == "}":
                self._advance()
                break
            token = self._peek()
            if token.value in _TASK_ONLY | _AGENT_ONLY:
                raise DialectError(
                    f"'{token.value}' is not allowed in worker files (.psyw)",
                    self._span(token),
                    hint="Use worker statements: sandbox, cwd, allow.",
                )
            if self._match_keyword("sandbox"):
                path_token = self._expect_path_or_string()
                sandbox = path_token.value
                self._expect_symbol(";")
            elif self._match_keyword("cwd"):
                path_token = self._expect_path_or_string()
                cwd = path_token.value
                self._expect_symbol(";")
            elif self._match_keyword("allow"):
                capability_token = self._expect_keyword_any(_WORKER_CAPS, allow_ident=True)
                if capability_token.value not in _WORKER_CAPS:
                    raise SyntaxError(
                        f"Unknown capability '{capability_token.value}'",
                        self._span(capability_token),
                        hint="Use fs.open, fs.create, exec.ps, or exec.cmd.",
                    )
                arg: Optional[str] = None
                if self._peek().kind in {"PATH", "STRING", "IDENT"}:
                    arg = self._advance().value
                self._expect_symbol(";")
                allows.append(
                    WorkerAllow(
                        capability=capability_token.value,
                        arg=arg,
                        line=capability_token.line,
                        column=capability_token.column,
                    )
                )
            else:
                raise SyntaxError(
                    f"Unexpected token '{token.value}' in worker definition",
                    self._span(token),
                    hint="Expected sandbox, cwd, or allow statement.",
                )
            self._skip_comments()
        return WorkerDef(name=name.value, sandbox=sandbox, cwd=cwd, allows=tuple(allows), source_path=self.path)

    def _parse_agent_def(self) -> AgentDef:
        self._expect_keyword("agent")
        name = self._expect_ident()
        self._expect_symbol("{")
        uses: list[AgentUse] = []
        while not self._match_symbol("}"):
            self._skip_comments()
            if self._peek_value() == "}":
                self._advance()
                break
            token = self._peek()
            if token.value in _TASK_ONLY | _WORKER_ONLY:
                raise DialectError(
                    f"'{token.value}' is not allowed in agent files (.psya)",
                    self._span(token),
                    hint="Use only 'use worker <name> count = <int>;'.",
                )
            self._expect_keyword("use")
            self._expect_keyword("worker")
            worker_name = self._expect_ident()
            self._expect_keyword("count")
            self._expect_symbol("=")
            count_token = self._expect_kind("INT")
            self._expect_symbol(";")
            uses.append(
                AgentUse(
                    worker_name=worker_name.value,
                    count=int(count_token.value),
                    line=worker_name.line,
                    column=worker_name.column,
                )
            )
            self._skip_comments()
        return AgentDef(name=name.value, uses=tuple(uses), source_path=self.path)

    def _peek(self) -> Token:
        self._skip_comments()
        return self.tokens[self.index]

    def _peek_value(self) -> str:
        return self._peek().value

    def _advance(self) -> Token:
        token = self.tokens[self.index]
        self.index += 1
        return token

    def _at_end(self) -> bool:
        return self._peek().kind == "EOF"

    def _skip_comments(self) -> None:
        while self.tokens[self.index].kind == "COMMENT":
            self.index += 1

    def _expect_kind(self, kind: str) -> Token:
        token = self._peek()
        if token.kind != kind:
            raise SyntaxError(
                f"Expected token kind '{kind}', got '{token.kind}'",
                self._span(token),
                hint="Check statement syntax.",
            )
        self.index += 1
        return token

    def _expect_symbol(self, value: str) -> Token:
        token = self._peek()
        if token.value != value:
            raise SyntaxError(
                f"Expected '{value}', got '{token.value}'",
                self._span(token),
                hint="Check punctuation and delimiters.",
            )
        self.index += 1
        return token

    def _expect_ident(self) -> Token:
        token = self._peek()
        if token.kind != "IDENT":
            raise SyntaxError(
                f"Expected identifier, got '{token.value}'",
                self._span(token),
                hint="Use an identifier name.",
            )
        self.index += 1
        return token

    def _expect_keyword(self, value: str) -> Token:
        token = self._peek()
        if token.value != value:
            raise SyntaxError(
                f"Expected keyword '{value}', got '{token.value}'",
                self._span(token),
                hint="Check dialect grammar.",
            )
        self.index += 1
        return token

    def _expect_keyword_any(self, values: set[str], allow_ident: bool = False) -> Token:
        token = self._peek()
        kinds = {"KEYWORD"}
        if allow_ident:
            kinds.add("IDENT")
        if token.kind not in kinds or token.value not in values and not (allow_ident and token.kind == "IDENT"):
            expected = ", ".join(sorted(values))
            raise SyntaxError(
                f"Expected one of: {expected}. Got '{token.value}'.",
                self._span(token),
                hint="Check the allowed statement keyword.",
            )
        self.index += 1
        return token

    def _expect_path_or_string(self) -> Token:
        token = self._peek()
        if token.kind not in {"PATH", "STRING"}:
            raise SyntaxError(
                f"Expected path or string, got '{token.value}'",
                self._span(token),
                hint="Use a bare path or a quoted string.",
            )
        self.index += 1
        return token

    def _match(self, kind: str) -> bool:
        token = self._peek()
        if token.kind == kind:
            self.index += 1
            return True
        return False

    def _match_symbol(self, value: str) -> bool:
        token = self._peek()
        if token.value == value:
            self.index += 1
            return True
        return False

    def _match_keyword(self, value: str) -> bool:
        token = self._peek()
        if token.value == value:
            self.index += 1
            return True
        return False

    def _reject_cross_dialect(self, forbidden: set[str], dialect_label: str) -> None:
        token = self._peek()
        if token.value in forbidden:
            raise DialectError(
                f"'{token.value}' is not allowed in {dialect_label}",
                self._span(token),
                hint="Use the correct file extension for this construct.",
            )

    def _span(self, token: Token) -> SourceSpan:
        return SourceSpan(self.path, token.line, token.column)

