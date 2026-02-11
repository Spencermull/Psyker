# PSYKER v0.1 — CLI Shell Spec (Psyker Bash)

> **Examples Notice**
>
> All code snippets in this documentation are **illustrative examples** of valid syntax.
> Implementations MUST follow **PSYKER_GRAMMAR.md** and MUST NOT hardcode behavior based on example patterns,
> fixed statement ordering, or specific example file layouts.


This document specifies the **interactive PSYKER shell** command surface (“Psyker Bash”).

**Design goals (v0.1):**
- minimal commands
- predictable flags
- immediate execution
- works on Windows
- integrates with `.psy/.psya/.psyw` files

---

## 1) Core Commands (v0.1)

### 1.1 Listing

```text
ls workers
ls agents
ls tasks
```

Output: table-like listing (id/name, type, counts).

---

### 1.2 Status / Inspect

```text
stx worker <worker_name>
stx agent <agent_name>
stx task <task_name>
```

Optional output format:
```text
stx agent crawler --output json
stx worker basic_drone --output table
```

`--output` formats (v0.1):
- `table` (default)
- `json`

---

### 1.3 Load Files

```text
load <path_to_file>
```

Rules:
- `.psy` loads tasks
- `.psya` loads an agent
- `.psyw` loads a worker

Errors:
- unknown extension → error
- dialect mismatch → DialectError
- parse error → SyntaxError

---

### 1.4 Run a Task

```text
run <agent_name> <task_name>
```

Behavior:
- resolves agent and task from registries
- selects a worker instance from the agent (v0.1: round-robin)
- enforces `@access`, capabilities, and sandbox constraints
- executes task statements in order
- prints output and exit status

---

### 1.5 Direct Utilities (Sandbox Mode)

These operate directly in sandbox workspace and are intended for testing.

```text
open <path>
mkfile <path>
mkdir <path>
ps "<powershell command>"
cmd "<cmd command>"
```

Rules:
- `open/mkfile/mkdir` MUST enforce sandbox path validation.
- `ps/cmd` run with cwd set to sandbox workspace.

---

## 2) Exit Codes (Recommended)

- `0` success
- `1` general error
- `2` syntax/dialect error
- `3` permission/access error
- `4` sandbox violation
- `5` execution failure (shell exit code propagated where possible)

---

## 3) Help (Optional in v0.1)

```text
help
help run
help load
```

If implemented, help should print command usage + examples.

## Dev/Test Utilities

CLI utilities (`open`, `mkfile`, `mkdir`, `ps`, `cmd`) are **dev/test-first** helpers for sandbox experimentation.
Production automation should be captured as `.psy` tasks.

## Extensibility

CLI commands must be registered through a command registry (verb → handler → help → output schema).
New commands should be namespaced and version-gated.

## Feature Flags (TBD)
CLI support for feature flags is TBD; commands must query a centralized feature-flag interface.
