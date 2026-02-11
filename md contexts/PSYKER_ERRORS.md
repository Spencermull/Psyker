# PSYKER v0.1 — Errors & Diagnostics

> **Examples Notice**
>
> All code snippets in this documentation are **illustrative examples** of valid syntax.
> Implementations MUST follow **PSYKER_GRAMMAR.md** and MUST NOT hardcode behavior based on example patterns,
> fixed statement ordering, or specific example file layouts.


PSYKER must provide **actionable diagnostics** with file/line/column when possible.

---

## 1) Error Types (v0.1)

### SyntaxError
Raised when input does not match the grammar for the current dialect.
- Include expected token(s) and the unexpected token.

### DialectError
Raised when a file contains constructs not allowed for its extension/dialect.
Example: `exec.ps` inside `.psya`, or `agent {}` inside `.psy`.

### ReferenceError
Raised when a referenced entity does not exist.
Examples:
- agent uses unknown worker
- `run` references unknown agent/task

### PermissionError
Raised when a worker lacks capability required by a task statement.

### AccessError (may be implemented as PermissionError in v0.1)
Raised when task `@access` disallows the current agent/worker.

### SandboxError
Raised when a filesystem path escapes the sandbox or is otherwise invalid.

### ExecError
Raised when `exec.ps` or `exec.cmd` fails (non-zero exit code).
- Include exit code, stdout, stderr (truncated in CLI if needed).

---

## 2) Diagnostic Format (Recommended)

```text
error[DialectError]: 'exec.ps' is not allowed in agent files (.psya)
  --> crawler.psya:12:5
   |
12 |     exec.ps "Write-Output 'hi'";
   |     ^^^^^^^ move this into a task (.psy)
```

Minimum fields:
- error type
- message
- file:line:column
- one-line hint

---

## 3) Common Examples

### Example A: Dialect misuse

Input (`crawler.psya`):
```psyker
agent crawler {
    exec.ps "Write-Output 'no'";
}
```

Output:
- DialectError at `exec.ps` token

---

### Example B: Missing capability

Worker:
```psyker
worker w {
    sandbox "./psyker_sandbox";
    cwd "./psyker_sandbox/workspace";
    allow fs.open;
}
```

Task:
```psyker
task t {
    exec.ps "Write-Output 'hi'";
}
```

Running `t` with `w` must raise PermissionError: missing `exec.ps`.

---

### Example C: Sandbox escape

```psyker
task read {
    fs.open "../secrets.txt";
}
```

Must raise SandboxError.

## Error Philosophy

Errors are programmer-facing: precise, technical, and actionable. Include file:line:column and a concrete fix hint.

## Missing Access Header
Parsers must emit a DialectError when required access headers are missing for non-task files.
