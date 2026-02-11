# Psyker VS Code Usability Plan — Language, Icons, Debugging, and Simple Install

> **Compliance:** Follows PSYKER_VSCODE_EXTENSION_PLAN.md, PSYKER_CLI_SPEC.md, PSYKER_GRAMMAR.md, AGENTS.md.
>
> **High‑level goal:** Make Psyker feel like a first‑class language in VS Code:
> - Easy to install (`.vsix`, no repo wiring needed)
> - Files with `.psy/.psya/.psyw` automatically recognized and nicely highlighted
> - Your **logo icon** used consistently for Psyker files
> - Solid editing UX (completions, hovers, navigation, snippets)
> - A minimal but real **debug story** for Psyker code inside VS Code

---

## Phase 0 — Requirements Summary (What “good” means)

Before changing anything, codify what “good” UX looks like:

- **Install experience**
  - User downloads a `.vsix` and installs it via “Install from VSIX…” in VS Code.
  - They do **not** need to open the repo, run F5, or configure extensionDevelopmentPath.

- **Language recognition + icons**
  - Any file named `*.psy`, `*.psya`, `*.psyw`:
    - Automatically gets the **Psyker language mode** (`psy`, `psya`, `psyw`).
    - Shows your **logo icon** in the Explorer.

- **Editing experience**
  - Typing Psyker code feels like a real language:
    - Syntax highlighting is accurate and stable.
    - Intellisense for **keywords**, **agents/workers/tasks**, and **@access** lists.
    - Hover provides meaningful docs for keywords and capabilities.
    - Quick snippets to scaffold new tasks/agents/workers.

- **Debugging story**
  - A user can:
    - Set breakpoints or at least run Psyker tasks with visible step-by-step output.
    - Use a simple **“Psyker: Debug task”** or **“Psyker: Run task”** command from the editor.
  - v0.1 focuses on **debugging via the CLI runtime** (no heavy debugger protocol yet):
    - Launch tasks via a VS Code debug configuration that shells out to `psyker` or `python -m psyker`.
    - Capture stdout/stderr in a dedicated debug console.

---

## Phase 1 — Simple .vsix Packaging & Install

| # | Action | Details |
|---|--------|---------|
| 1.1 | Verify extension packaging | Ensure `vscode-extension/package.json` is valid and `vsce package` works from that folder. |
| 1.2 | Standardize packaging script | Add a short script (e.g. `vscode-extension/package.ps1` or npm script) that runs: `npm install` then `vsce package`. Result: `psyker-vscode-<version>.vsix`. |
| 1.3 | Install instructions (root README) | Update root `README.md` with a **simple, user‑facing flow**:<br>- Download `.vsix` from Releases<br>- In VS Code: Extensions → “Install from VSIX…” → select the file. |
| 1.4 | LSP runtime assumptions | Document that the extension expects:<br>- Python available on PATH<br>- `psyker` package + `psyker_lsp` installed (e.g. `pip install -e .` and `pip install -r requirements-lsp.txt`), or adjust extension to find a bundled Python env if needed in the future. |

**Acceptance criteria:**
- A new user can download the `.vsix`, install it, and immediately get syntax highlighting + diagnostics for `.psy/.psya/.psyw` **without** opening the repo as an extension dev host.

---

## Phase 2 — Icons & Language Association (Make Files Feel Native)

| # | Action | Details |
|---|--------|---------|
| 2.1 | Confirm icon theme wiring | `vscode-extension/package.json` already contributes `iconThemes` with `psyker-icons.json`. Verify that installing the extension + selecting the icon theme shows your logo for `.psy/.psya/.psyw`. |
| 2.2 | Default icon usage | Document in README and extension README how to activate the icon theme:<br>- Command Palette → “File Icon Theme” → “Psyker Icons”. |
| 2.3 | Language IDs and detection | Ensure the `languages` contribution maps `.psy`, `.psya`, `.psyw` to the right `id` and that files are auto‑detected as Psyker dialects. |
| 2.4 | Deep description in extension README | Add a dedicated section describing:<br>- What each dialect is (`psy` / `psya` / `psyw`)<br>- Which icon appears for which file type<br>- How VS Code chooses the language mode. |

**Acceptance criteria:**
- Opening `*.psy/*.psya/*.psyw` shows your logo icon in the Explorer and the Psyker language mode automatically.

---

## Phase 3 — Editing UX: Completions, Hovers, Snippets (Deep Descriptions)

### 3.1 Completions (LSP)

| # | Action | Details |
|---|--------|---------|
| 3.1.1 | Extend keyword completions | In `psyker_lsp/server.py`, ensure `keywords_for_suffix` covers all reserved words from `PSYKER_GRAMMAR.md` (per dialect). |
| 3.1.2 | Agent/worker/task names | Add completions for known identifiers:<br>- In `.psya`, when completing `use worker` or in `@access { workers: [...] }`, suggest existing worker names from parsed `.psyw` files.<br>- In `.psy`, for `@access { agents: [...] }`, suggest existing agent names. |
| 3.1.3 | Context-aware suggestions | Avoid noisy suggestions; restrict completions to relevant positions (e.g. inside `@access` lists, after `use worker`, at task header). |

### 3.2 Hovers (Deep descriptions)

| # | Action | Details |
|---|--------|---------|
| 3.2.1 | Expand hover map | Extend `_HOVER_TEXT_BY_WORD` (or equivalent) with **clear, human‑readable descriptions** for:<br>- `task`, `agent`, `worker`<br>- `@access`, `agents`, `workers`<br>- `fs.open`, `fs.create`, `exec.ps`, `exec.cmd`<br>- `sandbox`, `cwd`, `allow`. |
| 3.2.2 | Link to concepts | Where helpful, mention cross‑reference to specs (e.g. “See PSYKER_PERMISSIONS.md §2 for capability mapping”). |
| 3.2.3 | Hover on identifiers | For task/agent/worker names, show a short description:<br>- Kind (task/agent/worker)<br>- Source file path<br>- Maybe a summary of key fields (e.g. worker sandbox path, capabilities). |

