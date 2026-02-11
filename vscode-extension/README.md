# Psyker VS Code Extension

Phase 2a provides syntax highlighting for:

- `.psy` (tasks)
- `.psya` (agents)
- `.psyw` (workers)

The extension registers language IDs `psy`, `psya`, and `psyw`, and applies TextMate grammars for:

- comments (`# ...`)
- strings (`"..."` with escapes)
- reserved keywords per dialect

Phase 2b adds LSP diagnostics.
