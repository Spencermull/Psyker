# PSYKER ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Phase 1 Task Tracker

Codex marks steps complete when done. Cursor may add review or test tasks. Human approves merges.

---

## Phase 1 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Parser + Runtime + Sandbox + CLI

- [x] **Step 1** ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Project layout + lexer (src/, tokenize per PSYKER_GRAMMAR.md)
- [x] **Step 2** ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â AST + parsers (three dialects, Grammar Context valid/invalid)
- [x] **Step 3** ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Validator + load pipeline (registries, no partial updates on error)
- [x] **Step 4** ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Sandbox (root, layout, path validation, logs)
- [x] **Step 5** ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Executor (run flow, fs.*/exec.*, capabilities, sandbox cwd)
- [ ] **Step 6** ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â CLI (ls, stx, load, run, open/mkfile/mkdir/ps/cmd, exit codes)

---

## Review / follow-up (Cursor or human)

- [x] Review Step 1 lexer ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â spec-compliant; optional: STRING value without quotes + unescape for parser, lexer corpus test script.
- [x] Review Step 2 parsers Ã¢â‚¬â€ spec-compliant; valid/invalid corpus OK. Optional: normalize STRING arg (strip quotes, unescape) before Step 5.
- [x] Review Step 3 validator + load â€” spec-compliant; registries unchanged on failure; agentâ†’worker refs + count>0. Tests pass with PYTHONPATH=src.
- [ ] _Add items here after Codex steps, e.g. "Review Step 4 sandbox" or "Add invalid test for X"_

---

Ref: `md contexts/AUTONOMOUS_DEV_PLAN.md`





- [x] Step 5 executor implemented and verified (run_task + ExecutionResult + executor tests).
