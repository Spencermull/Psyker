# Psyker EXE Plan — Standalone Terminal + Themed UI

> **Compliance:** Follows PSYKER_CLI_SPEC.md, PSYKER_SANDBOX.md, PSYKER_AI_AGENT_BRIEF.md, AGENTS.md (dependency policy).

---

## Goal

Package Psyker as a **standalone Windows console app** (`Psyker.exe`) that:

- Launches directly into the existing **Psyker REPL** (same commands/exit codes/sandbox rules).
- Uses a **“cool blue matrix” themed terminal UI**: blue-toned prompt/background accents, red flags, generally stylized but still readable.
- Does **not** break v0.1 constraints (sandbox-only, no background services, no OS-level kernel work).

This EXE is a **thin wrapper** around the existing runtime, not a new engine.

---

## Phase 1 — UX + Theme Design (Blue “Matrix” Look)

| # | Action | Details |
|---|--------|---------|
| 1.1 | Define theme palette | Use a dark console base with **blue primary** and **red accent** for flags/errors. Example: background near `#000814`, standard text light gray, prompt and command names bright cyan/blue, flags red. |
| 1.2 | Prompt styling | Make `psyker>` prompt stand out in blue: e.g. `PSYKER>` in bright blue followed by a subtle arrow or bracket. Keep it legible with good contrast. |
| 1.3 | Banner styling | Keep the existing banner text but allow subtle coloring: name/version in blue, byline neutral, maybe a faint divider line. |
| 1.4 | Matrix feel (within reason) | Optional: very light “scanline” / subtle animation at startup (e.g. a single line of animated dots or a short “initializing sandbox…” sequence) **without** hiding core diagnostics or slowing startup too much. No heavy ASCII art that hurts readability. |
| 1.5 | UX design tools | Prefer **prompt_toolkit**’s styling capabilities (already approved as a dependency) to design and iterate on colors/lexing. Additional UI toolkits (e.g. curses/rich, textual) require **explicit human approval** per AGENTS.md. |

**Constraints:**
- Do not sacrifice readability for style; error messages and diagnostics must remain clear.
- Keep animations very short and optional; Psyker remains a **fast REPL**, not a splash-screen app.

---

## Phase 2 — Clean Entry Layer for EXE

| # | Action | Details |
|---|--------|---------|
| 2.1 | Confirm single entry function | Ensure `psyker.__main__:main` is the canonical entry that: creates the default sandbox/runtime and runs the REPL. No side effects on import. |
| 2.2 | Optional refactor | If needed, introduce a small `psyker.cli.run()` (or similar) that `__main__.py` calls, to give PyInstaller a clean target. No behavior change. |

---

## Phase 3 — Packaging Strategy (PyInstaller)

| # | Action | Details |
|---|--------|---------|
| 3.1 | Dependency approval | Use **PyInstaller** for building the EXE. Add it as a **dev/build dependency only** (extras section), per AGENTS.md. |
| 3.2 | Spec file | Create `psyker.spec` (or similar) targeting `psyker.__main__:main` as entry point, console mode (not GUI). |
| 3.3 | Bundle layout | Start with **one-directory build** (`--onedir`): `dist/Psyker/Psyker.exe` + Python runtime, libraries, and required data. |
| 3.4 | Icons/resources | Include: `vscode-extension/icons/logo_icon.ico` (or `icons/logo_icon.ico`) as the EXE icon; optionally bundle `Grammar Context/` and `md contexts/` as read-only resources. |

---

## Phase 4 — Sandbox + Paths in Packaged EXE

| # | Action | Details |
|---|--------|---------|
| 4.1 | Sandbox root unchanged | Continue to use a user-local sandbox root (e.g. `%USERPROFILE%\\psyker_sandbox`). Do **not** use the PyInstaller temp dir as sandbox. |
| 4.2 | Working directory behavior | Treat the current working directory as the logical project root when the EXE is launched from a terminal; double‑clicking should still work by falling back to default sandbox behavior. |
| 4.3 | Logging | Keep logging to `psyker_sandbox/logs/psyker.log` as per PSYKER_SANDBOX.md. |

---

## Phase 5 — Themed Terminal Implementation

| # | Action | Details |
|---|--------|---------|
| 5.1 | prompt_toolkit theme | Use `prompt_toolkit` styles to apply the **blue matrix theme**: `command` class in blue, `flag` class in red, and allow a subtle tint on regular text if desired. |
| 5.2 | Prompt styling | Update `PROMPT_TEXT` and any prompt_toolkit prompt configuration to match the theme (e.g. `PSYKER>` in bright blue). |
| 5.3 | Optional animation | If desired, implement a **short** (sub‑second) animated line at startup using prompt_toolkit (e.g. a quick “initializing sandbox…” spinner), but keep it optional and non-blocking. |
| 5.4 | Fallback mode | If ANSI or prompt_toolkit is unavailable, fall back to the current plain REPL with simple blue/red coloring (as already implemented). |

---

## Phase 6 — Testing & Verification

| # | Action | Details |
|---|--------|---------|
| 6.1 | Automated tests | Continue to run `PYTHONPATH=src python -m unittest discover -s tests -v` on the Python codebase (non‑packaged). |
| 6.2 | Manual EXE tests | On a Windows machine without dev tooling, verify: banner, blue/red prompt and flags, load/run for sample tasks, sandbox utilities, sandbox reset, and correct exit codes for error cases. |
| 6.3 | Theme check | Confirm the new theme is legible in both dark and default Windows terminal backgrounds; adjust colors if needed. |

---

## Phase 7 — Docs & Distribution

| # | Action | Details |
|---|--------|---------|
| 7.1 | README section | Add a “Psyker.exe (Themed Terminal)” section to `README.md` with: where to find the EXE, how to run it (double-click vs terminal), and screenshots/gifs of the blue matrix theme. |
| 7.2 | Build script | Optionally add `scripts/build_exe.ps1` to automate PyInstaller builds. |

---

## Constraints & Approvals (AGENTS.md)

- **New dependencies:** `prompt_toolkit` is already in use; any additional UI/terminal libraries (e.g. `rich`, `textual`) require explicit human approval before adding.
- **No daemons/services:** Psyker remains a foreground console app; no background processes or installers that change system behavior beyond a normal app.
- **Sandbox-only execution:** The EXE must enforce the same sandbox rules as the Python CLI.

---

## Handoff for Codex

1. Implement Phases 2–5 in order, using this plan and existing md specs. The theme work (Phase 1 & 5) should reuse `prompt_toolkit` where possible.
2. Then create the PyInstaller spec and build script (Phase 3 & 7).
3. Finally, run tests and perform manual EXE verification (Phase 6).

No additional UI toolkit dependencies beyond `prompt_toolkit` without explicit human approval.