### 3.3 Snippets (Editor‑side)

| # | Action | Details |
|---|--------|---------|
| 3.3.1 | Task snippet | Add a VS Code snippet `psyker-task-basic` that expands to a spec‑compliant task skeleton with `@access` and at least one statement. |
| 3.3.2 | Agent snippet | Snippet to create a basic agent definition with `use worker` block and count. |
| 3.3.3 | Worker snippet | Snippet to create a worker with sandbox, cwd, and `allow` capabilities. |
| 3.3.4 | Deep descriptions in snippet docs | Each snippet should have a **detailed description** explaining what it is and how it relates to the specs (e.g. “Creates a basic task with deny‑all access; modify `@access` as needed.”). |

**Acceptance criteria:**
- While typing, the user sees **useful, context‑aware suggestions**, and hovering over keywords/identifiers gives **clear, spec‑aligned explanations**.
- Typing `task`/`agent`/`worker` + snippet trigger yields a correct, well‑documented skeleton.

---

## Phase 4 — Navigation & Refactor Support

| # | Action | Details |
|---|--------|---------|
| 4.1 | Go to definition | Implement LSP “go to definition” so that clicking or F12 on:<br>- a worker name in `.psya` (`use worker w1`) jumps to `w1`’s `.psyw` file<br>- (optional) agent names in `.psy` `@access { agents: [...] }` jump to `.psya`. |
| 4.2 | Document symbols | Add LSP document symbols so the Outline view lists:<br>- tasks in `.psy`<br>- workers in `.psyw`<br>- agents in `.psya`. |
| 4.3 | Rename (optional v0.1+) | If feasible, implement a conservative LSP rename for:<br>- worker names<br>- agent names<br>- task names<br>ensuring all three dialects are updated consistently. If not ready for v0.1, document it as a future feature. |

**Acceptance criteria:**
- From any agent file, you can jump to the referenced worker definition.
- Outline view meaningfully shows Psyker constructs.

---

## Phase 5 — Run & Debug from VS Code

> Goal: A minimal, practical way to **run and debug Psyker tasks from inside VS Code**.

### 5.1 Run Task Command

| # | Action | Details |
|---|--------|---------|
| 5.1.1 | VS Code command | Add a command `psyker.runTask` (“Psyker: Run task”) that:<br>- If triggered from a `.psy` file, infers the task name under the cursor or prompts for one.<br>- Prompts for an agent (default from a setting, e.g. `psyker.defaultAgent`).<br>- Spawns a VS Code terminal that runs `psyker` (or `python -m psyker`) and issues the appropriate `load` + `run` commands. |
| 5.1.2 | Settings | Add extension settings:<br>- `psyker.defaultAgent` (string)<br>- `psyker.cliPath` (path or command for running CLI, default `psyker`)<br>- `psyker.sandboxRoot` override (optional). |

### 5.2 Debug Config (Lightweight)

| # | Action | Details |
|---|--------|---------|
| 5.2.1 | Launch configuration | Add a `debugger` contribution or preconfigured launch snippet in extension README, e.g.:<br>- “Psyker: Debug current task” that runs a Python debug session (`"program": "psyker_frozen_entry.py"` or similar) with arguments to load a specific agent/task, or<br>- A simple “Run in integrated terminal” launch config. |
| 5.2.2 | Logging hooks | Ensure runtime/CLI logs enough information (agent, worker, operation) so that reading sandbox logs + terminal output is a usable “debug session” even before step‑level debugging exists. |

**Note (v0.1 scope):** A full debug adapter (DAP) is out‑of‑scope; focus on **launching Psyker with good visibility** rather than fine‑grained stepping.

---

## Phase 6 — Documentation & UX Polish

| # | Action | Details |
|---|--------|---------|
| 6.1 | Extension README deep pass | Rewrite `vscode-extension/README.md` with deep, user‑focused sections:<br>- What Psyker is<br>- How to install via `.vsix`<br>- How to configure Python / CLI<br>- How to use snippets, navigation, run/debug commands<br>- Screenshots of icons and blue matrix terminal. |
| 6.2 | Root README cross‑links | From root `README.md`, link to the extension README and summarize:<br>- Install → Open folder → Edit Psyker files → Run task. |
| 6.3 | Troubleshooting section | Add a “Troubleshooting” area:<br>- “No diagnostics?” → Check Python path / `psyker_lsp` installation.<br>- “Icons don’t show?” → Activate Psyker icon theme.<br>- “Run task fails?” → Check sandbox root, CLI path. |

---

## Handoff for Codex

1. Implement **Phases 1–2** first (simple `.vsix` install, icons + language association) and update both the extension README and root README with clear, step‑by‑step instructions.
2. Then implement **Phase 3** (completions, hovers, snippets with deep descriptions) and **Phase 4** (navigation support).
3. Finally, implement **Phase 5** (run/debug commands) and do a documentation pass (Phase 6).

At each step:
- Use `md contexts/PSYKER_VSCODE_EXTENSION_PLAN.md`, `PSYKER_GRAMMAR.md`, `PSYKER_CLI_SPEC.md` as spec references.
- Keep changes minimal and well‑scoped; no new dependencies beyond what’s already approved (vscode-languageclient, prompt_toolkit, pygls).
- Run tests (`PYTHONPATH=src python -m unittest discover -s tests -v`) and manual extension smoke tests.
- Update `TODO.md` with a “VS Code usability” section and mark phases as they complete.

