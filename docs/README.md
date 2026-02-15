# Psyker User Guide

This guide is for end users of Psyker v0.1.x.  
Specification and planning files under `md contexts/` are internal and not required for normal usage.

## Quick Start

1. Install Psyker:

```bash
pip install -e .
```

2. Launch the CLI:

```bash
python -m psyker
```

3. Load a worker, agent, and task:

```text
PSYKER> load "Grammar Context/valid/worker_basic.psyw"
PSYKER> load "Grammar Context/valid/agent_basic.psya"
PSYKER> load "Grammar Context/valid/task_basic.psy"
```

4. Run the task:

```text
PSYKER> run alpha hello
```

## CLI Commands

Use `help` in the REPL for full usage text. Core commands:

- `load <path>`: load one `.psy`, `.psya`, or `.psyw` file.
- `load --dir <path>`: load all `.psyw`, `.psya`, and `.psy` files in a directory (non-recursive, workers -> agents -> tasks).
- `ls workers|agents|tasks`: list currently loaded definitions.
- `stx worker|agent|task <name> [--output table|json]`: inspect a loaded definition.
- `run <agent> <task>`: execute a task through an agent.
- `open <path>`: print file contents from sandbox workspace.
- `mkfile <path>`: create file in sandbox workspace.
- `mkdir <path>`: create directory in sandbox workspace.
- `ps "<powershell command>"`: run PowerShell command in sandbox workspace.
- `cmd "<cmd command>"`: run cmd command in sandbox workspace.
- `sandbox reset [--logs|--clear-logs]`: clear workspace/tmp (and optionally logs).
- `help [--cmds|--version|--about|<command>]`: show command help.
- `exit` or `quit`: exit REPL.

Entry flags:

- `--version`: print Psyker version and exit.
- `--verbose` / `-v`: enable troubleshooting output to stderr.
- `--check-updates`: optional startup-only update check.
- `--gui`: start the GUI instead of CLI.

## GUI Usage

Start GUI:

```bash
pip install -e ".[gui]"
python -m psyker --gui
```

Main GUI capabilities:

- Embedded Psyker terminal uses the same command handlers as CLI.
- Top context bar shows sandbox and loaded state.
- Right monitor panel shows runtime lists and task progress.
- Bottom explorer can load `.psy`, `.psya`, `.psyw` files by double-click.
- Output controls:
  - `Copy Output` copies terminal output to clipboard.
  - `Clear Output` clears visible terminal output.
- Running task controls:
  - `Stop` button and `Ctrl+C` request cancellation.
- Theme control:
  - Toolbar toggle switches light/dark theme (dark default).

## File Formats Overview

Psyker has three DSL file types:

- `.psyw` (worker): defines capabilities and sandbox/cwd policy.
- `.psya` (agent): defines worker usage and counts.
- `.psy` (task): defines one or more tasks and executable statements.

Minimal examples:

```psyker
worker w1 {
  sandbox "sandbox";
  cwd "sandbox/workspace";
  allow fs.open;
  allow exec.ps;
}
```

```psyker
agent alpha {
  use worker w1 count = 1;
}
```

```psyker
@access { agents: [alpha], workers: [w1] }
task hello {
  fs.open "input.txt";
}
```
