# PSYKER — Autonomous Development Plan (Codex + Cursor)

> **Goal:** Codex and Cursor develop the project using all md contexts with minimal human prompts.  
> **Human:** Still approves merges and dependency changes (AGENTS.md). "Autonomous" = clear handoff and single plan, not zero oversight.

---

## How This Works

1. **Codex (terminal)** — Receives this file + `md contexts/` and executes **Phase 1 steps in order**. After each step (or batch), Codex commits locally and reports what it did. No need to ask for permission between steps; proceed through the checklist.
2. **Cursor (chat)** — When the user posts "Codex did step N" or pastes a diff/log:
   - **Review** implementation against the cited specs (grammar, CLI, runtime, sandbox, errors).
   - **Suggest** fixes, extra test cases in `Grammar Context/valid` or `Grammar Context/invalid`, or clarifications.
   - **Do not** rewrite Codex’s code unless the user asks; focus on review and test/spec alignment.
3. **Task tracker** — `TODO.md` at repo root lists Phase 1 steps. Codex marks steps complete when done; Cursor can add "Review step N" or "Add test for X" as needed.
4. **Single source of truth** — All behavior comes from **PSYKER_GRAMMAR.md** and the other md contexts. Do not hardcode example file patterns; use the grammar and the Grammar Context corpus.

---

## Spec Index (md contexts)

Use these for every step. Do not rely on memory; open the spec when implementing or reviewing.

| Spec | Use for |
|------|--------|
| **PSYKER_GRAMMAR.md** | Lexer tokens, EBNF, dialect grammars, reserved words |
| **PSYKER_CLI_SPEC.md** | Commands, exit codes, load/run behavior |
| **PSYKER_RUNTIME_MODEL.md** | Registries, load pipeline, agent→worker, run flow |
| **PSYKER_SANDBOX.md** | Sandbox root, layout, path rules, shell cwd |
| **PSYKER_PERMISSIONS.md** | @access, capabilities |
| **PSYKER_ERRORS.md** | Error types, diagnostic format, exit codes |
| **PSYKER_FILE_FORMATS.md** | File formats if needed |
| **PSYKER_LANGUAGE_SPEC.md** | Language semantics |
| **AGENTS.md** | Constraints, dependency policy, commit policy |
| **CODEX_PHASES_AND_STRUCTURE.md** | Folder layout, stack, phase overview |

---

## Phase 1 — Step-by-Step (Codex)

Implement in this order. After each step, run the relevant tests (Grammar Context + any unit tests you add) and update `TODO.md`. Small commits per step are preferred.

### Step 1 — Project layout and lexer

**Read:** PSYKER_GRAMMAR.md (§1–2, lexical tokens and EBNF), AGENTS.md (dependency policy, low-abstraction).

