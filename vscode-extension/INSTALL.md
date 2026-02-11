# How to run the Psyker extension

Cursor often **does not show** the "Launch Psyker Extension" option (it doesn’t support Extension Development Host the same way VS Code does). Use one of these methods instead.

---

## Option 1: Run from VS Code (recommended)

1. **Install VS Code** from https://code.visualstudio.com/ if you don’t have it.

2. **Open the Psyker repo in VS Code**  
   - Start VS Code.  
   - File → Open Folder → select `c:\Users\spenc\Documents\Psyker`.

3. **Install extension dependencies** (once):
   ```powershell
   cd c:\Users\spenc\Documents\Psyker\vscode-extension
   npm install
   ```

4. **Launch the extension**  
   - In VS Code: **Run and Debug** (Ctrl+Shift+D).  
   - In the dropdown at the top, select **"Launch Psyker Extension"**.  
   - Press **F5** or click the green play button.  
   - A second window opens with the extension loaded. Open a `.psy` / `.psya` / `.psyw` file there to test.

---

## Option 2: Command line (any editor)

From **PowerShell**, run (replace with your actual path if different):

```powershell
code "c:\Users\spenc\Documents\Psyker" --extensionDevelopmentPath="c:\Users\spenc\Documents\Psyker\vscode-extension"
```

That starts VS Code with the Psyker extension loaded in development mode. Then open a `.psy`, `.psya`, or `.psyw` file in that window.

**Note:** `code` is the VS Code command-line launcher. If it’s not in your PATH, use the full path to `Code.exe` (e.g. in your user folder under `AppData\Local\Programs\Microsoft VS Code\bin\Code.exe`).

---

## Option 3: Install as a .vsix (use extension without dev mode)

1. Install the packaging tool: `npm install -g @vscode/vsce`
2. Package the extension:
   ```powershell
   cd c:\Users\spenc\Documents\Psyker\vscode-extension
   npm install
   vsce package
   ```
3. In VS Code: Extensions (Ctrl+Shift+X) → **...** (top right) → **Install from VSIX...** → choose the generated `.vsix` file.

**Note:** The LSP expects to run from the repo with `PYTHONPATH=src`. For a packaged install you may need to set that in your environment or the extension may only provide syntax highlighting until the server path is fixed.
