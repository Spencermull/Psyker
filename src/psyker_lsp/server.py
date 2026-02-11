"""Pygls-based language server for Psyker diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from urllib.parse import unquote, urlparse

from lsprotocol.types import (
    Diagnostic,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    Position,
    Range,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
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
    ast: object | None = None


class PsykerLanguageServer(LanguageServer):
    def __init__(self) -> None:
        super().__init__(SERVER_NAME, SERVER_VERSION)
        self.open_documents: Dict[str, OpenDocument] = {}


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
    ls.publish_diagnostics(uri, [])


def _parse_and_publish(ls: PsykerLanguageServer, uri: str, text: str) -> None:
    path = uri_to_path(uri)
    try:
        document = parse_text(path, text)
        ls.open_documents[uri] = OpenDocument(path=path, ast=document)
        _validate_optional_references(ls, uri, document)
        ls.publish_diagnostics(uri, [])
    except (SyntaxError, DialectError, ReferenceError) as exc:
        ls.open_documents[uri] = OpenDocument(path=path, ast=None)
        ls.publish_diagnostics(uri, [to_lsp_diagnostic(exc, path)])
    except PsykerError as exc:
        ls.open_documents[uri] = OpenDocument(path=path, ast=None)
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
    line = max(span.line - 1, 0)
    col = max(span.column - 1, 0)
    message = exc.to_diagnostic()
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


def run() -> None:
    server.start_io()