**Do:**
- Create Python package layout under `src/` (e.g. `src/psyker/` or `src/` with `psyker` package). No new dependencies without human approval; stdlib only for lexer.
- Implement **lexer**: input string → list of tokens. Tokens: IDENT, INT, STRING, BARE_PATH (or PATH), COMMENT, and symbols/braces/keywords needed by the grammars. Preserve line/column for diagnostics.
- Lexer must support: identifiers `[A-Za-z][A-Za-z0-9_-]*`, integers, double-quoted strings with `\"` escape, bare paths (letters, digits, `_`, `-`, `.`, `/`, `\`, `:`), comments `#` to EOL. Whitespace separates tokens.

**Done when:** Lexer tokenizes all files in `Grammar Context/valid` and `Grammar Context/invalid` without crashing; token types and boundaries match the grammar. No parsing yet.

**Commit:** e.g. "Add src layout and lexer (Phase 1 step 1)"

---

### Step 2 — AST and parsers (three dialects)

**Read:** PSYKER_GRAMMAR.md (§3–7): dialect dispatch, task grammar, worker grammar, agent grammar, reserved words.

**Do:**
- Define **AST** types (e.g. TaskDef, WorkerDef, AgentDef, stmt types) in a single module. Design so future agent logic fields can be added without breaking (AGENTS.md).
- Implement **three parsers** (or one parser with dialect switch): one for `.psy`, one for `.psya`, one for `.psyw`. Dialect is chosen **only by file extension**.
- Each parser consumes tokens from the lexer and produces the corresponding AST. Reject reserved words from other dialects with **DialectError** (file:line:column).
- Statement order in files is arbitrary; do not hardcode ordering.

**Done when:** Every file in `Grammar Context/valid` parses to the correct dialect AST. Every file in `Grammar Context/invalid` fails with SyntaxError or DialectError as appropriate. No validator or execution yet.

**Commit:** e.g. "Add AST and per-dialect parsers (Phase 1 step 2)"

---

### Step 3 — Validator and load pipeline

**Read:** PSYKER_RUNTIME_MODEL.md (§1–2), PSYKER_PERMISSIONS.md, PSYKER_ERRORS.md.

**Do:**
- Implement **validator**: dialect rules (already enforced by parser), cross-refs (e.g. agent’s `use worker X` → worker X must exist in worker registry). Emit **ReferenceError** / **PermissionError** / **AccessError** as per spec.
- Implement **load pipeline**: given path → infer dialect from extension → parse → validate → insert into in-memory **Worker / Agent / Task** registries. On any failure, do not modify registries; return diagnostic (PSYKER_ERRORS.md format).
- Registries: `{ name -> Def }` for workers, agents, tasks (PSYKER_RUNTIME_MODEL.md).

**Done when:** `load` of each `Grammar Context/valid` file populates registries; load of each `Grammar Context/invalid` file fails with the expected error type and does not change registries. No sandbox or execution yet.

**Commit:** e.g. "Add validator and load pipeline (Phase 1 step 3)"

---

### Step 4 — Sandbox

**Read:** PSYKER_SANDBOX.md (full doc).

**Do:**
- **Sandbox root:** e.g. `%USERPROFILE%\psyker_sandbox` (or configurable); create if missing. Layout: `workspace/`, `logs/`, `tmp/`.
- **Path validation:** all file paths must resolve inside sandbox root; reject path traversal and absolute paths outside sandbox (**SandboxError**). Symlinks escaping sandbox rejected.
- **Session sandbox:** CLI utilities use a session-level sandbox workspace (same root); workers may declare sandbox/cwd but both must resolve inside sandbox root.
- Logging: sandbox activity to `psyker_sandbox/logs/psyker.log` (timestamp, agent, worker, operation, status). Optional: `psyker sandbox reset` to clear workspace/tmp.

**Done when:** Path validator accepts in-sandbox paths and rejects out-of-sandbox paths; sandbox dirs are created on first use; no execution of task statements yet.

**Commit:** e.g. "Add sandbox layout and path validation (Phase 1 step 4)"

---

### Step 5 — Executor

**Read:** PSYKER_RUNTIME_MODEL.md (§3–5), PSYKER_SANDBOX.md (shell constraints), PSYKER_PERMISSIONS.md, PSYKER_ERRORS.md.

**Do:**
- **Run flow:** `run <agent> <task>` → resolve agent and task from registries → select worker instance (v0.1: round-robin) → enforce task `@access` and worker capabilities → for each task statement: check capability, validate path (sandbox), then execute.
- **Statements:** `fs.open` / `fs.create`: validate path in sandbox, then create/open file in sandbox. `exec.ps`: `powershell -NoProfile -Command "<cmd>"` with cwd = sandbox workspace (or worker cwd inside sandbox). `exec.cmd`: `cmd /c "<cmd>"` with same cwd.
- Emit **PermissionError**, **SandboxError**, **ExecError** as per PSYKER_ERRORS.md. Aggregate stdout/stderr and return status.

**Done when:** After loading valid worker + agent + task, `run <agent> <task>` executes statements in order, respects sandbox and capabilities, and returns correct exit code. Invalid access or paths fail with the right errors.

**Commit:** e.g. "Add executor and run flow (Phase 1 step 5)"

---

### Step 6 — CLI (Psyker Bash)

**Read:** PSYKER_CLI_SPEC.md (full), PSYKER_ERRORS.md (exit codes).

**Do:**
- **REPL/shell** with commands: `ls workers | agents | tasks` (table-like listing); `stx worker | agent | task <name>` with optional `--output json|table`; `load <path>`; `run <agent> <task>`; dev utilities: `open`, `mkfile`, `mkdir`, `ps "..."`, `cmd "..."` with sandbox path checks and cwd in sandbox workspace.
- **Exit codes:** 0 success, 1 general, 2 syntax/dialect, 3 permission/access, 4 sandbox, 5 execution (PSYKER_CLI_SPEC.md §2).
- **Command registry:** verb → handler → help (optional). REPL parsing is separate from file grammars; bash-like only in CLI.
- Entrypoint: e.g. `python -m psyker` or `psyker` if installed.

**Done when:** All CLI commands work; `load` + `run` plus dev utilities operate in sandbox; exit codes match spec; Grammar Context valid/invalid files behave as required (valid load/run, invalid load fails with expected code).

**Commit:** e.g. "Add CLI shell and command registry (Phase 1 step 6)"

---

## Phase 1 — Cursor review triggers

When the user posts in Cursor:

- **"Codex finished step N"** or **"Review step N"** — Review the diff/code for step N against the spec listed above. Confirm: grammar compliance, no hardcoded example order, error types and exit codes, sandbox and permission rules. Suggest any missing test cases in `Grammar Context/valid` or `Grammar Context/invalid`.
- **"Codex reported [error message]"** — Help interpret the error against PSYKER_GRAMMAR.md and PSYKER_ERRORS.md; suggest a minimal fix or a test case that would catch it.
- **"Add a test for X"** — Propose a new file in `Grammar Context/valid` or `Grammar Context/invalid` that exercises X, and the expected outcome (parse success or error type).

Do not take over implementation from Codex unless the user explicitly asks (e.g. "you implement step N").

---

## Phase 2 (later)

After Phase 1 is complete and reviewed:

- **Phase 2a** — VS Code extension: language IDs for `.psy` / `.psya` / `.psyw`, TextMate grammars, basic highlighting (see PSYKER_VSCODE_EXTENSION_PLAN.md).
- **Phase 2b** — LSP reusing the same lexer/parser; diagnostics (SyntaxError, DialectError, reference errors).

Phase 2 is not part of the autonomous plan until Phase 1 is done and human-approved.

---

## One-line prompt for Codex

You can give Codex this prompt (and the repo or `md contexts/` path):

```text
Execute Phase 1 of the PSYKER project using md contexts/AUTONOMOUS_DEV_PLAN.md and all other md contexts as the source of truth. Implement steps 1–6 in order. After each step, run tests (Grammar Context), update TODO.md, and commit. Report when each step is done. No new dependencies without human approval; follow PSYKER_GRAMMAR.md and AGENTS.md.
```

---

*This file is the single autonomous execution plan for Codex and the review playbook for Cursor.*
