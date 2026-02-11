# Psyker

Psyker is a small DSL runtime with three dialects:
- `.psy` for task definitions
- `.psya` for agent definitions
- `.psyw` for worker definitions

## Install

```bash
pip install -e .
pip install -r requirements-lsp.txt
```

## VS Code (Install via VSIX)

Install the Psyker VS Code extension without dev-host mode:

```bash
cd vscode-extension
npm install
vsce package
```

That creates `psyker-vscode-<version>.vsix` in `vscode-extension/`.

Then in VS Code:
1. Open Extensions (`Ctrl+Shift+X`).
2. Click `...` (top-right).
3. Select `Install from VSIX...`.
4. Pick `psyker-vscode-<version>.vsix`.

After install:
1. Open any `*.psy`, `*.psya`, or `*.psyw` file.
2. Optional icon theme: `Ctrl+Shift+P` -> `File Icon Theme` -> `Psyker Icons`.
3. Run `Psyker: Run task` from Command Palette to execute the task under your cursor.

LSP diagnostics require Python + Psyker runtime on your machine:

```bash
pip install -e .
pip install -r requirements-lsp.txt
```

### Optional (but recommended): live typing colors in the REPL

Psyker supports **live highlighting while you type** (commands in blue, `--flags` in red) when `prompt_toolkit` is available.
It is included as a Psyker dependency via `pyproject.toml`, but if you need to install it manually:

```bash
python -m pip install prompt_toolkit
```

## Run

Start the CLI:

```bash
psyker
```

or:

```bash
python -m psyker
```

Basic load/run flow:

```text
psyker> load "Grammar Context/valid/worker_basic.psyw"
psyker> load "Grammar Context/valid/agent_basic.psya"
psyker> load "Grammar Context/valid/task_basic.psy"
psyker> run alpha hello
```

## Psyker.exe (Themed Terminal)

Build the Windows EXE from repo root with the existing PyInstaller spec:

```bash
python -m pip install -e ".[build]"
pyinstaller psyker.spec
```

Build output (onedir):

```text
dist/Psyker/Psyker.exe
```

Run it from a terminal or by double-clicking `dist/Psyker/Psyker.exe`.
The EXE launches the same sandbox-only REPL and keeps CLI behavior/exit codes aligned with `python -m psyker`.

When `prompt_toolkit` is available in a TTY, the terminal uses a blue matrix look:
- blue `PSYKER>` prompt and command verb highlighting
- red `--flags`
- dark-friendly input styling tuned for typical Windows terminals

If themed input is unavailable, Psyker falls back to the plain REPL behavior.
Sandbox root defaults to `%USERPROFILE%\\psyker_sandbox` and can be overridden with `PSYKER_SANDBOX_ROOT`.

## Test

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## VS Code Extension

For full extension documentation (language modes, snippets, navigation, run/debug commands, settings, troubleshooting), see `vscode-extension/README.md`.
