# PSYKER v0.1 — File Formats

> **Examples Notice**
>
> All code snippets in this documentation are **illustrative examples** of valid syntax.
> Implementations MUST follow **PSYKER_GRAMMAR.md** and MUST NOT hardcode behavior based on example patterns,
> fixed statement ordering, or specific example file layouts.


PSYKER uses three file types. The interpreter MUST choose parsing rules based on file extension.

---

## 1) `.psy` — Task Files

Purpose: define task code (execution steps).

Required structure:
- One or more `task <name> { ... }` blocks
- Optional `@access { ... }` header per task

Example:

```psyker
@access { agents: [crawler], workers: [basic_drone] }
task hello {
    exec.ps "Write-Output 'Hello from PSYKER'";
}

task make_dir {
    fs.create "./workspace/output";
}
```

Allowed statements inside tasks:
- `fs.open <path>;`
- `fs.create <path>;`
- `exec.ps "<powershell command>";`
- `exec.cmd "<cmd command>";`

---

## 2) `.psya` — Agent Files

Purpose: define an agent and its worker pool.

Required structure:
- Exactly one `agent <name> { ... }` block in v0.1

Example:

```psyker
agent crawler {
    use worker basic_drone count = 2;
}
```

Allowed statements inside agent blocks:
- `use worker <worker_name> count = <int>;`

---

## 3) `.psyw` — Worker Files

Purpose: define worker permissions and sandbox configuration.

Required structure:
- Exactly one `worker <name> { ... }` block in v0.1

Example:

```psyker
worker basic_drone {
    sandbox "./psyker_sandbox";
    cwd "./psyker_sandbox/workspace";

    allow fs.open;
    allow fs.create;
    allow exec.ps;
}
```

Allowed statements inside worker blocks:
- `sandbox <path>;`
- `cwd <path>;`
- `allow <capability> [arg];`

Capabilities (v0.1):
- `fs.open`
- `fs.create`
- `exec.ps`
- `exec.cmd`

---

## 4) Cross-File Linking

- Agents reference workers by `worker_name`.
- The REPL command `run <agent> <task>` references a loaded agent and a loaded task.
- Tasks may restrict execution using `@access`.

---

## 5) Strict Dialect Separation

`.psya` and `.psyw` MUST NOT contain task statements (`fs.*`, `exec.*`) or `task` blocks.
`.psy` MUST NOT contain `agent` or `worker` blocks.

Violations MUST raise **DialectError** with line/column.

## Access Header Requirement (v0.1)
- **Agents (.psya) and Workers (.psyw)** MUST include an explicit access header where applicable to declare scope/visibility for loading.
- **Tasks (.psy)** MAY include `@access { agents: [...], workers: [...] }`. If omitted, default behavior is **deny-all** (no agent/worker may run the task).
- Parsers MUST error if required access headers are missing in non-task dialects.
