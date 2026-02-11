# PSYKER — Folder Structure & Phase Execution (Codex + Cursor)

> **For Codex (terminal):** Use this as the single reference for repo layout, stack, and which phase you are executing.  
> **For Cursor:** Design review, grammar/spec clarification, test planning; work alongside Codex on the same phases.

---

## 1) Folder Structure (Current)

```
Psyker/
├── Grammar Context/
│   ├── README.md
│   ├── valid/                    # Must parse successfully
│   │   ├── agent_basic.psya
│   │   ├── agent_two_workers.psya
│   │   ├── task_basic.psy
│   │   ├── task_multiple_stmts.psy
│   │   └── worker_basic.psyw
│   └── invalid/                  # Must produce expected errors
│       ├── agent_missing_access_header.psya
│       ├── task_missing_semicolon.psy
│       ├── task_no_access_header.psy
│       ├── task_path_traversal.psy
│       ├── task_with_worker_def.psy
│       └── worker_invalid_capability.psyw
│
└── md contexts/                  # Specs (source of truth)
    ├── AGENTS.md                 # AI operating rules, Cursor vs Codex roles
    ├── PSYKER_AI_AGENT_BRIEF.md
    ├── PSYKER_CLI_SPEC.md
    ├── PSYKER_ERRORS.md
    ├── PSYKER_FILE_FORMATS.md
    ├── PSYKER_GRAMMAR.md         # EBNF — parser MUST follow this
    ├── PSYKER_LANGUAGE_SPEC.md
    ├── PSYKER_PERMISSIONS.md
    ├── PSYKER_RUNTIME_MODEL.md
    ├── PSYKER_SANDBOX.md
    ├── PSYKER_VSCODE_EXTENSION_PLAN.md
    ├── CODEX_PHASES_AND_STRUCTURE.md  (this file)
    └── ...
```

**No Python package exists yet.** Implementation will live under a new tree (e.g. `src/` or `psyker/`) once Phase 1 starts.

---

## 2) Stack (Locked for v0.1)

| Layer | Technology | Notes |
|-------|------------|--------|
| **Runtime** | Python | Session-only, in-memory registries |
| **CLI** | Python | Interactive shell (“Psyker Bash”), command registry |
| **Parser** | Handwritten | Lexer + per-dialect parser; no parser generator |
| **Execution** | Sandboxed subprocess | Windows: `exec.ps` → PowerShell, `exec.cmd` → cmd; cwd = sandbox workspace |
| **Tooling (later)** | VS Code | Phase 2: syntax highlighting; Phase 2+: LSP reusing CLI lexer/parser |

Dialect is chosen **by file extension only** (`.psy` / `.psya` / `.psyw`). Grammar: **PSYKER_GRAMMAR.md** (EBNF).

---

## 3) Execution Phases (Codex + Cursor)

### Phase 1 — Parser + Runtime + Sandbox + CLI (Python)

**Owner: Codex (terminal)** for code; **Cursor** for design/spec questions and test strategy.

1. **Lexer** — Tokenize per shared lexical rules (IDENT, INT, STRING, PATH, comments, reserved words).
2. **Parsers** — Three dialects, one parser per dialect (or one parser with dialect switch). Output AST; no cross-dialect keywords.
3. **Validator** — Dialect rules, cross-refs (e.g. agent → worker names). Use `Grammar Context/valid` and `Grammar Context/invalid` as test corpus.
4. **Sandbox** — Single sandbox root (e.g. `%USERPROFILE%\psyker_sandbox`), `workspace/`, `logs/`, `tmp/`. Path checks; block traversal outside sandbox.
5. **Executor** — Run task statements: resolve agent → worker, check `@access` and capabilities, run `fs.open`/`fs.create`/`exec.ps`/`exec.cmd` in sandbox.
6. **CLI** — Commands: `ls workers|agents|tasks`, `stx worker|agent|task <name>`, `load <path>`, `run <agent> <task>`, and dev utilities `open`/`mkfile`/`mkdir`/`ps`/`cmd` with sandbox path checks.

**Deliverables:** Python package, CLI entrypoint, all Grammar Context files pass (valid → success, invalid → expected error). Exit codes per PSYKER_CLI_SPEC.md.

---

### Phase 2 — VS Code Tooling (Later)

**Owner:** TBD; can be Codex + Cursor.

- **Phase 2a — Syntax highlighting:** Extension with `.psy` / `.psya` / `.psyw`, TextMate grammars.
- **Phase 2b — LSP:** Language server reusing the same lexer/parser from Phase 1; diagnostics (SyntaxError, DialectError, reference errors).

See **PSYKER_VSCODE_EXTENSION_PLAN.md** for details.

---

## 4) How to Work Alongside Codex

- **Cursor** (this agent): answers spec/grammar questions, suggests test cases, reviews structure; does not generate the main Python patches.
- **Codex**: generates small, isolated patches (lexer, parser, validator, sandbox, executor, CLI, tests). Uses this file + **PSYKER_GRAMMAR.md** + **AGENTS.md**.
- **Single source of truth:** EBNF and reserved words in **PSYKER_GRAMMAR.md**. Do not hardcode behavior from example snippets in other docs.
- **Human:** Approves merges, dependency changes, and scope. Resets drift per AGENTS.md.

When starting a phase, Codex can say: “Starting Phase 1, step 1 (Lexer).” Cursor can respond with any spec clarifications or test expectations. When a step is done, Codex can report and move to the next step; Cursor can suggest valid/invalid cases or review.

---

## 5) Quick Spec References

| Need | Document |
|------|----------|
| EBNF, tokens, dialect rules | PSYKER_GRAMMAR.md |
| CLI commands, exit codes | PSYKER_CLI_SPEC.md |
| Registries, load pipeline, run flow | PSYKER_RUNTIME_MODEL.md |
| Sandbox layout, path rules, shell | PSYKER_SANDBOX.md |
| Access control, capabilities | PSYKER_PERMISSIONS.md |
| Error types, diagnostics | PSYKER_ERRORS.md |
| AI rules, who does what | AGENTS.md |

---

*This file is the handoff for Codex and the coordination point for Cursor when executing phases.*
