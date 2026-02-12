# Codex Brief: Create Psyker Test Files for Manual CLI Testing

Use this brief to generate `.psy`, `.psya`, and `.psyw` files that exercise all Psyker features. Place them in `test_tasks/` for manual testing.

---

## Goal

Create a minimal but complete set of files so a user can run them in the Psyker REPL and verify every feature works.

---

## Required Files

### 1. Worker (`test_tasks/worker_all_caps.psyw`)

- Define worker `w1` with:
  - `sandbox "sandbox"`
  - `cwd "sandbox/workspace"`
  - All four capabilities: `allow fs.open`, `allow fs.create`, `allow exec.ps`, `allow exec.cmd`

### 2. Agent (`test_tasks/agent_alpha.psya`)

- Define agent `alpha` that uses worker `w1` with `count = 1`

### 3. Task (`test_tasks/task_full.psy`)

- Define task `full` with:
  - `@access { agents: [alpha], workers: [w1] }`
  - `fs.create "input.txt"` (create a file first)
  - `fs.open "input.txt"` (read it back)
  - `exec.ps "Write-Host 'hello from ps'"` (PowerShell)
  - `exec.cmd "echo hello from cmd"` (cmd)

### 4. Optional: Separate task for fs.open only (`test_tasks/task_read.psy`)

- `@access { agents: [alpha], workers: [w1] }`
- Task `read` with only `fs.open "input.txt"` (requires file to exist first)

---

## CLI Test Sequence

After generating the files, run these commands in the Psyker REPL:

```
load "test_tasks/worker_all_caps.psyw"
load "test_tasks/agent_alpha.psya"
load "test_tasks/task_full.psy"
ls workers
ls agents
ls tasks
stx worker w1
stx agent alpha
stx task full
mkfile input.txt
run alpha full
open input.txt
sandbox reset
```

---

## Grammar Reference

- **Worker**: `worker <name> { sandbox <path>; cwd <path>; allow <cap> [arg]; }` — caps: fs.open, fs.create, exec.ps, exec.cmd
- **Agent**: `agent <name> { use worker <name> count = <int>; }`
- **Task**: `[ @access { agents: [...], workers: [...] } ] task <name> { <stmt>; ... }` — stmts: fs.open, fs.create, exec.ps, exec.cmd (each takes path or string arg)
- All statements end with `;`

---

## Notes

- Task `fs.*` paths are workspace-relative. Use `input.txt` to resolve to `sandbox/workspace/input.txt`.
- Worker `cwd` applies to `exec.*` statements.
- `fs.open` requires the file to exist; `fs.create` creates it.
- For `exec.ps` and `exec.cmd`, use quoted strings for commands with spaces.
