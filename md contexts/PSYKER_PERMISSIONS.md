# PSYKER v0.1 — Permissions & Capabilities

> **Examples Notice**
>
> All code snippets in this documentation are **illustrative examples** of valid syntax.
> Implementations MUST follow **PSYKER_GRAMMAR.md** and MUST NOT hardcode behavior based on example patterns,
> fixed statement ordering, or specific example file layouts.


PSYKER v0.1 uses a **capability-based permissions model** enforced at runtime.

- Capabilities are granted in `.psyw` worker definitions using `allow ...;`
- Task statements require specific capabilities to execute.
- Even with capabilities, all filesystem operations are constrained by the sandbox rules.

---

## 1) Capability List (v0.1)

| Capability   | Meaning |
|--------------|---------|
| `fs.open`    | Read a file (sandbox restricted) |
| `fs.create`  | Create a file or directory (sandbox restricted) |
| `exec.ps`    | Execute a PowerShell command |
| `exec.cmd`   | Execute a CMD command |

---

## 2) Mapping: Task Statements → Required Capability

| Task statement | Required capability |
|----------------|---------------------|
| `fs.open ...;`   | `fs.open` |
| `fs.create ...;` | `fs.create` |
| `exec.ps "...";` | `exec.ps` |
| `exec.cmd "...";`| `exec.cmd` |

If a worker does not have the required capability, execution MUST fail with **PermissionError**.

---

## 3) Worker Capability Declaration

Example worker:

```psyker
worker basic_drone {
    sandbox "./psyker_sandbox";
    cwd "./psyker_sandbox/workspace";

    allow fs.open;
    allow fs.create;
    allow exec.ps;
}
```

Notes:
- v0.1 does not require capability arguments, but the grammar allows future extension.
- `sandbox` and `cwd` MUST be inside the sandbox root when sandbox mode is enabled.

---

## 4) Access Control (Task-Level)

A task may restrict which agents/workers can dispatch/execute it:

```psyker
@access { agents: [crawler], workers: [basic_drone] }
task hello {
    exec.ps "Write-Output 'hi'";
}
```

Enforcement order (recommended):
1. Check task access block (`@access`) for the agent/worker
2. Check worker capability for each statement
3. Check sandbox path constraints for each filesystem statement
4. Execute

---

## 5) Default Policy (Safe-by-Default)

Recommended defaults for v0.1:
- Workers start with **no capabilities** unless explicitly allowed.
- Tasks without `@access` are “public” inside the Psyker runtime, but still constrained by worker capabilities and sandboxing.

## Identity-Based Access Control

Tasks may restrict execution using `@access` by **agent name** and **worker name** (identities), not roles.

## Capability Registry (Extensible)

Represent each capability as a registry entry (name, required permission, handler, diagnostics mapping). Additive-only in v0.x.
