# Audit: fs.open After fs.create — File Not Found / Not Visible

## Status (February 12, 2026)

- Resolved in Phase 4 Step 1 (`Align task fs.* path resolution with PSYKER_SANDBOX`).
- Runtime `fs.open` and `fs.create` now resolve relative task paths through workspace (`resolve_in_workspace`).
- Test tasks now use workspace-relative task paths such as `input.txt`.
- This audit is now archival context.

## Problem

User ran `task full` which contains:
1. `fs.create "sandbox/workspace/input.txt"` — creates file
2. `fs.open "sandbox/workspace/input.txt"` — reads file

Result: file did not open after creation (either ExecError or empty/invisible output).

---

## Root Cause: Path Resolution Mismatch

### Two Different Resolution Functions

| Context | Function | Base | Example: `"sandbox/workspace/input.txt"` |
|---------|----------|------|----------------------------------------|
| **Task fs.create / fs.open** | `resolve_under_root()` | sandbox root | `root/sandbox/workspace/input.txt` |
| **CLI `open` command** | `resolve_in_workspace()` | sandbox root + `workspace/` | `root/workspace/sandbox/workspace/input.txt` |

So:
- Task creates at: `%USERPROFILE%\psyker_sandbox\sandbox\workspace\input.txt`
- CLI `open sandbox/workspace/input.txt` looks at: `%USERPROFILE%\psyker_sandbox\workspace\sandbox\workspace\input.txt`

These are different paths. If the user ran `open sandbox/workspace/input.txt` after `run alpha full`, the CLI would fail with "File not found".

### Spec vs Implementation

`PSYKER_SANDBOX.md` states: "All relative paths in Psyker tasks resolve inside workspace/."

The runtime uses `resolve_under_root` for task fs operations, so paths are relative to the sandbox root, not workspace. Paths like `"sandbox/workspace/input.txt"` end up under `root/sandbox/...`, not `root/workspace/...`.

---

## Fix Options

### Option A: Align Task Paths With CLI (Recommended for test_tasks)

Use paths that resolve to `root/workspace/` so both task and CLI `open` see the same file:

- In `task_full.psy`, change `"sandbox/workspace/input.txt"` → `"workspace/input.txt"`
- Both task fs.* and CLI `open input.txt` will then use `root/workspace/input.txt`

Update `test_tasks/task_full.psy`:

```psy
@access { agents: [alpha], workers: [w1] }
task full {
  fs.create "workspace/input.txt";
  fs.open "workspace/input.txt";
  exec.ps "Write-Host 'hello from ps'";
  exec.cmd "echo hello from cmd";
}
```

CLI after run: `open input.txt` (or `open workspace/input.txt` if using resolve_in_workspace — the latter would need `workspace/input.txt` under workspace = workspace/workspace/input.txt, so actually just `open input.txt`).

Note: `resolve_in_workspace("input.txt")` → `root/workspace/input.txt`. Correct.

### Option B: Code Change — Task fs.* Use Workspace-Relative Paths

Per spec, task fs operations could resolve relative to workspace:

- In `runtime._run_statement` for fs.open/fs.create, use `resolve_in_workspace(value)` instead of `resolve_under_root(value)` when the path is relative.

This would make task paths consistent with the spec and with CLI `open`. Requires validator/spec approval per AGENTS.md.

### Option C: worker.sandbox Unused

`worker.sandbox` is parsed but never used. Runtime always uses the global sandbox root. If worker.sandbox were intended to scope fs operations, that would need implementation. Out of scope for this audit.

---

## Verification

After applying Option A:

1. `load "test_tasks/worker_all_caps.psyw"`
2. `load "test_tasks/agent_alpha.psya"`
3. `load "test_tasks/task_full.psy"`
4. `run alpha full` — should create and read `workspace/input.txt`
5. `open input.txt` — should display the file (empty or content)

---

## Files to Modify

- **test_tasks/task_full.psy**: Change `sandbox/workspace/input.txt` → `workspace/input.txt`
- **test_tasks/task_read.psy** (if it exists): Same change
- **CODEX_PSYKER_TEST_FILES_BRIEF.md**: Update example paths to `workspace/input.txt` and document that task paths should use `workspace/` prefix for CLI `open` compatibility

---

## Summary

The bug is a path base mismatch: task fs.* uses root, CLI open uses workspace. Align test files to use `workspace/input.txt` so both resolve to the same file.
