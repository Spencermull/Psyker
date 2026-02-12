# Installer Wizard — Feasibility Assessment

> **Goal:** Let users download a single installer EXE, run it, and have Psyker fully set up (including sandbox) without touching the repo or Python.

---

## Summary: **Feasible — Proceed to Codex**

The installer wizard is feasible with standard tools. No new runtime dependencies; no changes to AGENTS.md constraints. Sandbox is already auto-created on first run; the installer’s job is to place the Psyker runtime and optional shortcuts.

---

## 1. Current State (from docs)

| Source | Detail |
|--------|--------|
| **psyker.spec** | PyInstaller onedir build → `dist/Psyker/` (Psyker.exe + _internal/) |
| **PSYKER_SANDBOX.md** | Sandbox root: `%USERPROFILE%\psyker_sandbox` (or `PSYKER_SANDBOX_ROOT`) |
| **sandbox.py** | `Sandbox.create_default()` → `ensure_layout()` creates `workspace/`, `logs/`, `tmp/` on first use |
| **CODEX_EXE_PLAN.md** | Phase 4.1: sandbox root stays user-local; Phase 7: optional build script |
| **AGENTS.md** | No new runtime deps without approval; build-time tools OK |

---

## 2. Sandbox Behavior

**Already automatic:** The runtime creates the sandbox on first run:

```python
# cli.py
runtime = RuntimeState(sandbox=Sandbox.create_default())  # → ensure_layout()
```

So `%USERPROFILE%\psyker_sandbox\workspace`, `logs`, `tmp` are created when the user first runs Psyker.exe. The installer does **not** need to create them for sandbox to work.

**Optional:** The installer could pre-create the sandbox during install (e.g. `%USERPROFILE%\psyker_sandbox` + subdirs). That’s a nice-to-have, not required.

---

## 3. Installer Approach

**PyInstaller is not an installer.** It produces executables; it does not create install wizards.

**Standard approach:** Use a separate installer tool:

- **Inno Setup** — widely used, free, scriptable
- **NSIS** — alternative
- **WiX** — MSI-based

**Recommended:** Inno Setup. No Python dependency; `.iss` script plus `iscc.exe` (build-time only).

**Flow:**
1. Run `pyinstaller psyker.spec` → produce `dist/Psyker/`
2. Run `iscc installer.iss` → produce `Psyker-Setup-0.1.0.exe`
3. User downloads `Psyker-Setup-0.1.0.exe`, runs it, follows wizard steps.

---

## 4. What the Installer Should Do

| Step | Action |
|------|--------|
| **Source** | Bundle `dist/Psyker/` as input |
| **Wizard** | Welcome, choose install location (default `%LOCALAPPDATA%\Psyker` or `C:\Program Files\Psyker`), optional shortcuts |
| **Install** | Copy `dist/Psyker/` to chosen location |
| **Shortcuts** | Start Menu shortcut to `Psyker.exe`; optional Desktop shortcut |
| **Optional** | Pre-create `%USERPROFILE%\psyker_sandbox` (workspace, logs, tmp) |
| **Uninstall** | Add entry in Programs & Features; remove shortcuts and install dir |

---

## 5. Build Pipeline

```
pyinstaller psyker.spec          → dist/Psyker/
iscc installer/Psyker.iss        → dist/Psyker-Setup-0.1.0.exe
```

Script: `scripts/build_installer.ps1` (or `.bat`):

```powershell
# 1. Build EXE
pyinstaller psyker.spec
# 2. Build installer
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\Psyker.iss
```

Inno Setup is typically installed on the dev machine; CI can use `choco install innosetup` or the portable compiler.

---

## 6. Constraints Check (AGENTS.md)

- **New dependencies:** None. Inno Setup is a build-time external tool, not a pip package.
- **Sandbox-only:** Unchanged; installer only configures install location.
- **No daemons/services:** Installer is a one-time wizard; no background processes.

---

## 7. Scope for Codex

- Create `installer/Psyker.iss` (Inno Setup script)
- Create `scripts/build_installer.ps1` that runs PyInstaller then `iscc`
- Optionally pre-create sandbox (workspace, logs, tmp) during install
- Add short README section describing the installer flow

**Out of scope:** Code signing, auto-update, PATH integration (unless explicitly requested).

---

## 8. Recommendation

**Proceed to Codex.** Add a brief (e.g. `CODEX_INSTALLER_WIZARD_BRIEF.md`) that references this feasibility doc and specifies the installer steps.
