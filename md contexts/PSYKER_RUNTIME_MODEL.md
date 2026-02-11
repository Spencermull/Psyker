# PSYKER v0.1 — Runtime Model

> **Examples Notice**
>
> All code snippets in this documentation are **illustrative examples** of valid syntax.
> Implementations MUST follow **PSYKER_GRAMMAR.md** and MUST NOT hardcode behavior based on example patterns,
> fixed statement ordering, or specific example file layouts.


This document describes how PSYKER v0.1 should behave internally at runtime.

---

## 1) Registries

PSYKER maintains three registries in memory:

- Worker Registry: `{ worker_name -> WorkerDef }`
- Agent Registry: `{ agent_name -> AgentDef }`
- Task Registry: `{ task_name -> TaskDef }`

v0.1 may store these only in-memory (no persistence required).

---

## 2) Load Pipeline

`load <file>` performs:

1. Determine dialect from extension (`.psy/.psya/.psyw`).
2. Parse file into an AST.
3. Validate AST by dialect rules.
4. Insert definition into correct registry.
5. Run cross-reference checks (at least for agents → workers).

On failure:
- do not modify registry
- return diagnostic

---

## 3) Agent → Worker Instances

`agent` definitions contain a pool declaration:

```text
use worker <name> count = N;
```

At runtime, PSYKER creates N **worker instances** for that agent.
Instances can share the same WorkerDef (capability envelope).

Worker instance selection algorithm (v0.1):
- round-robin per agent

---

## 4) Running a Task

`run <agent> <task>`:

1. Resolve agent and task from registries
2. Select a worker instance from the agent pool
3. Enforce task access block (`@access`) if present
4. For each statement in task:
   - check capability on worker def
   - if fs statement: validate sandbox path + perform operation
   - if exec statement: run subprocess in sandbox cwd
5. Aggregate stdout/stderr + return status

---

## 5) Sandbox Integration

- Each worker def has `sandbox` and `cwd`.
- In sandbox mode, both MUST resolve inside the sandbox root.
- `fs.open` and `fs.create` operate only on validated paths.
- `exec.ps` uses `powershell -NoProfile -Command "<cmd>"` with cwd.
- `exec.cmd` uses `cmd /c "<cmd>"` with cwd.

---

## 6) Determinism

v0.1 SHOULD be deterministic for:
- parsing
- load ordering
- worker selection (round-robin)

Any randomness must be explicit and optional.

## Session Model (v0.1)

Runtime state is in-memory only in v0.1. Registries are rebuilt each session; no persistence.

## Modular Pipeline

Implement execution as a pipeline of stages (parse → validate → access → capability → sandbox → exec) so stages can be extended later.
Stages should be pluggable/middleware-style.

## Session Sandbox Workspace
Runtime provides a session-level sandbox workspace for CLI dev/test operations, in addition to worker-declared sandbox roots.
