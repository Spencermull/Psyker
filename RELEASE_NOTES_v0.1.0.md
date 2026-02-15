# Psyker v0.1.0 (Alpha)

First alpha release of Psyker, a DSL runtime for terminal automation on Windows.

## What's included

- **Three dialects:** `.psy` (tasks), `.psya` (agents), `.psyw` (workers)
- **REPL CLI:** load, run, ls, stx, sandbox reset, dev utilities
- **Sandbox-only execution:** isolated workspace at `%USERPROFILE%\psyker_sandbox`
- **VS Code extension:** syntax highlighting, LSP diagnostics, completions, hover, definitions
- **Standalone EXE:** PyInstaller build, no Python required
- **GUI:** Native desktop app with embedded terminal (PsykerGUI.exe)

## Install

**Python (dev):**
```bash
pip install -e .
pip install -r requirements-lsp.txt
```

**Windows installer (recommended):**
- Download `Psyker-Setup-0.1.0.exe` from Assets → Run → Next → Install → Finish
- Launches Psyker GUI by default; CLI also available from Start Menu

**Windows (zip):**
- **CLI:** Download `Psyker-CLI-0.1.0.zip` → extract and run `Psyker.exe`
- **GUI:** Download `PsykerGUI-0.1.0.zip` → extract and run `PsykerGUI.exe`

## Quick start

```
psyker> load "path/to/worker.psyw"
psyker> load "path/to/agent.psya"
psyker> load "path/to/task.psy"
psyker> run <agent> <task>
```

## Known limitations (v0.1)

- Sandbox-only execution (no trusted mode)
- LSP requires Python + Psyker for diagnostics
- Windows only (EXE/installer)

## Full changelog

See [md contexts/RELEASE_V01_AUDIT.md](md%20contexts/RELEASE_V01_AUDIT.md) for the release audit.
