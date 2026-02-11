# Psyker Sandbox Environment (v0.1)

> **Examples Notice**
>
> All code snippets in this documentation are **illustrative examples** of valid syntax.
> Implementations MUST follow **PSYKER_GRAMMAR.md** and MUST NOT hardcode behavior based on example patterns,
> fixed statement ordering, or specific example file layouts.


## Purpose

The Psyker Sandbox is a **separate testing environment** designed to safely run and validate Psyker agents and workers.

**Psyker OS** is the terminal-based automation runtime.  
**The Sandbox** is an isolated workspace used exclusively for testing Psyker behavior without affecting the host system.

This separation ensures that Psyker can be developed and tested safely without interacting with real user files or system resources.

---

## Relationship to Psyker OS

- Psyker OS: CLI-based automation runtime (agents, workers, tasks)
- Sandbox: Isolated filesystem + execution environment used by Psyker OS for testing

Psyker OS does not own the sandbox.  
It only *targets* the sandbox as an execution environment when running in test mode.

---

## Sandbox Root

All sandbox operations are confined to a single directory on the host system.

Example (Windows):

```
C:\Users\<username>\psyker_sandbox\
```

This directory is created automatically when Psyker is launched in sandbox mode.

---

## Directory Layout

```
psyker_sandbox/
├── workspace/   # working directory for tasks
├── logs/        # sandbox execution logs
└── tmp/         # temporary worker files
```

All relative paths in Psyker tasks resolve inside `workspace/`.

---

## Path Restrictions

The following rules are enforced:

- All file paths must resolve inside `psyker_sandbox/`
- Path traversal outside the sandbox is blocked
- Absolute paths outside the sandbox are rejected
- Symlinks that resolve outside the sandbox are rejected

Allowed:

```
fs.open "./workspace/config.txt"
fs.create "./workspace/output.txt"
```

Blocked:

```
fs.open "../secrets.txt"
fs.open "C:\Windows\System32\config"
```

---

## Shell Execution Constraints

When Psyker executes PowerShell or CMD commands in sandbox mode:

- Working directory is set to `psyker_sandbox/workspace/`
- Commands operate only on sandbox files
- Any resolved path outside the sandbox is blocked

Example:

```
exec.ps "Get-ChildItem ."
exec.cmd "echo Hello > hello.txt"
```

---

## Logging

All sandbox activity is logged to:

```
psyker_sandbox/logs/psyker.log
```

Logs include:
- timestamp
- agent name
- worker name
- operation type
- execution status

---

## Resetting the Sandbox

The sandbox can be wiped and recreated for testing:

```
psyker sandbox reset
```

This clears:
- workspace/
- tmp/

Logs may be preserved unless explicitly cleared.

---

## Security Notice

The sandbox is an application-level isolation layer.  
It is not a hardened security boundary and does not provide OS-level containment.

It exists solely to prevent accidental file or system modification during Psyker development.

---

## Out of Scope (v0.1)

- Network sandboxing
- Container isolation
- Multiple sandbox profiles
- Privileged command execution

These are intentionally excluded from v0.1.

## Sandbox-Only v0.1

All execution is confined to the sandbox in v0.1. Future trusted modes are explicitly out of scope for v0.1.

## Sandbox Scope (v0.1)
- The sandbox is a **general shared testing area** for program experimentation in v0.1.
- Workers may declare a sandbox root, but the runtime must also support a **session-level sandbox workspace** for CLI dev/test utilities.
- Production intent remains in `.psy` tasks; CLI utilities operate within the shared sandbox workspace.
