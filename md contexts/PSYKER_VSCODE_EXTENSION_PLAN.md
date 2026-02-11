# PSYKER v0.1 — VS Code Extension Plan

> **Examples Notice**
>
> All code snippets in this documentation are **illustrative examples** of valid syntax.
> Implementations MUST follow **PSYKER_GRAMMAR.md** and MUST NOT hardcode behavior based on example patterns,
> fixed statement ordering, or specific example file layouts.


Goal: make PSYKER usable in VS Code with syntax highlighting and reliable error diagnostics.

You can build this in two phases.

---

## Phase 1 — Syntax Highlighting (Fast)

Deliverables:
- a VS Code extension that registers languages for:
  - `.psy`  (tasks)
  - `.psya` (agents)
  - `.psyw` (workers)
- TextMate grammars (`tmLanguage.json`) per dialect
- Basic comment/string/keyword highlighting

Notes:
- Phase 1 does not validate cross-references or permissions.
- Phase 1 is enough to feel “real” in the editor.

---

## Phase 2 — Language Server (Real Diagnostics)

Build a PSYKER Language Server (LSP):
- Reuse the real lexer/parser used by the PSYKER CLI
- On document change:
  - parse with correct dialect based on extension
  - emit diagnostics (SyntaxError, DialectError, etc.)
  - optionally provide completions (v0.2+)

Recommended languages:
- TypeScript (common for VS Code tooling)
- Python (also viable; use `pygls` or similar)

---

## Diagnostics to Support (v0.1)

- Dialect misuse (keywords in wrong file type)
- Syntax errors (missing braces, missing ';', etc.)
- Reference errors (agent uses unknown worker) — optional in v0.1 but recommended

---

## Minimal Completion Targets (Optional)

- Keywords per dialect
- Known worker names inside `.psya`
- Known task names for REPL commands (outside LSP scope unless you add workspace indexing)

---

## Why LSP Matters for Cursor/Codex

Cursor/Codex agents will write better code/spec compliance if:
- the editor shows immediate errors
- the grammar is strict and deterministic
- the spec is machine-parseable (EBNF + reserved words)

## Feature Flags

Surface feature-flagged syntax as diagnostics/warnings when disabled.

## Feature Flags (TBD)
- The concrete mechanism for enabling/disabling feature flags is **TBD**.
- Specs require that new syntax be version-gated; the transport (CLI/config/header) will be decided in a future revision.
- Implementations MUST centralize feature-flag checks behind a single interface to avoid lock-in.
