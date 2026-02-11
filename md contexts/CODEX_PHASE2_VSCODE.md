# Codex — Phase 2: VS Code Extension + LSP

Implement **Phase 2** of the Psyker project: VS Code editor support. The Python runtime and CLI (Phase 1) are complete. Use **PSYKER_VSCODE_EXTENSION_PLAN.md** and **PSYKER_GRAMMAR.md** as the source of truth.

---

## Overview

- **Phase 2a — Syntax highlighting:** A VS Code extension that registers languages for `.psy`, `.psya`, `.psyw` and provides TextMate grammars for comment/string/keyword highlighting.
- **Phase 2b — Language Server (LSP):** A language server that reuses the **existing Python lexer/parser** (in `src/psyker/`). On document change, parse by dialect (from file extension), then publish diagnostics (SyntaxError, DialectError, optional ReferenceError). No cross-reference or permission validation required for v0.1 beyond what the parser/validator already do.

---

## Phase 2a — Syntax Highlighting

### Deliverables

1. **Extension scaffold** in a new directory (e.g. `vscode-extension/` or `editor/psyker-vscode/`):
   - `package.json`: extension manifest, `activationEvents` (e.g. `onLanguage:psy`), engine `^1.70.0` or similar.
   - Register three languages:
     - `psy` (tasks) — file extensions: `["psy"]`
     - `psya` (agents) — file extensions: `["psya"]`
     - `psyw` (workers) — file extensions: `["psyw"]`

2. **TextMate grammars** (one per dialect or one combined with scope selectors):
   - Comments: `#` to end of line → `comment.line.number-sign.psy` (or equivalent).
   - Strings: double-quoted with `\"` escape.
   - Keywords and reserved words per **PSYKER_GRAMMAR.md §7**:
     - Task: `task`, `@access`, `agents`, `workers`, `fs.open`, `fs.create`, `exec.ps`, `exec.cmd`
     - Worker: `worker`, `allow`, `sandbox`, `cwd`, plus the four capabilities
     - Agent: `agent`, `use`, `worker`, `count`
   - Identifiers, numbers, symbols `{ } [ ] : , ; =` as needed for a readable theme.
   - Store grammars as `tmLanguage.json` (or embed in package.json). Reference from `package.json` with `grammar` contribution point.

3. **No validation in 2a** — highlighting only. Phase 2b adds diagnostics.

### Notes

- Do not hardcode behavior from example files; use the reserved word list from the grammar.
- One grammar file per dialect is fine, or a single grammar with different scopes per dialect if the format allows.

---

## Phase 2b — Language Server (LSP)

### Deliverables

1. **LSP server** that reuses the existing **Python** lexer and parser (`psyker.parser`, `psyker.lexer`, `psyker.errors`):
   - **Recommended:** Implement the server in **Python** using **pygls** (or similar), so it can `import psyker` and call `parse_path()` / or tokenize and parse from document text with the correct dialect from the file URI.
   - On **didOpen** / **didChange**: get document URI and path; infer dialect from extension (`.psy` / `.psya` / `.psyw`); run the parser (e.g. parse from document text; path is for diagnostics). Publish **diagnostics** for:
     - **SyntaxError** (parse failure) — range and message.
     - **DialectError** (wrong-dialect keyword) — range and message.
     - **ReferenceError** (e.g. agent references unknown worker) — optional but recommended: requires a minimal “workspace” view (e.g. other open docs or loaded files) to resolve worker names; if out of scope for v0.1, skip and add in a follow-up.
   - Map `psyker.errors` types to LSP `Diagnostic` (range, message, severity: Error). Use `to_diagnostic()` or equivalent for the message text.
   - Server can live in the same repo (e.g. `src/psyker_lsp/` or `vscode-extension/server/`) and be launched by the VS Code extension.

2. **VS Code extension** (TypeScript/JavaScript):
   - Add a **Language Server client** that starts the Python LSP server (e.g. `python -m psyker_lsp` or a script that runs the pygls server). Use `vscode-languageclient` to connect the extension to the server.
   - Ensure the extension activates for `psy`, `psya`, `psyw` and connects the client to the server for those documents.
   - No need to implement completions in v0.1 unless trivial (e.g. keyword completion).

3. **Dependency:** Phase 2b requires a **Python LSP library** (e.g. **pygls**). Per AGENTS.md, new dependencies need human approval. Propose **pygls** (or alternative) in the implementation; document it in the extension README or a short “LSP” section so the human can approve.

### Diagnostics to support (v0.1)

- Dialect misuse (keywords not allowed in the current file type).
- Syntax errors (missing `;`, braces, invalid tokens).
- Reference errors (agent uses unknown worker) — recommended; implement if workspace/context is available without large scope creep.

### Out of scope for v0.1

- Completions (optional for v0.2+).
- Feature flags in the LSP (TBD per plan).
- Full workspace indexing beyond what’s needed for reference checks.

---

## File layout (suggestion)

```
Psyker/
├── src/
│   ├── psyker/           # existing runtime (unchanged)
│   └── psyker_lsp/      # optional: Python LSP server (pygls)
├── vscode-extension/    # or editor/psyker-vscode/
│   ├── package.json
│   ├── syntax/
│   │   ├── psy.tmLanguage.json
│   │   ├── psya.tmLanguage.json
│   │   └── psyw.tmLanguage.json
│   ├── client/          # TS LSP client (if server is separate process)
│   └── README.md
└── ...
```

If the LSP server is inside the extension (e.g. as a Python script started by the extension), it could be `vscode-extension/server/` with a `requirements.txt` for pygls.

---

## Spec references

| Need | Document |
|------|----------|
| Reserved words, tokens | PSYKER_GRAMMAR.md §1, §7 |
| Error types | PSYKER_ERRORS.md |
| Extension goals | PSYKER_VSCODE_EXTENSION_PLAN.md |
| Grammar (EBNF) | PSYKER_GRAMMAR.md |

---

## Done when

- **2a:** Opening a `.psy` / `.psya` / `.psyw` file in VS Code shows syntax highlighting (comments, strings, keywords). Extension installs and activates.
- **2b:** On open/change, diagnostics appear for syntax and dialect errors (and optionally reference errors). LSP server uses the existing psyker parser; no duplicate parser logic.

---

## Human approval

- New dependency **pygls** (or equivalent) for the LSP server must be approved per AGENTS.md. Document it clearly so the human can approve before or after implementation.
