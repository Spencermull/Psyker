# Codex Brief: v0.1 Release Prep

Psyker is one CI fix away from a proper v0.1 release. Execute the following.

---

## Step 1 — Push the CI Fix (if not already pushed)

The sandbox test `test_resolve_under_root_accepts_relative_inside` fails on GitHub Actions due to path casing on Windows. The fix is already applied: it now uses `resolved.resolve().relative_to(self.root.resolve())` instead of `str(resolved).startswith(str(self.root))`.

Verify the fix is committed and pushed. If not:
```bash
git add tests/test_step4_sandbox.py
git commit -m "Fix sandbox test for Windows path casing on CI"
git push
```

---

## Step 2 — Update TODO.md

Mark Phase C items complete:
- [x] C1 VS Code command "Psyker: Run task" (already implemented in extension)
- [x] C3 CI job for test suite (added in Phase 4)

C2 (task name completions) remains optional.

---

## Step 3 — Verify CI Passes

After pushing, check GitHub Actions. If it passes, v0.1 is ready to tag.

---

## One-Line Prompt for Codex

```text
Check that the sandbox test fix (test_resolve_under_root_accepts_relative_inside using relative_to) is committed and pushed. Update TODO.md: mark C1 and C3 complete. Report CI status. See md contexts/CODEX_V01_RELEASE_BRIEF.md.
```
