# Audit: Unused and Redundant Code (Feb 2026)

Per AGENTS.md: low abstraction, no drift, grammar is source of truth.

---

## Changes Applied

| Item | Action |
|------|--------|
| **model.py** | Removed unused `field` import from dataclasses |
| **lexer.py** | Removed unused `tokenize_many` and `Iterable` import |
| **.gitignore** | Added `.psyker_sandbox_test/`, `dist-banner/`, `*.vsix` |
| **test_tasks/create_file.psy** | Fixed syntax error (malformed `exec.ps`) and aligned paths to workspace-relative |

---

## Files Flagged (No Change)

| File | Notes |
|------|------|
| **newlogores.png** | Root-level image; not referenced in config. Icons use `icons/logo_icon.*`. Kept for human decision. |
| **CODEX_* briefs** | Multiple Codex briefs in md contexts; some may be obsolete after Phase 4. Kept as documentation. |

---

## Model Fields (Per AGENTS Future-Proofing)

- **worker.sandbox** — Parsed and stored; displayed in LSP hover. Not used for runtime path resolution. Kept per spec (WorkerDef declares sandbox).
- **worker.cwd** — Used for exec.ps/exec.cmd. Required.

---

## Verification

- All source modules remain in use
- Grammar Context valid/invalid unchanged
- test_tasks: agent_alpha, worker_all_caps, task_full, task_read, create_file — all valid
