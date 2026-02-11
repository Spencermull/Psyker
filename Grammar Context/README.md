# PSYKER Grammar Test Corpus

This corpus validates that parsers and runtime logic are **grammar-driven**, not example-driven.

## Structure
- valid/   → files that MUST parse and validate
- invalid/ → files that MUST fail with specific errors

## Expectations
- Cross-dialect constructs → DialectError
- Syntax issues (e.g., missing ;) → SyntaxError
- Invalid capabilities → SyntaxError or ValidationError
- Missing access header on non-task files → DialectError
- Tasks without @access → Runtime AccessError (deny-all)
- Path traversal attempts → SandboxError

## How to Use
Run the parser against all files in `valid/` and assert success.
Run the parser/validator against all files in `invalid/` and assert the expected error types.