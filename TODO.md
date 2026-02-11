# PSYKER ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Phase 1 Task Tracker

Codex marks steps complete when done. Cursor may add review or test tasks. Human approves merges.

---

## Phase 1 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Parser + Runtime + Sandbox + CLI

- [x] **Step 1** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Project layout + lexer (src/, tokenize per PSYKER_GRAMMAR.md)
- [x] **Step 2** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â AST + parsers (three dialects, Grammar Context valid/invalid)
- [x] **Step 3** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Validator + load pipeline (registries, no partial updates on error)
- [ ] **Step 4** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Sandbox (root, layout, path validation, logs)
- [ ] **Step 5** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Executor (run flow, fs.*/exec.*, capabilities, sandbox cwd)
- [ ] **Step 6** ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â CLI (ls, stx, load, run, open/mkfile/mkdir/ps/cmd, exit codes)

---

## Review / follow-up (Cursor or human)

- [x] Review Step 1 lexer Ã¢â‚¬â€ spec-compliant; optional: STRING value without quotes + unescape for parser, lexer corpus test script.
- [x] Review Step 2 parsers â€” spec-compliant; valid/invalid corpus OK. Optional: normalize STRING arg (strip quotes, unescape) before Step 5.
- [ ] _Add items here after Codex steps, e.g. "Review Step 3 validator" or "Add invalid test for X"_

---

Ref: `md contexts/AUTONOMOUS_DEV_PLAN.md`



