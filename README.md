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

## Test

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## VS Code Extension

See `vscode-extension/INSTALL.md`.
