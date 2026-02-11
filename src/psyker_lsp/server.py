"""Pygls-based language server for Psyker diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from urllib.parse import unquote, urlparse

from lsprotocol.types import (
    CompletionItem,
    CompletionItemKind,
    CompletionParams,
    Diagnostic,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    Hover,
    HoverParams,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_HOVER,
)
from pygls.lsp.server import LanguageServer

from psyker.errors import DialectError, PsykerError, ReferenceError, SourceSpan, SyntaxError
from psyker.lexer import tokenize
from psyker.model import AgentDocument, WorkerDocument
from psyker.parser import Parser
from psyker.validator import ValidationContext, validate_document

SERVER_NAME = "psyker-lsp"
SERVER_VERSION = "0.1.0"


@dataclass
class OpenDocument:
    path: Path
    text: str = ""
    ast: object | None = None


class PsykerLanguageServer(LanguageServer):
    def __init__(self) -> None:
        super().__init__(SERVER_NAME, SERVER_VERSION)
        self.open_documents: Dict[str, OpenDocument] = {}


server = PsykerLanguageServer()

_KEYWORDS_BY_SUFFIX = {
    ".psy": ["task", "@access", "agents", "workers", "fs.open", "fs.create", "exec.ps", "exec.cmd"],
    ".psya": ["agent", "use", "worker", "count"],
    ".psyw": ["worker", "allow", "sandbox", "cwd", "fs.open", "fs.create", "exec.ps", "exec.cmd"],
}

_HOVER_TEXT_BY_WORD = {
    "task": "Define a task block containing executable statements.",
    "@access": "Restrict which agents and workers may run a task.",
    "agents": "List of agent names allowed by @access.",
    "workers": "List of worker names allowed by @access.",
    "agent": "Define an agent and its worker usage declarations.",
    "use": "Declare worker usage for an agent.",
    "worker": "Declare a worker reference or a worker definition.",
    "count": "Set how many instances of a worker an agent uses.",
    "allow": "Grant a capability to a worker.",
    "sandbox": "Set the worker sandbox root path.",
    "cwd": "Set the worker command working directory.",
    "fs.open": "Read a file (sandbox-restricted).",
    "fs.create": "Create a file or directory (sandbox-restricted).",
    "exec.ps": "Run a PowerShell command in sandbox cwd.",
    "exec.cmd": "Run a cmd command in sandbox cwd.",
}


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
    ls.publish_diagnostics(uri, [])


@server.feature(TEXT_DOCUMENT_COMPLETION)
def completion(ls: PsykerLanguageServer, params: CompletionParams) -> list[CompletionItem]:
    uri = params.text_document.uri
    suffix = _suffix_for_uri(ls, uri)
    items = [
        CompletionItem(label=keyword, kind=CompletionItemKind.Keyword)
        for keyword in keywords_for_suffix(suffix)
    ]
    if suffix == ".psya":
        items.extend(
            CompletionItem(label=worker_name, kind=CompletionItemKind.Variable)
            for worker_name in worker_names_from_open_docs(ls.open_documents)
        )
    return items


@server.feature(TEXT_DOCUMENT_HOVER)
def hover(ls: PsykerLanguageServer, params: HoverParams) -> Hover | None:
    uri = params.text_document.uri
    open_doc = ls.open_documents.get(uri)
    if open_doc is None:
        return None
    word = _word_at_position(open_doc.text, params.position)
    if word is None:
        return None
    text = hover_text_for_word(word)
    if text is None:
        return None
    return Hover(contents=MarkupContent(kind=MarkupKind.PlainText, value=text))


def _parse_and_publish(ls: PsykerLanguageServer, uri: str, text: str) -> None:
    path = uri_to_path(uri)
    try:
        document = parse_text(path, text)
        ls.open_documents[uri] = OpenDocument(path=path, text=text, ast=document)
        _validate_optional_references(ls, uri, document)
        ls.publish_diagnostics(uri, [])
    except (SyntaxError, DialectError, ReferenceError) as exc:
        ls.open_documents[uri] = OpenDocument(path=path, text=text, ast=None)
        ls.publish_diagnostics(uri, [to_lsp_diagnostic(exc, path)])
    except PsykerError as exc:
        ls.open_documents[uri] = OpenDocument(path=path, text=text, ast=None)
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


def run() -> None:
    server.start_io()

