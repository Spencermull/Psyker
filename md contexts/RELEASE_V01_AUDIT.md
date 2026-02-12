# Release v0.1.0 (Alpha) — Final Audit

**Date:** 2025-02-11  
**Version:** 0.1.0 (Alpha)

---

## Audit Summary

| Area | Status | Notes |
|------|--------|------|
| **Tests** | Pass | 48 tests, all passing |
| **CI** | Pass | GitHub Actions test workflow on master/main |
| **Runtime** | Ready | Lexer, parser (3 dialects), validator, sandbox, executor |
| **CLI** | Ready | ls, stx, load, run, open/mkfile/mkdir/ps/cmd, help, exit, sandbox reset |
| **VS Code** | Ready | Syntax highlighting, LSP (diagnostics, completions, hover, definitions) |
| **EXE** | Ready | PyInstaller onedir build (psyker.spec) |
| **Installer** | Ready | Inno Setup wizard (installer/Psyker.iss, scripts/build_installer.ps1) |
| **Docs** | Ready | README, md contexts, VS Code extension README |

---

## Test Results

```
Ran 48 tests in ~0.9s — OK
```

- Lexer, parser, runtime load, sandbox, executor, CLI
- Phase A diagnostics, Phase B LSP features, Phase C navigation
- Phase 2 EXE entry

---

## Deliverables

| Item | Location |
|------|----------|
| Python package | `pip install -e .` |
| VS Code extension | `vscode-extension/` → `.vsix` |
| Standalone EXE | `pyinstaller psyker.spec` → `dist/Psyker/` |
| Installer | `scripts/build_installer.ps1` → `dist/Psyker-Setup-0.1.0.exe` |

---

## Known Limitations (v0.1)

- Sandbox-only execution (no trusted mode)
- No network sandboxing
- LSP requires Python + Psyker on machine for diagnostics
- Installer build requires Inno Setup (build-time only)

---

## Release Checklist

- [x] All tests pass
- [x] CI passes
- [x] README up to date (install, run, installer, test)
- [x] Version 0.1.0 in pyproject.toml
- [ ] Tag v0.1.0
- [ ] Push to origin
- [ ] Create GitHub release (alpha)
- [ ] Attach Psyker-Setup-0.1.0.exe (build manually if needed)
