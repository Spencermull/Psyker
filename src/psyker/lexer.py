"""Handwritten lexer for PSYKER files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .errors import SourceSpan, SyntaxError
from .token import Token

_SYMBOLS = {"{", "}", "[", "]", ":", ",", ";", "="}
_SINGLE_DIALECT_WORDS = {"task", "agent", "worker", "allow", "use", "count", "sandbox", "cwd", "agents", "workers"}
_DOTTED_KEYWORDS = {"fs.open", "fs.create", "exec.ps", "exec.cmd"}


def tokenize(source: str, path: Path | None = None) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    line = 1
    column = 1
    length = len(source)

    def advance() -> str:
        nonlocal i, line, column
        ch = source[i]
        i += 1
        if ch == "\n":
            line += 1
            column = 1
        else:
            column += 1
        return ch

    def peek(offset: int = 0) -> str:
        idx = i + offset
        if idx >= length:
            return ""
        return source[idx]

    while i < length:
        ch = peek()
        if ch in {" ", "\t", "\r", "\n"}:
            advance()
            continue
        if ch == "#":
            start_line, start_col = line, column
            content = advance()
            while i < length and peek() != "\n":
                content += advance()
            tokens.append(Token("COMMENT", content, start_line, start_col))
            continue
        if ch in _SYMBOLS:
            tokens.append(Token(ch, ch, line, column))
            advance()
            continue
        if ch == '"':
            start_line, start_col = line, column
            advance()  # consume opening quote
            value = _lex_string(advance, peek, line, column, path)
            tokens.append(Token("STRING", value, start_line, start_col))
            continue
        if ch == "@":
            start_line, start_col = line, column
            value = advance()
            while peek() and (peek().isalnum() or peek() in {"_", "-"}):
                value += advance()
            if value == "@access":
                tokens.append(Token("AT_ACCESS", value, start_line, start_col))
                continue
            raise SyntaxError(
                f"Unknown directive '{value}'",
                SourceSpan(path, start_line, start_col),
                hint="Use @access.",
            )
        if _is_ident_start(ch):
            start_line, start_col = line, column
            value = advance()
            while _is_ident_part(peek()):
                value += advance()
            if peek() == "." and value in {"fs", "exec"}:
                value += advance()
                if not _is_ident_start(peek()):
                    raise SyntaxError(
                        f"Invalid dotted keyword '{value}'",
                        SourceSpan(path, start_line, start_col),
                        hint="Expected operation name after '.'.",
                    )
                while _is_ident_part(peek()):
                    value += advance()
                token_kind = "KEYWORD" if value in _DOTTED_KEYWORDS else "IDENT"
                tokens.append(Token(token_kind, value, start_line, start_col))
                continue
            if value in _SINGLE_DIALECT_WORDS:
                tokens.append(Token("KEYWORD", value, start_line, start_col))
            else:
                tokens.append(Token("IDENT", value, start_line, start_col))
            continue
        if ch.isdigit():
            start_line, start_col = line, column
            value = advance()
            while peek().isdigit():
                value += advance()
            tokens.append(Token("INT", value, start_line, start_col))
            continue
        if _is_path_start(ch):
            start_line, start_col = line, column
            value = advance()
            while _is_path_part(peek()):
                value += advance()
            tokens.append(Token("PATH", value, start_line, start_col))
            continue
        raise SyntaxError(
            f"Unexpected character '{ch}'",
            SourceSpan(path, line, column),
            hint="Check token spelling and punctuation.",
        )

    tokens.append(Token("EOF", "", line, column))
    return tokens


def _lex_string(
    advance: callable,
    peek: callable,
    start_line: int,
    start_col: int,
    path: Path | None,
) -> str:
    value = '"'
    escaped = False
    while True:
        ch = peek()
        if not ch:
            raise SyntaxError(
                "Unterminated string literal",
                SourceSpan(path, start_line, start_col),
                hint='Close the string with a double quote.',
            )
        if ch == "\n":
            raise SyntaxError(
                "Newline in string literal",
                SourceSpan(path, start_line, start_col),
                hint="Strings cannot contain raw newlines.",
            )
        current = advance()
        value += current
        if escaped:
            escaped = False
            continue
        if current == "\\":
            escaped = True
            continue
        if current == '"':
            break
    return value


def _is_ident_start(ch: str) -> bool:
    return bool(ch) and ch.isalpha()


def _is_ident_part(ch: str) -> bool:
    return bool(ch) and (ch.isalnum() or ch in {"_", "-"})


def _is_path_start(ch: str) -> bool:
    return bool(ch) and (ch.isalpha() or ch.isdigit() or ch in {"_", "-", ".", "/", "\\", ":"})


def _is_path_part(ch: str) -> bool:
    return _is_path_start(ch)


def tokenize_file(path: Path) -> list[Token]:
    return tokenize(path.read_text(encoding="utf-8"), path=path)


def tokenize_many(paths: Iterable[Path]) -> dict[Path, list[Token]]:
    return {path: tokenize_file(path) for path in paths}
