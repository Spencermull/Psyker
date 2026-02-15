# Psyker UI Assets

Drop visual assets here to skin the GUI without code changes.

- `icons/*.svg`:
  - Monochrome line icons using `currentColor` for stroke/fill.
  - The app tints these at runtime to match theme colors.
- `decals/*.png`:
  - Optional HUD decals (corner ornaments, texture strips).
  - Rendered at low opacity by `DecalOverlay` and scaled to window size.

Current icon names used by the GUI:

- `cpu.svg`
- `agents.svg`
- `workers.svg`
- `tasks.svg`
- `files.svg`
