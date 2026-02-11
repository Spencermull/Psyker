# Psyker VS Code Extension

This extension provides:

- `.psy` (tasks)
- `.psya` (agents)
- `.psyw` (workers)

## How to run / install the extension

### Option A: Run from workspace (recommended for development)

1. **Install Node dependencies** (once):
   ```bash
   cd vscode-extension
   npm install
   cd ..
   ```

2. **Open the Psyker repo** in VS Code (File → Open Folder → select the `Psyker` folder, not `vscode-extension`).

3. **Install Python LSP deps** (once) so diagnostics work:
   ```bash
   pip install -r requirements-lsp.txt
   ```

4. **Launch the extension:** Press **F5** or go to Run and Debug (Ctrl+Shift+D), choose **"Launch Psyker Extension"**, then Run. A new VS Code window opens with the extension loaded.

5. In the new window, open any `.psy`, `.psya`, or `.psyw` file (e.g. from `Grammar Context/valid` or `invalid`) to see syntax highlighting and LSP diagnostics.

### Option B: Install as a .vsix (optional)

1. Install the VS Code extension packaging tool: `npm install -g @vscode/vsce`
2. In the repo: `cd vscode-extension`, run `npm install`, then `vsce package`.
3. In VS Code: Extensions view (Ctrl+Shift+X) → "..." menu → **Install from VSIX...** → select the generated `.vsix` file.

**Note:** The LSP server runs `python -m psyker_lsp` with `PYTHONPATH` set to the repo `src` folder. For Option B, the extension still expects to be run from the repo layout (or you’d need to change how the server is started). Option A is the most reliable for this repo.

---

## Syntax Highlighting (Phase 2a)

The extension registers language IDs `psy`, `psya`, and `psyw`, and applies TextMate grammars for:

- comments (`# ...`)
- strings (`"..."` with escapes)
- reserved keywords per dialect

## LSP Diagnostics (Phase 2b)

The extension launches a Python language server (`python -m psyker_lsp`) and reports parser diagnostics on open/change for Psyker files.

Supported diagnostics:

- `SyntaxError`
- `DialectError`
- optional `ReferenceError` for agent-to-worker references across currently open documents

## Dependency Approval Note

Phase 2b requires the Python dependency `pygls` (and `lsprotocol`).
Per `md contexts/AGENTS.md`, this dependency addition requires human approval before installation/use in shared environments.
