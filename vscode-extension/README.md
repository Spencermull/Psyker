# Psyker VS Code Extension

Psyker language support for:
- `.psy` task files (`psy`)
- `.psya` agent files (`psya`)
- `.psyw` worker files (`psyw`)

## Install via VSIX (recommended)

From the repo root:

```bash
cd vscode-extension
npm install
vsce package
```

This creates:

```text
vscode-extension/psyker-vscode-<version>.vsix
```

Install it in VS Code:
1. Open Extensions (`Ctrl+Shift+X`).
2. Click `...` in the Extensions view.
3. Select `Install from VSIX...`.
4. Pick `psyker-vscode-<version>.vsix`.

No extension development host is required.

## Language Identity and Icons

After install:
- `*.psy`, `*.psya`, and `*.psyw` are auto-detected with Psyker language IDs.
- Syntax highlighting activates immediately.
- To show Psyker file icons, run:
  `Ctrl+Shift+P` -> `File Icon Theme` -> `Psyker Icons`.

## Runtime Prerequisites (for diagnostics/completions)

The extension starts the Python LSP server with `python -m psyker_lsp`.
Install runtime dependencies on the machine where VS Code runs:

```bash
pip install -e .
pip install -r requirements-lsp.txt
```

If Python/Psyker is not installed, syntax highlighting still works but language-server features will be unavailable.
