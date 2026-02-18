"""Pygls-based language server for Psyker diagnostics and editor features."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict
from urllib.parse import unquote, urlparse

from lsprotocol.types import (
    CompletionItem,
    CompletionItemKind,
    CompletionParams,
    DefinitionParams,
    Diagnostic,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DocumentSymbol,
    DocumentSymbolParams,
    Hover,
    HoverParams,
    Location,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
    SymbolKind,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DOCUMENT_SYMBOL,
    TEXT_DOCUMENT_HOVER,
)
from pygls.lsp.server import LanguageServer

from psyker.errors import DialectError, PsykerError, ReferenceError, SourceSpan, SyntaxError
from psyker.lexer import tokenize
from psyker.model import AgentDocument, TaskDocument, WorkerDocument
from psyker.parser import Parser
from psyker.validator import ValidationContext, validate_document

SERVER_NAME = "psyker-lsp"
SERVER_VERSION = "0.1.1"

_TASK_NAME_RE = re.compile(r"^\s*task\s+([A-Za-z][A-Za-z0-9_-]*)\b")
_AGENT_NAME_RE = re.compile(r"^\s*agent\s+([A-Za-z][A-Za-z0-9_-]*)\b")
_WORKER_NAME_RE = re.compile(r"^\s*worker\s+([A-Za-z][A-Za-z0-9_-]*)\b")
_AGENTS_LIST_RE = re.compile(r"@access\s*\{[^}]*\bagents\s*:\s*\[[^\]]*$", re.DOTALL)
_WORKERS_LIST_RE = re.compile(r"@access\s*\{[^}]*\bworkers\s*:\s*\[[^\]]*$", re.DOTALL)
_USE_WORKER_RE = re.compile(r"\buse\s+worker\s+[A-Za-z0-9_-]*$")
_TASK_NAME_CONTEXT_RE = re.compile(r"^\s*task\s+[A-Za-z0-9_-]*$")
_ALLOW_CAPABILITY_RE = re.compile(r"^\s*allow\s+[A-Za-z0-9_.-]*$")
_PROJECT_ROOT_MARKERS = (".git", "pyproject.toml")

_CTX_DEFAULT = "default"
_CTX_ACCESS_AGENTS = "access_agents"
_CTX_ACCESS_WORKERS = "access_workers"
_CTX_USE_WORKER = "use_worker"
_CTX_TASK_NAME = "task_name"
_CTX_ALLOW_CAPABILITY = "allow_capability"

_KEYWORDS_BY_SUFFIX = {
    ".psy": ["task", "@access", "agents", "workers", "fs.open", "fs.create", "exec.ps", "exec.cmd"],
    ".psya": ["agent", "use", "worker", "count"],
    ".psyw": ["worker", "allow", "sandbox", "cwd", "fs.open", "fs.create", "exec.ps", "exec.cmd"],
}

_HOVER_TEXT_BY_WORD = {
    "task": "Task block in .psy files. Contains ordered execution statements.",
    "@access": "Access gate for a task. Limits which agents/workers can run the task.",
    "agents": "Allowed agent names for @access. Omit or leave empty to deny by default.",
    "workers": "Allowed worker names for @access. Omit or leave empty to deny by default.",
    "agent": "Agent definition in .psya. Binds one or more workers via use statements.",
    "use": "Declare worker usage in an agent: use worker <name> count = <int>;",
    "worker": "Worker definition in .psyw or a worker reference in .psya/.psy @access.",
    "count": "Number of worker instances used by an agent declaration.",
    "allow": "Worker capability grant. Controls which operations the worker may execute.",
    "sandbox": "Worker sandbox root path. All file operations stay under this root.",
    "cwd": "Default command working directory for worker shell execution.",
    "fs.open": "Read a file from sandbox scope (requires worker allow fs.open).",
    "fs.create": "Create/write files in sandbox scope (requires worker allow fs.create).",
    "exec.ps": "Execute a PowerShell command in sandbox cwd (requires allow exec.ps).",
    "exec.cmd": "Execute a cmd command in sandbox cwd (requires allow exec.cmd).",
}


@dataclass
class OpenDocument:
    path: Path
    text: str = ""
    ast: object | None = None


@dataclass(frozen=True)
class SymbolRecord:
    name: str
    kind: str
    path: Path
    line: int
    column: int
    summary: str


@dataclass
class WorkspaceIndex:
    tasks: dict[str, list[SymbolRecord]]
    agents: dict[str, list[SymbolRecord]]
    workers: dict[str, list[SymbolRecord]]


class PsykerLanguageServer(LanguageServer):
    def __init__(self) -> None:
        super().__init__(SERVER_NAME, SERVER_VERSION)
        self.open_documents: Dict[str, OpenDocument] = {}
        self._index_dirty = True
        self._index: WorkspaceIndex | None = None

    def mark_index_dirty(self) -> None:
        self._index_dirty = True


server = PsykerLanguageServer()


@server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: PsykerLanguageServer, params: DidOpenTextDocumentParams) -> None:
    _parse_and_publish(ls, params.text_document.uri, params.text_document.text)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: PsykerLanguageServer, params: DidChangeTextDocumentParams) -> None:
    changes = params.content_changes
    if not changes:
        return
    _parse_and_publish(ls, params.text_document.uri, changes[-1].text)


@server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: PsykerLanguageServer, params: DidCloseTextDocumentParams) -> None:
    uri = params.text_document.uri
    ls.open_documents.pop(uri, None)
    ls.mark_index_dirty()
    ls.publish_diagnostics(uri, [])


@server.feature(TEXT_DOCUMENT_COMPLETION)
def completion(ls: PsykerLanguageServer, params: CompletionParams) -> list[CompletionItem]:
    uri = params.text_document.uri
    suffix = _suffix_for_uri(ls, uri)
    open_doc = ls.open_documents.get(uri)
    context = _CTX_DEFAULT
    if open_doc is not None:
        context = completion_context_for_position(open_doc.text, params.position, suffix)

    index = _get_workspace_index(ls, uri)
    if context == _CTX_ACCESS_AGENTS:
        return _identifier_items(agent_names_from_index(index))
    if context in {_CTX_ACCESS_WORKERS, _CTX_USE_WORKER}:
        return _identifier_items(worker_names_from_index(index))
    if context == _CTX_TASK_NAME:
        return _identifier_items(task_names_from_index(index))
    if context == _CTX_ALLOW_CAPABILITY:
        return _keyword_items(["fs.open", "fs.create", "exec.ps", "exec.cmd"])

    return _keyword_items(keywords_for_suffix(suffix))


@server.feature(TEXT_DOCUMENT_HOVER)
def hover(ls: PsykerLanguageServer, params: HoverParams) -> Hover | None:
    uri = params.text_document.uri
    open_doc = ls.open_documents.get(uri)
    if open_doc is None:
        return None
    word = _word_at_position(open_doc.text, params.position)
    if word is None:
        return None

    keyword_text = hover_text_for_word(word)
    if keyword_text is not None:
        return Hover(contents=MarkupContent(kind=MarkupKind.PlainText, value=keyword_text))

    identifier_text = _hover_text_for_identifier(_get_workspace_index(ls, uri), word)
    if identifier_text is None:
        return None
    return Hover(contents=MarkupContent(kind=MarkupKind.PlainText, value=identifier_text))


@server.feature(TEXT_DOCUMENT_DEFINITION)
def definition(ls: PsykerLanguageServer, params: DefinitionParams) -> list[Location] | None:
    uri = params.text_document.uri
    open_doc = ls.open_documents.get(uri)
    if open_doc is None:
        return None
    word = _word_at_position(open_doc.text, params.position)
    if word is None:
        return None
    target_kind = definition_target_kind_for_position(open_doc.text, params.position, open_doc.path.suffix.lower())
    if target_kind is None:
        return None

    index = _get_workspace_index(ls, uri)
    records = _records_for_name(index, word, target_kind)
    if not records:
        return None
    return [_location_for_record(record) for record in records]


@server.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbol(ls: PsykerLanguageServer, params: DocumentSymbolParams) -> list[DocumentSymbol]:
    uri = params.text_document.uri
    open_doc = ls.open_documents.get(uri)
    if open_doc is None:
        return []
    spans = definition_spans_for_text(open_doc.text, open_doc.path.suffix.lower())
    return [_document_symbol_from_span(span) for span in spans]


def _parse_and_publish(ls: PsykerLanguageServer, uri: str, text: str) -> None:
    path = uri_to_path(uri)
    try:
        document = parse_text(path, text)
        ls.open_documents[uri] = OpenDocument(path=path, text=text, ast=document)
        _validate_optional_references(ls, uri, document)
        ls.mark_index_dirty()
        ls.publish_diagnostics(uri, [])
    except (SyntaxError, DialectError, ReferenceError) as exc:
        ls.open_documents[uri] = OpenDocument(path=path, text=text, ast=None)
        ls.mark_index_dirty()
        ls.publish_diagnostics(uri, [to_lsp_diagnostic(exc, path)])
    except PsykerError as exc:
        ls.open_documents[uri] = OpenDocument(path=path, text=text, ast=None)
        ls.mark_index_dirty()
        ls.publish_diagnostics(uri, [to_lsp_diagnostic(exc, path)])


def _validate_optional_references(ls: PsykerLanguageServer, uri: str, document: object) -> None:
    if not isinstance(document, AgentDocument):
        return
    workers: Dict[str, object] = {}
    for item in ls.open_documents.values():
        if isinstance(item.ast, WorkerDocument):
            workers[item.ast.worker.name] = item.ast.worker
    context = ValidationContext(workers=workers, agents={}, tasks={})
    validate_document(document, context)


def parse_text(path: Path, text: str) -> object:
    suffix = path.suffix.lower()
    tokens = tokenize(text, path=path)
    parser = Parser(tokens, path)
    if suffix == ".psy":
        return parser.parse_task_file()
    if suffix == ".psya":
        return parser.parse_agent_file()
    if suffix == ".psyw":
        return parser.parse_worker_file()
    raise DialectError(
        f"Unsupported file extension '{path.suffix}'",
        SourceSpan(path, 1, 1),
        hint="Use .psy, .psya, or .psyw.",
    )


def to_lsp_diagnostic(exc: PsykerError, default_path: Path) -> Diagnostic:
    span = exc.span or SourceSpan(default_path, 1, 1)
    if span.path is None:
        span = SourceSpan(default_path, span.line, span.column)
    line = max(span.line - 1, 0)
    col = max(span.column - 1, 0)
    normalized_error = type(exc)(exc.message, span=span, hint=exc.hint)
    message = normalized_error.to_diagnostic()
    return Diagnostic(
        range=Range(
            start=Position(line=line, character=col),
            end=Position(line=line, character=col + 1),
        ),
        severity=DiagnosticSeverity.Error,
        source=SERVER_NAME,
        message=message,
    )


def uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return Path(uri)
    return Path(unquote(parsed.path.lstrip("/")))


def keywords_for_suffix(suffix: str) -> list[str]:
    return list(_KEYWORDS_BY_SUFFIX.get(suffix.lower(), []))


def worker_names_from_open_docs(open_documents: Dict[str, OpenDocument]) -> list[str]:
    worker_names = {
        item.ast.worker.name
        for item in open_documents.values()
        if isinstance(item.ast, WorkerDocument)
    }
    return sorted(worker_names)


def hover_text_for_word(word: str) -> str | None:
    return _HOVER_TEXT_BY_WORD.get(word)


def completion_context_for_position(text: str, position: Position, suffix: str) -> str:
    suffix = suffix.lower()
    prefix = _text_prefix_at_position(text, position)
    line_prefix = _line_prefix_at_position(text, position)

    if suffix == ".psy":
        if _AGENTS_LIST_RE.search(prefix):
            return _CTX_ACCESS_AGENTS
        if _WORKERS_LIST_RE.search(prefix):
            return _CTX_ACCESS_WORKERS
        if _TASK_NAME_CONTEXT_RE.match(line_prefix):
            return _CTX_TASK_NAME
    if suffix == ".psya" and _USE_WORKER_RE.search(line_prefix):
        return _CTX_USE_WORKER
    if suffix == ".psyw" and _ALLOW_CAPABILITY_RE.match(line_prefix):
        return _CTX_ALLOW_CAPABILITY
    return _CTX_DEFAULT


def definition_target_kind_for_position(text: str, position: Position, suffix: str) -> str | None:
    suffix = suffix.lower()
    prefix = _text_prefix_at_position(text, position)
    line_prefix = _line_prefix_at_position(text, position)
    if suffix == ".psya" and _USE_WORKER_RE.search(line_prefix):
        return "worker"
    if suffix == ".psy" and _AGENTS_LIST_RE.search(prefix):
        return "agent"
    if suffix == ".psy" and _WORKERS_LIST_RE.search(prefix):
        return "worker"
    return None


def definition_spans_for_text(text: str, suffix: str) -> list[tuple[str, str, int, int, int, int]]:
    suffix = suffix.lower()
    spans: list[tuple[str, str, int, int, int, int]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        pattern: re.Pattern[str] | None = None
        kind = ""
        if suffix == ".psy":
            pattern = _TASK_NAME_RE
            kind = "task"
        elif suffix == ".psya":
            pattern = _AGENT_NAME_RE
            kind = "agent"
        elif suffix == ".psyw":
            pattern = _WORKER_NAME_RE
            kind = "worker"
        if pattern is None:
            continue
        match = pattern.match(line)
        if not match:
            continue
        name = match.group(1)
        start_col = max(match.start(1), 0)
        end_line = _find_block_end_line(lines, index)
        end_col = len(lines[end_line]) if end_line < len(lines) else len(line)
        spans.append((name, kind, index + 1, start_col + 1, end_line + 1, end_col + 1))
    return spans


def _get_workspace_index(ls: PsykerLanguageServer, context_uri: str | None = None) -> WorkspaceIndex:
    if ls._index is not None and not ls._index_dirty:
        return ls._index
    index = WorkspaceIndex(tasks={}, agents={}, workers={})
    path_to_open_doc = {doc.path.resolve(): doc for doc in ls.open_documents.values()}
    roots = _workspace_roots(ls, context_uri)
    candidate_paths: dict[Path, None] = {}
    for root in roots:
        for pattern in ("*.psy", "*.psya", "*.psyw"):
            for item in root.rglob(pattern):
                candidate_paths[item.resolve()] = None
    for open_path in path_to_open_doc:
        candidate_paths[open_path] = None

    for path in sorted(candidate_paths):
        open_doc = path_to_open_doc.get(path)
        if open_doc is not None:
            text = open_doc.text
            ast = open_doc.ast
        else:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            try:
                ast = parse_text(path, text)
            except PsykerError:
                ast = None
        for record in _records_from_document(path, text, ast):
            _add_record(index, record)

    ls._index = index
    ls._index_dirty = False
    return index


def _records_from_document(path: Path, text: str, ast: object | None) -> list[SymbolRecord]:
    spans = definition_spans_for_text(text, path.suffix.lower())
    records: list[SymbolRecord] = []

    task_map: dict[str, list[object]] = {}
    agent_map: dict[str, list[object]] = {}
    worker_map: dict[str, list[object]] = {}
    if isinstance(ast, TaskDocument):
        for task in ast.tasks:
            task_map.setdefault(task.name, []).append(task)
    elif isinstance(ast, AgentDocument):
        agent_map.setdefault(ast.agent.name, []).append(ast.agent)
    elif isinstance(ast, WorkerDocument):
        worker_map.setdefault(ast.worker.name, []).append(ast.worker)

    for name, kind, line, column, _, _ in spans:
        summary = f"{kind} definition"
        if kind == "task":
            task_values = task_map.get(name, [])
            task = task_values.pop(0) if task_values else None
            if task is not None:
                access = task.access
                access_summary = "deny-all"
                if access is not None:
                    access_summary = f"agents={list(access.agents)}, workers={list(access.workers)}"
                summary = f"{len(task.statements)} statement(s), access {access_summary}"
        elif kind == "agent":
            agent_values = agent_map.get(name, [])
            agent = agent_values.pop(0) if agent_values else None
            if agent is not None:
                summary = f"{len(agent.uses)} use declaration(s)"
        elif kind == "worker":
            worker_values = worker_map.get(name, [])
            worker = worker_values.pop(0) if worker_values else None
            if worker is not None:
                capabilities = sorted({allow.capability for allow in worker.allows})
                summary = f"capabilities={capabilities}, sandbox={worker.sandbox}, cwd={worker.cwd}"
        records.append(
            SymbolRecord(
                name=name,
                kind=kind,
                path=path,
                line=line,
                column=column,
                summary=summary,
            )
        )
    return records


def _add_record(index: WorkspaceIndex, record: SymbolRecord) -> None:
    if record.kind == "task":
        index.tasks.setdefault(record.name, []).append(record)
    elif record.kind == "agent":
        index.agents.setdefault(record.name, []).append(record)
    elif record.kind == "worker":
        index.workers.setdefault(record.name, []).append(record)


def _records_for_name(index: WorkspaceIndex, name: str, kind: str) -> list[SymbolRecord]:
    if kind == "task":
        return index.tasks.get(name, [])
    if kind == "agent":
        return index.agents.get(name, [])
    if kind == "worker":
        return index.workers.get(name, [])
    return []


def worker_names_from_index(index: WorkspaceIndex) -> list[str]:
    return sorted(index.workers.keys())


def agent_names_from_index(index: WorkspaceIndex) -> list[str]:
    return sorted(index.agents.keys())


def task_names_from_index(index: WorkspaceIndex) -> list[str]:
    return sorted(index.tasks.keys())


def _hover_text_for_identifier(index: WorkspaceIndex, word: str) -> str | None:
    records = index.tasks.get(word, []) + index.agents.get(word, []) + index.workers.get(word, [])
    if not records:
        return None
    primary = records[0]
    location_text = primary.path.as_posix()
    return f"{primary.kind} `{primary.name}`\nDefined in {location_text}:{primary.line}:{primary.column}\n{primary.summary}"


def _location_for_record(record: SymbolRecord) -> Location:
    start_line = max(record.line - 1, 0)
    start_col = max(record.column - 1, 0)
    end_col = start_col + max(len(record.name), 1)
    return Location(
        uri=record.path.resolve().as_uri(),
        range=Range(
            start=Position(line=start_line, character=start_col),
            end=Position(line=start_line, character=end_col),
        ),
    )


def _document_symbol_from_span(span: tuple[str, str, int, int, int, int]) -> DocumentSymbol:
    name, kind, line, col, end_line, end_col = span
    symbol_kind = SymbolKind.Object
    if kind == "task":
        symbol_kind = SymbolKind.Function
    elif kind == "agent":
        symbol_kind = SymbolKind.Class
    elif kind == "worker":
        symbol_kind = SymbolKind.Struct
    start = Position(line=max(line - 1, 0), character=max(col - 1, 0))
    end = Position(line=max(end_line - 1, 0), character=max(end_col - 1, 0))
    return DocumentSymbol(
        name=name,
        kind=symbol_kind,
        range=Range(start=start, end=end),
        selection_range=Range(start=start, end=Position(line=start.line, character=start.character + len(name))),
    )


def _workspace_roots(ls: PsykerLanguageServer, context_uri: str | None) -> list[Path]:
    roots: list[Path] = []
    try:
        folders = ls.workspace.folders  # type: ignore[attr-defined]
    except Exception:
        folders = None
    if isinstance(folders, dict):
        for folder in folders.values():
            uri = getattr(folder, "uri", None)
            if uri:
                roots.append(uri_to_path(uri))
    elif isinstance(folders, list):
        for folder in folders:
            uri = getattr(folder, "uri", None)
            if uri:
                roots.append(uri_to_path(uri))

    if roots:
        return [root.resolve() for root in roots if root.exists()]

    fallback = None
    if context_uri is not None:
        fallback = uri_to_path(context_uri)
    elif ls.open_documents:
        fallback = next(iter(ls.open_documents.values())).path
    if fallback is None:
        return []
    return [_guess_project_root(fallback)]


def _guess_project_root(path: Path) -> Path:
    current = path.resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current] + list(current.parents):
        if any((candidate / marker).exists() for marker in _PROJECT_ROOT_MARKERS):
            return candidate
    return current


def _keyword_items(keywords: list[str]) -> list[CompletionItem]:
    return [CompletionItem(label=keyword, kind=CompletionItemKind.Keyword) for keyword in keywords]


def _identifier_items(names: list[str]) -> list[CompletionItem]:
    return [CompletionItem(label=name, kind=CompletionItemKind.Variable) for name in names]


def _suffix_for_uri(ls: PsykerLanguageServer, uri: str) -> str:
    open_doc = ls.open_documents.get(uri)
    if open_doc is not None:
        return open_doc.path.suffix.lower()
    return uri_to_path(uri).suffix.lower()


def _is_word_char(char: str) -> bool:
    return char.isalnum() or char in {"_", ".", "@"}


def _word_at_position(text: str, position: Position) -> str | None:
    lines = text.splitlines()
    if position.line < 0 or position.line >= len(lines):
        return None
    line = lines[position.line]
    if not line:
        return None
    index = min(max(position.character, 0), len(line))
    if index == len(line):
        index -= 1
    if index < 0:
        return None
    if not _is_word_char(line[index]):
        if index == 0 or not _is_word_char(line[index - 1]):
            return None
        index -= 1
    start = index
    while start > 0 and _is_word_char(line[start - 1]):
        start -= 1
    end = index + 1
    while end < len(line) and _is_word_char(line[end]):
        end += 1
    word = line[start:end]
    if not any(char.isalpha() for char in word):
        return None
    return word


def _text_prefix_at_position(text: str, position: Position) -> str:
    lines = text.splitlines(keepends=True)
    if position.line < 0:
        return ""
    if position.line >= len(lines):
        return text
    prefix = "".join(lines[: position.line])
    line = lines[position.line]
    return prefix + line[: min(max(position.character, 0), len(line))]


def _line_prefix_at_position(text: str, position: Position) -> str:
    lines = text.splitlines()
    if position.line < 0 or position.line >= len(lines):
        return ""
    line = lines[position.line]
    return line[: min(max(position.character, 0), len(line))]


def _find_block_end_line(lines: list[str], start_line: int) -> int:
    depth = 0
    started = False
    for index in range(start_line, len(lines)):
        line = lines[index]
        for char in line:
            if char == "{":
                depth += 1
                started = True
            elif char == "}":
                depth -= 1
                if started and depth <= 0:
                    return index
    return start_line


def run() -> None:
    server.start_io()
