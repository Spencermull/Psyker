# Phase 4 — Spec Alignment + CI (Codex)

> **Scope:** Align task fs.* path resolution with PSYKER_SANDBOX, add CI job. No new dependencies. Small, isolated patches per AGENTS.md.

---

## Prerequisites

- Phase 1–6 complete (parser, runtime, sandbox, executor, CLI)
- Phase 2 complete (VS Code extension, LSP)
- All 48 tests pass

---

## Constraints (from AGENTS.md)

- No new dependencies without human approval
- Grammar is source of truth (PSYKER_GRAMMAR.md)
- Commit per step; do not push to main
- Small, isolated patches

---

## Step 1 — Align Task fs.* Path Resolution With PSYKER_SANDBOX

**Read:** PSYKER_SANDBOX.md (§ Path Restrictions): "All relative paths in Psyker tasks resolve inside `workspace/`."

**Current behavior:** `runtime._run_statement` for `fs.open` and `fs.create` uses `resolve_under_root(path)` — paths are relative to sandbox root. So `"sandbox/input.txt"` → `root/sandbox/input.txt`.

**Spec behavior:** Task paths should resolve inside workspace. So `"input.txt"` → `root/workspace/input.txt`.

**Do:**
1. In `runtime._run_statement`, for `fs.open` and `fs.create`, change from `resolve_under_root(value)` to `resolve_in_workspace(value)` when the path is relative (non-absolute). Keep path traversal and sandbox checks; `resolve_in_workspace` stays under root.
2. Update `Grammar Context/valid/task_basic.psy`: change `fs.open "sandbox/input.txt"` to `fs.open "input.txt"` (resolves to workspace/input.txt).
3. Update `tests/test_step5_executor.py` `test_run_valid_task`: create input file at `self.sandbox.resolve_in_workspace("input.txt")` (or equivalent), and ensure task uses `"input.txt"`.
4. Update `test_tasks/task_full.psy` and `test_tasks/task_read.psy`: change `workspace/input.txt` to `input.txt` (workspace-relative).
5. Update `Grammar Context/valid/task_multiple_stmts.psy`: change `sandbox/a.txt` to `a.txt` (workspace-relative).
6. Update `Grammar Context/invalid/task_path_traversal.psy`: change `../secret.txt` to `../../secret.txt` so the path escapes sandbox root when resolved from workspace (otherwise `../secret.txt` → root/secret.txt, which stays inside root; `../../secret.txt` escapes).
7. Run full test suite. All tests must pass.

**Done when:** Task fs.* paths resolve under workspace; tests pass; Grammar Context valid/invalid unchanged in semantics (valid still parses/runs, invalid still fails).

**Commit:** `Align task fs.* path resolution with PSYKER_SANDBOX (Phase 4 step 1)`

---

## Step 2 — Add CI Job

**Read:** CI_CHECKLIST.md, V01_READINESS_PLAN.md (C3).

**Do:**
1. Create `.github/workflows/test.yml` with:
   - Trigger: `push` (branches: main, master), `pull_request` (same branches)
   - Job: run on `windows-latest` (Psyker targets Windows)
   - Steps: checkout, setup Python 3.10+, `pip install -e .` and `pip install -r requirements-lsp.txt`, set `PYTHONPATH=src`, run `python -m unittest discover -s tests -v`
   - No new dependencies; use GitHub-hosted runner only
2. Ensure `.github/workflows/` is not in `.gitignore`.

**Done when:** Workflow file exists; locally verifiable via `act` (optional) or by pushing to a branch; human can confirm CI runs on next push.

**Commit:** `Add CI workflow for test suite (Phase 4 step 2)`

---

## Step 3 — Update TODO.md and Briefs

**Do:**
1. Add a "Phase 4 — Spec Alignment + CI" section to `TODO.md` (or update existing Phase C) with:
   - [x] Step 1: Task fs.* path resolution aligned with workspace
   - [x] Step 2: CI job added
2. Update `CODEX_PSYKER_TEST_FILES_BRIEF.md`: change path examples from `workspace/input.txt` to `input.txt`; note that task paths are workspace-relative.
3. Update `CODEX_AUDIT_FS_OPEN_AFTER_CREATE.md`: add note that Step 1 resolves the issue; audit can be archived.

**Commit:** `Update TODO.md and briefs for Phase 4 completion`

---

## Verification

After all steps:

```powershell
cd c:\Users\spenc\Documents\Psyker
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
```

All 48 tests must pass. Manual: load `test_tasks/*`, run `alpha full`, `open input.txt` — file should be found.

---

## One-Line Prompt for Codex

```text
Execute Phase 4 of the PSYKER project per md contexts/CODEX_PHASE4_SPEC_ALIGNMENT_CI.md. Implement steps 1–3 in order. Use PSYKER_SANDBOX.md and CI_CHECKLIST.md as spec. No new dependencies. After each step, run the full test suite, update TODO.md, and commit. Report when each step is done.
```
