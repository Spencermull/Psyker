# PSYKER v0.1 — AI Agent Brief (Cursor/Codex)

> **Examples Notice**
>
> All code snippets in this documentation are **illustrative examples** of valid syntax.
> Implementations MUST follow **PSYKER_GRAMMAR.md** and MUST NOT hardcode behavior based on example patterns,
> fixed statement ordering, or specific example file layouts.


Use this document as shared context for development agents.

---

## Project Identity

PSYKER is an **interpreted DSL** + terminal runtime (Psyker OS) that runs alongside Windows.
It supports defining workers, agents, and tasks with minimal permissions and a sandbox testing environment.

---

## Non-Goals (v0.1)

- no real OS kernel work
- no assembly
- no hardware interaction
- no scheduling/cron
- no DAG workflow engine
- no networking
- no background daemons

---

## File Dialects (Hard Separation)

- `.psy`  → task code (statements: fs.open, fs.create, exec.ps, exec.cmd)
- `.psya` → agent definition (statements: use worker <name> count = <int>;)
- `.psyw` → worker definition (statements: sandbox, cwd, allow capabilities)

Dialect enforcement is required at parse time.

---

## Sandbox

All filesystem ops and shell execution are restricted to the sandbox root.
Shell execution runs with `cwd` inside sandbox workspace.
Paths escaping sandbox MUST be rejected.

---

## v0.1 Capabilities

Worker capabilities:
- fs.open
- fs.create
- exec.ps
- exec.cmd

Task statements require corresponding capability.

---

## CLI Shell (Psyker Bash)

Required REPL commands:
- ls workers|agents|tasks
- stx worker|agent|task <name> [--output json|table]
- load <file>
- run <agent> <task>
- (optional utilities) open/mkfile/mkdir/ps/cmd

---

## Must-Have Quality

- Clear diagnostics: file:line:column, error type, hint
- Deterministic parsing
- Safe-by-default execution (no sandbox escape)

---

## Specs to Follow

- PSYKER_GRAMMAR.md
- PSYKER_LANGUAGE_SPEC.md
- PSYKER_PERMISSIONS.md
- PSYKER_SANDBOX.md
- PSYKER_CLI_SPEC.md
- PSYKER_ERRORS.md

## v0.1 Decisions (Locked)

- **Session-only runtime** (no persistence in v0.1)
- **Strict DSL in `.psy`**; bash-like UX belongs to the **interactive CLI**, not file syntax
- **Identity-based access control** via `@access { agents: [...], workers: [...] }`
- **Sandbox-only** execution in v0.1 (future “trusted” modes allowed later, not now)
- CLI “utilities” are **dev/test-first** (test-before-prod); production intent lives in tasks
- **Agents are minimal in v0.1** but are **future logic-bearing** (extension points only in v0.1)
- **Human auditing only** for AI-generated code; no autonomous behavior
- **Rigid audits for large commits**, lighter PR checks for small tasks

## Examples Are Illustrative

Snippets are illustrative; the grammar is authoritative. Do not hardcode example patterns or ordering.

## Human Approval

AI may propose patches/commits, but all merges require human approval. No autonomous dependency installation.
