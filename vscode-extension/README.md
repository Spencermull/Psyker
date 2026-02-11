# Psyker VS Code Extension

Language support for the Psyker DSL:
- `.psy` task files
- `.psya` agent files
- `.psyw` worker files

## Install

### Install via VSIX (one-file install)

```bash
cd vscode-extension
npm install
vsce package
```

This produces:

```text
psyker-vscode-<version>.vsix
```

Install in VS Code:
1. Open Extensions (`Ctrl+Shift+X`).
2. Click `...` in the Extensions pane.
3. Select `Install from VSIX...`.
4. Choose `psyker-vscode-<version>.vsix`.

### Python/LSP prerequisites

The extension launches `python -m psyker_lsp` for diagnostics, completions, hovers, and navigation.

```bash
pip install -e .
pip install -r requirements-lsp.txt
```

If Python/LSP is missing, syntax highlighting still works but language-server features do not.

## Language Modes and Icons

After install, VS Code auto-detects:
- `*.psy` as `psy`
- `*.psya` as `psya`
- `*.psyw` as `psyw`

Psyker file types use the Psyker logo as their language icon in Explorer without requiring a custom file icon theme.

## Editing Experience

### Completions

Context-aware completions include:
- dialect keywords (`task`, `agent`, `worker`, `allow`, `sandbox`, etc.)
- agent names in `@access { agents: [...] }`
- worker names in `use worker ...` and `@access { workers: [...] }`
- task-name completion after `task ...`
- capability completion after `allow ...`

### Hovers

Hovers include spec-aligned descriptions for:
- core keywords and directives (`task`, `@access`, `agents`, `workers`, `use`, `count`)
- capabilities and operations (`fs.open`, `fs.create`, `exec.ps`, `exec.cmd`, `sandbox`, `cwd`)
- identifiers (task/agent/worker name, source location, short summary)

### Snippets

Built-in snippets:
- `psyker-task-basic` in `.psy`
- `psyker-agent-basic` in `.psya`
- `psyker-worker-basic` in `.psyw`

Each snippet expands to a spec-compliant starter skeleton with descriptive metadata.

## Navigation

### Go to Definition

- From `.psya`: `use worker w1` -> jump to worker definition.
- From `.psy` access lists: agent/worker names in `@access` -> jump to matching definition.

Use `F12` or `Ctrl+Click`.

### Outline / Document Symbols

The Outline view shows:
- task definitions in `.psy`
- agent definitions in `.psya`
- worker definitions in `.psyw`

## Run and Debug

### Command: `Psyker: Run task`

From an open `.psy` editor:
1. Infers task under cursor (or prompts if needed).
2. Prompts for agent (uses `psyker.defaultAgent` when set).
3. Launches Psyker CLI in an integrated terminal.
4. Loads worker/agent/task files and runs `run <agent> <task>`.

### Command: `Psyker: Debug task`

Runs the same flow in a dedicated debug terminal and emits extra `stx` inspection output for agent/task.

### Command: `Psyker: Add Debug Launch Configuration`

Creates/updates `.vscode/launch.json` with a Python launch config (`module: psyker`) so you can run Psyker from VS Code debug workflows.

### Settings

- `psyker.defaultAgent`: preferred agent name for run/debug commands.
- `psyker.cliPath`: command/path used to launch Psyker CLI (default `psyker`).
- `psyker.sandboxRoot`: optional value exported as `PSYKER_SANDBOX_ROOT` for run/debug terminals.

## Example

With `task_basic.psy`, `agent_basic.psya`, and `worker_basic.psyw` in a workspace:
1. Open `task_basic.psy`.
2. Run `Psyker: Run task`.
3. Select agent `alpha`.
4. View terminal output from the Psyker REPL execution.

## Troubleshooting

### No diagnostics/completions/hover

- Confirm Python is on PATH (`python --version`).
- Confirm LSP deps installed:
  - `pip install -e .`
  - `pip install -r requirements-lsp.txt`

### Psyker icons do not appear

- Try a different file icon theme; some third-party themes disable language-mode fallback icons.

### `Psyker: Run task` or `Debug task` fails

- Verify `psyker` command works in a terminal (or set `psyker.cliPath`).
- Confirm selected agent/task names exist and files parse.
- If needed, set `psyker.sandboxRoot` explicitly.
