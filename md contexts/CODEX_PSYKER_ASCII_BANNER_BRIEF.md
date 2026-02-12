# Codex Brief: Replace Startup Banner with PSYKER Slant ASCII Art

Replace the hex-eye ASCII art in the CLI welcome banner with "PSYKER" spelled in slant ASCII art font style.

---

## Target File

`src/psyker/cli.py` — replace the `METRO_HEX_EYE_ASCII` constant.

---

## Reference Style (Slant ASCII Font)

The user wants this slant/italic 3D style:

```
    ____  _______  ____ __ __________ 
   / __ \/ ___/\ \/ / //_// ____/ __ \
  / /_/ /\__ \  \  / ,<  / __/ / /_/ /
 / ____/___/ /  / / /| |/ /___/ _, _/ 
/_/    /____/  /_/_/ |_/_____/_/ |_|  
```

---

## Task

1. Generate "PSYKER" in the same slant ASCII art font style (5 lines, underscore/slash 3D look).
2. Replace `METRO_HEX_EYE_ASCII` in `cli.py` with the new constant (e.g. `PSYKER_BANNER_ASCII`).
3. Ensure the banner still fits in typical terminal width (~80 cols). Center or left-align as needed.
4. Run tests: `PYTHONPATH=src python -m unittest discover -s tests -v`
5. Update `tests/test_step6_cli.py` `test_run_repl_prints_welcome_banner`: replace assertions for `"#########################"` and `"##  ## ##  ##"` with assertions that match the new slant PSYKER banner (e.g. `self.assertIn("PSYKER", output)` or a distinctive line from the slant art like `"/ __ \\"` or `"____"`).

---

## Verification

After change, run `psyker` and confirm the banner displays "PSYKER" in slant style before the REPL prompt.

---

## One-Line Prompt for Codex

```text
Replace METRO_HEX_EYE_ASCII in src/psyker/cli.py with "PSYKER" in slant ASCII art font (5-line underscore/slash style). Update test assertions if they check banner content. Run tests. See md contexts/CODEX_PSYKER_ASCII_BANNER_BRIEF.md.
```
