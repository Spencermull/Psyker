# AGENTS.md — PSYKER v0.1 (Cursor AI Chat + Codex Terminal Operating Rules)

## Purpose
This document governs how AI assistance is used to develop PSYKER v0.1. It enforces scope discipline, low abstraction, human approval gates, and safety. Examples in specs are illustrative only; the grammar is the source of truth.

---

## Operating Model
- Cursor AI Chat: design review, grammar clarification, refactor guidance, test planning.
- Codex (terminal): code generation for small, isolated patches (parser, validator, CLI wiring, tests).
- No autonomous agents. Human-in-the-loop for all merges.

---

## Hard Constraints (v0.1)
- Interpreted DSL; no native compilation.
- Session-only runtime; no persistence or background services.
- Strict dialect separation by file extension: .psy (tasks), .psya (agents), .psyw (workers).
- Strict DSL in files; bash-like feel only in the interactive CLI.
- Identity-based access control via @access { agents: [...], workers: [...] }.
- Sandbox-only execution (no whole-PC access in v0.1).
- CLI utilities (open/ps/cmd/etc.) are dev/test-first; production intent lives in tasks.

---

## Examples Are Not the Language
- Code snippets in MD files are illustrative.
- Implementations MUST follow PSYKER_GRAMMAR.md.
- Do NOT hardcode example patterns or statement orderings.
- Validate against a grammar test corpus (positive + negative cases).

---

## Low-Abstraction Coding Rules
- Prefer explicit modules: lexer, per-dialect parser, validator, sandbox, executor, CLI.
- Keep REPL parsing separate from file grammars.
- Avoid hidden frameworks/magic. If abstraction is introduced, justify in PR.

---

## Dependency Policy
- No new dependencies without explicit human approval.
- Prefer stdlib or pre-approved parsing approach; lock parser strategy early.
- Any new dep requires: rationale, alternatives considered, impact on tooling.

---

## Commit & Approval Policy
- AI may propose commits; must not push to main.
- Commits should be small and reference spec sections.
- Human approval required for merges.
- Rigid audits for large changes; light PR checks for small tasks.

---

## Drift & Reset Protocol
Trigger reset if AI:
- repeats fixes, expands scope, or adds deps/frameworks.
Reset steps:
1) Restate current goal + constraints.
2) Repost relevant spec excerpts.
3) Ask for minimal patch aligned to grammar/spec.

---

## Future-Proofing Guardrails
- Design AST to allow future agent logic-bearing fields (no policies/retries in v0.1).
- Architect sandbox policy so trusted modes can be added in future major versions without rewriting executor.

## Access & Sandbox Rules (v0.1)
- Access headers are mandatory for non-task files; tasks default deny-all if @access omitted.
- CLI utilities operate in a shared session sandbox workspace; production intent lives in tasks.
