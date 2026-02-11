# PSYKER v0.1 Readiness Plan

This document defines what “v0.1 ready” means and the plan of action to get there. All criteria are derived from the md context specs.

---

## Current State (Done)

| Area | Status | Notes |
|------|--------|--------|
| **Runtime** | Done | Lexer, parser (3 dialects), validator, registries, load pipeline, executor, sandbox |
| **CLI** | Done | ls, stx, load, run, open/mkfile/mkdir/ps/cmd, help, exit; exit codes 0–5; `python -m psyker` |
| **VS Code** | Done | Syntax highlighting (3 languages), LSP diagnostics (SyntaxError, DialectError, ReferenceError) |
| **Tests** | Done | 21 tests (lexer, parser, load, sandbox, executor, CLI); Grammar Context valid/invalid |
| **Specs** | Done | Grammar, errors, CLI, runtime, sandbox, permissions, file formats, extension plan |

---

## v0.1 Readiness Criteria (from specs)

### Must-have for v0.1

1. **CLI runnable as installed command**  
   - PSYKER_CLI_SPEC + PSYKER_AI_AGENT_BRIEF: “works on Windows”, “integrates with .psy/.psya/.psyw”.  
   - **Action:** Add console script entry point in `pyproject.toml` so `psyker` (or `psyker.exe`) is available after `pip install -e .`.

2. **Sandbox reset from CLI**  
   - PSYKER_SANDBOX: “psyker sandbox reset” clears workspace/tmp (logs optional).  
   - **Action:** Add CLI command `sandbox reset` (and optionally `sandbox reset --logs`) that calls `runtime.sandbox.reset()`.

3. **Diagnostics match spec**  
   - PSYKER_ERRORS: file:line:column, error type, one-line hint. LSP already uses parser; confirm diagnostic message format includes hint where applicable.

4. **All Grammar Context files behave as specified**  
   - Valid files parse and load (and run where tested); invalid files fail with the expected error type. Already covered by tests; spot-check once.

5. **No regressions**  
   - Full test suite passes; no new dependencies without human approval (AGENTS.md).

### Should-have for v0.1 (proper IDE experience)

6. **LSP completions**  
   - PSYKER_VSCODE_EXTENSION_PLAN: “Minimal Completion Targets (Optional): keywords per dialect, known worker names inside .psya, known task names.”  
   - **Action:** Implement LSP completion provider: (a) keywords per dialect from PSYKER_GRAMMAR §7, (b) worker names from open/parsed .psyw docs in workspace, (c) optionally task names for .psy.

7. **Hover / definitions help**  
   - Plan implies “proper definitions help” in the IDE.  
   - **Action:** Add LSP hover provider: for keywords and capability names, show a short description (e.g. from grammar or a small help map). Optionally hover on identifier → show “worker” / “agent” / “task” and where defined.

8. **Extension install/run instructions**  
   - User must be able to run the extension (F5 in VS Code or script).  
   - **Action:** Ensure INSTALL.md and run-psyker-extension.ps1 are correct; add a short “Editor setup” section to root README.

### Nice-to-have for v0.1

9. **Run from IDE**  
   - “Run through a code file”: run current task (or chosen agent+task) from the editor.  
   - **Action:** Add VS Code command / task: “Psyker: Run task” that (a) loads workspace .psy/.psya/.psyw (or current file’s project), (b) runs selected or default agent+task via CLI/runtime, (c) shows output in terminal or channel.

10. **Root README**  
    - Single entry point for users: what Psyker is, how to install, how to run (CLI + extension), link to specs.  
    - **Action:** Add `README.md` at repo root with install, quick start (load/run), testing, and editor setup.

11. **CI (optional)**  
    - CI_CHECKLIST: dialect separation, grammar, capability+sandbox, deps, negative tests.  
    - **Action:** Add a single CI job (e.g. GitHub Actions) that runs the test suite with `PYTHONPATH=src`. No new deps.

---

## Plan of Action (Ordered)

Execute in this order so the product is shippable early and improves incrementally.

### Phase A — Ship-ready CLI and extension (must-have)

| # | Action | Owner | Done when |
|---|--------|--------|-----------|
| A1 | Add console script to `pyproject.toml`: `psyker` → `psyker.__main__:main` | Codex/Cursor | `psyker` runs after `pip install -e .` |
| A2 | Add CLI command `sandbox reset` [--logs] calling `runtime.sandbox.reset()` | Codex/Cursor | `psyker> sandbox reset` clears workspace/tmp |
| A3 | Verify LSP diagnostic messages include hint when present (to_diagnostic) | Cursor | Red squiggles show message + hint |
| A4 | Run full test suite + quick manual pass on Grammar Context | Human/Cursor | All 21 tests pass; valid/invalid behave as spec |

### Phase B — Proper IDE experience (should-have)

| # | Action | Owner | Done when |
|---|--------|--------|-----------|
| B1 | LSP: completions for keywords per dialect (from PSYKER_GRAMMAR §7) | Codex | Trigger completion in .psy/.psya/.psyw → keywords listed |
| B2 | LSP: completions for worker names in .psya (from open .psyw docs or workspace) | Codex | After `use worker ` → worker names suggested |
| B3 | LSP: hover for keywords/capabilities with short help text | Codex | Hover on `fs.open` / `task` etc. → one-line description |
| B4 | Root README: install, quick start, run (CLI + extension), testing, editor setup | Cursor/Codex | New user can install and run from README |

### Phase C — Polish (nice-to-have)

| # | Action | Owner | Done when |
|---|--------|--------|-----------|
| C1 | VS Code command “Psyker: Run task” (load + run agent/task, show output) | Codex | User can run from editor without switching to terminal |
| C2 | Optional: completions for task names (e.g. in .psy or for a future “run” UI) | Codex | Optional v0.1 |
| C3 | CI: one job running tests with PYTHONPATH=src | Codex/Human | PRs run tests automatically |

---

## Definition of “v0.1 ready”

- **Minimum:** Phase A complete. CLI is installable (`psyker`), sandbox reset exists, diagnostics are spec-compliant, tests and Grammar Context pass.
- **Target:** Phase A + Phase B. IDE has completions and hover so it feels like a proper language extension; README exists.
- **Stretch:** Phase A + B + C. Run from IDE and CI in place.

---

## Spec References

- PSYKER_GRAMMAR.md — EBNF, reserved words (§7)
- PSYKER_ERRORS.md — Diagnostic format, hints
- PSYKER_CLI_SPEC.md — Commands, exit codes
- PSYKER_SANDBOX.md — sandbox reset
- PSYKER_VSCODE_EXTENSION_PLAN.md — Completions, diagnostics
- AGENTS.md — No new deps without approval

---

## Handoff for Codex

To continue development toward v0.1 ready:

1. **Phase A:** Implement A1 (console script), A2 (sandbox reset). Do not add new dependencies. Run tests after each change.
2. **Phase B:** Implement B1–B3 (LSP completions + hover), B4 (root README). Use existing psyker parser/validator; LSP server stays in Python (pygls).
3. **Phase C:** Optional C1–C3 when A and B are done.

Update TODO.md with a “v0.1 readiness” section and check off items as completed. Commit per logical change; reference this plan in commit messages.
