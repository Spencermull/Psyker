# AUDIT.md — PSYKER v0.1 Anti-Confirmation Bias & Release Gate

## Purpose
Ensure implementation matches the spec and avoids scope creep or example-driven parsing.

---

## Identity & Scope (Must Hold)
- Interpreted DSL; no native compilation.
- Session-only runtime; no persistence/background services.
- Sandbox-only in v0.1.
- Developer tool orientation.

## Dialect Separation
- .psy contains only tasks (+ optional @access).
- .psya contains only agent workforce declarations.
- .psyw contains only worker envelopes (sandbox/cwd/allow).
- Cross-dialect constructs raise DialectError.

## Grammar & Examples
- Grammar in PSYKER_GRAMMAR.md is source of truth.
- Examples are illustrative only.
- Parsers validated against positive + negative grammar tests.
- Errors include file:line:column with actionable hints.

## Runtime Enforcement
- Identity-based @access enforced before execution.
- Capability checks per statement.
- Sandbox blocks traversal, absolute escapes, symlink escape.
- Shell cwd confined to sandbox workspace.

## CLI Contract
- ls/stx/load/run conform to CLI spec.
- CLI utilities treated as dev/test-first.
- No undocumented commands.

## Extensibility Discipline
- Additive-only within v0.x; versioned grammar + feature flags.
- Registries for capabilities/CLI/runtime middleware.
- No premature policies/retries in agents for v0.1.

## Dependency & AI Hygiene
- No new deps without approval.
- Human auditing only.
- Large changes require rigid audit; small PRs minimal gate.

## Release Gate (v0.1)
- Grammar corpus passes (pos+neg).
- Dialect misuse → DialectError.
- Sandbox violations → SandboxError.
- Permission violations → PermissionError.
- Windows CLI smoke tests pass.

## Access & Sandbox Checks
- Non-task files include required access headers.
- Tasks without @access default to deny-all.
- CLI utilities confined to shared session sandbox workspace.
