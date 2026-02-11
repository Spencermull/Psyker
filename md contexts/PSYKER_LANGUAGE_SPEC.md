# PSYKER v0.1 — Language Specification

> **Examples Notice**
>
> All code snippets in this documentation are **illustrative examples** of valid syntax.
> Implementations MUST follow **PSYKER_GRAMMAR.md** and MUST NOT hardcode behavior based on example patterns,
> fixed statement ordering, or specific example file layouts.


PSYKER v0.1 is an **interpreted DSL** for a terminal-based automation environment (“Psyker OS”) that runs alongside Windows.
PSYKER defines three file dialects with strict separation:

- `.psy`  → task code (what to do)
- `.psya` → agent definitions (who coordinates)
- `.psyw` → worker definitions (what can execute)

The interpreter MUST enforce dialect boundaries at parse time and MUST enforce capabilities + sandbox boundaries at runtime.

---

## 1) Dialects and Responsibilities

### 1.1 `.psy` — Tasks
- Defines reusable task blocks.
- Contains only execution statements: `fs.open`, `fs.create`, `exec.ps`, `exec.cmd`.
- May include an `@access` header to restrict which agents/workers may dispatch/execute.

### 1.2 `.psya` — Agents
- Defines an agent and its workforce composition.
- Cannot execute shell commands or file operations.
- References worker types by name.

### 1.3 `.psyw` — Workers
- Defines worker capabilities (“minimal permissions”).
- Declares sandbox and working directory.
- Cannot define tasks or agents.

---

## 2) Execution Model (v0.1)

**Load → Validate → Run**

1. Load `.psyw` files (workers) into the Worker Registry.
2. Load `.psya` files (agents) into the Agent Registry.
3. Load `.psy` files (tasks) into the Task Registry.
4. Validate references:
   - agent uses existing worker name
5. Run tasks via the shell:
   - `run <agent> <task>`
   - agent selects a worker instance (v0.1: round-robin)
   - interpreter enforces:
     - task `@access` (if present)
     - worker capabilities (`allow ...`)
     - sandbox path restrictions
   - execute statements in order; aggregate output + exit status

v0.1 does **not** include scheduling, triggers, DAG workflows, or background services.

---

## 3) Capabilities (Minimal Permissions)

Workers may be granted only these capabilities in v0.1:

- `fs.open`   → read a file (sandbox restricted)
- `fs.create` → create file or directory (sandbox restricted)
- `exec.ps`   → execute a PowerShell command (run with cwd set to sandbox workspace)
- `exec.cmd`  → execute a CMD command (run with cwd set to sandbox workspace)

If a task uses an operation not allowed by the worker, the interpreter MUST raise **PermissionError**.

---

## 4) Sandbox Requirements

When running in sandbox mode:
- All file paths MUST resolve inside the sandbox root.
- `cwd` for shell execution MUST be inside sandbox (default: `sandbox/workspace/`).
- Path traversal attempts (e.g., `..`) MUST be rejected.

See `PSYKER_SANDBOX.md` for details.

---

## 5) Task Access Control (`@access`)

Tasks may optionally define access restrictions.

Example:

```psyker
@access { agents: [crawler], workers: [basic_drone] }
task hello {
    exec.ps "Write-Output 'hi'";
}
```

Rules:
- If `agents` is present, only listed agents may dispatch the task.
- If `workers` is present, only listed worker types may execute the task.
- If omitted, the task is visible/executable by any agent/worker (subject to capability checks).

Violations MUST raise **AccessError** (a subtype of PermissionError is fine in v0.1).

---

## 6) Determinism & Diagnostics

- Parsing MUST be deterministic per dialect.
- Errors MUST include file, line, column, and a short fix hint where possible.
- Tasks MUST enforce statement terminators `;` in v0.1 to simplify diagnostics and tooling.

---

## 7) Non-Goals (v0.1)

Not included:
- loops, conditionals, variables
- workflow graphs / DAG engine
- network operations
- background job scheduling
- distributed execution
- OS-level isolation (containers/VM)

---

## 8) Compatibility Notes (Windows)

- `exec.ps` SHOULD invoke: `powershell -NoProfile -Command "<cmd>"`
- `exec.cmd` SHOULD invoke: `cmd /c "<cmd>"`
- Both SHOULD run with `cwd` set to the worker’s configured `cwd` (inside sandbox).

## v0.1 Decisions (Locked)

- **Session-only runtime** (no persistence in v0.1)
- **Strict DSL in `.psy`**; bash-like UX belongs to the **interactive CLI**, not file syntax
- **Identity-based access control** via `@access { agents: [...], workers: [...] }`
- **Sandbox-only** execution in v0.1 (future “trusted” modes allowed later, not now)
- CLI “utilities” are **dev/test-first** (test-before-prod); production intent lives in tasks
- **Agents are minimal in v0.1** but are **future logic-bearing** (extension points only in v0.1)
- **Human auditing only** for AI-generated code; no autonomous behavior
- **Rigid audits for large commits**, lighter PR checks for small tasks

## Modular Extensibility (Design Requirement)

PSYKER must be built so future language/runtime versions can expand cleanly without rewrites:

- **Versioned grammar**: changes within `v0.x` are **additive only** (no breaking removals/renames).
- **Feature flags**: new syntax/ops are enabled explicitly (config/CLI flag) until promoted.
- **Registries**:
  - Capability registry maps statement → required permission → handler → diagnostics.
  - CLI command registry maps verb → handler → help/usage → output schema.
  - Runtime pipeline stages (middleware) allow adding validation/execution phases without altering core flow.
- **Stable dialect boundaries**: `.psy`, `.psya`, `.psyw` remain separate extension domains.
- **Parser as source of truth**: VS Code tooling must reuse the same parser/diagnostics logic as CLI.

## Audience

PSYKER is a **developer tool for programmers** to automate their desktop safely and predictably.

## Access Header Requirement (v0.1)
- **Agents (.psya) and Workers (.psyw)** MUST include an explicit access header where applicable to declare scope/visibility for loading.
- **Tasks (.psy)** MAY include `@access { agents: [...], workers: [...] }`. If omitted, default behavior is **deny-all** (no agent/worker may run the task).
- Parsers MUST error if required access headers are missing in non-task dialects.

## Feature Flags (TBD)
- The concrete mechanism for enabling/disabling feature flags is **TBD**.
- Specs require that new syntax be version-gated; the transport (CLI/config/header) will be decided in a future revision.
- Implementations MUST centralize feature-flag checks behind a single interface to avoid lock-in.
