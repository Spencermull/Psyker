# Codex — Step 6 CLI (Psyker Bash)

Implement **Phase 1 Step 6** only. Steps 1–5 are done: lexer, parser, validator, load pipeline, sandbox, executor. Runtime has `RuntimeState`, `load_file(path)`, `run_task(agent_name, task_name)`, and `Sandbox`.

---

## What to build

1. **Interactive REPL** (“Psyker Bash”): read line, parse as command (verb + args), dispatch to handler. REPL syntax is **bash-like** (space-separated, quoted strings); file grammar (`.psy`/`.psya`/`.psyw`) is unchanged.

2. **Commands** (register in a command registry: verb → handler, optional help):
   - **ls workers** | **ls agents** | **ls tasks** — Table-like listing (name/id, type, counts).
   - **stx worker \<name>** | **stx agent \<name>** | **stx task \<name>** — Inspect one definition. Optional **--output table** | **--output json** (default table).
   - **load \<path>** — Call `runtime.load_file(Path(path))`. Extension must be `.psy` / `.psya` / `.psyw`; otherwise error. On success, confirm; on failure, print diagnostic and set exit code.
   - **run \<agent_name> \<task_name>** — Call `runtime.run_task(agent_name, task_name)`. Print stdout/stderr and status; set exit code from result or exception.
   - **open \<path>** — Resolve path under sandbox (e.g. `runtime.sandbox.resolve_in_workspace` or `resolve_under_root`), read file, print content. Sandbox path validation required.
   - **mkfile \<path>** — Create file under sandbox (parents if needed). Sandbox path validation required.
   - **mkdir \<path>** — Create directory under sandbox. Sandbox path validation required.
   - **ps "\<powershell command>"** — Run `powershell -NoProfile -Command "<cmd>"` with cwd = sandbox workspace.
   - **cmd "\<cmd command>"** — Run `cmd /c "<cmd>"` with cwd = sandbox workspace.
   - **help** [command] — (Optional) Print usage for all commands or for one command.

3. **Exit codes** (map exceptions and run result to process exit code):
   - `0` success
   - `1` general error
   - `2` syntax/dialect error (SyntaxError, DialectError)
   - `3` permission/access (PermissionError, AccessError)
   - `4` sandbox (SandboxError)
   - `5` execution failure (ExecError, or exec subprocess non-zero)

4. **Entrypoint:** `python -m psyker` (and optionally console script `psyker` in pyproject.toml) starts the REPL. Single global `RuntimeState(sandbox=Sandbox.create_default())` (or equivalent) for the session.

5. **Specs:** PSYKER_CLI_SPEC.md (full), PSYKER_ERRORS.md (diagnostic format). Use existing `psyker.errors` types; print diagnostics via `to_diagnostic()` or equivalent when a command fails.

---

## Done when

- All commands above work from the REPL.
- `load` + `run` use the existing runtime; dev utilities (open, mkfile, mkdir, ps, cmd) use sandbox only.
- Exit codes match the table (2 for parse/dialect, 3 for access/permission, 4 for sandbox, 5 for exec).
- Grammar Context: loading valid files and running a task works; loading invalid files fails with the expected error and exit code.

---

## Constraints (AGENTS.md)

- No new dependencies without human approval (stdlib only for REPL/CLI).
- Command registry: verb → handler (and optional help); keep REPL parsing separate from file grammars.

---

Update **TODO.md** (mark Step 6 complete) and commit when done.
