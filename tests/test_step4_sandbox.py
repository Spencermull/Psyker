from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from psyker.errors import SandboxError
from psyker.sandbox import Sandbox, default_sandbox_root


class SandboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "psyker_sandbox"
        self.sandbox = Sandbox(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_creates_layout_on_first_use(self) -> None:
        self.sandbox.ensure_layout()
        self.assertTrue(self.sandbox.workspace.exists())
        self.assertTrue(self.sandbox.logs.exists())
        self.assertTrue(self.sandbox.tmp.exists())

    def test_resolve_under_root_accepts_relative_inside(self) -> None:
        resolved = self.sandbox.resolve_under_root("workspace/file.txt")
        # Use relative_to for robust containment check (avoids path casing issues on Windows CI)
        resolved.resolve().relative_to(self.root.resolve())

    def test_resolve_under_root_rejects_traversal(self) -> None:
        with self.assertRaises(SandboxError):
            self.sandbox.resolve_under_root("../secret.txt")

    def test_resolve_under_root_rejects_absolute_outside(self) -> None:
        outside = Path(self.tempdir.name).parent / "outside.txt"
        with self.assertRaises(SandboxError):
            self.sandbox.resolve_under_root(str(outside))

    def test_log_writes_entry(self) -> None:
        self.sandbox.log("alpha", "w1", "fs.open", "ok")
        content = self.sandbox.log_file.read_text(encoding="utf-8")
        self.assertIn("agent=alpha", content)
        self.assertIn("worker=w1", content)

    def test_default_sandbox_root_uses_home_not_pyinstaller_temp(self) -> None:
        home = Path(self.tempdir.name) / "home"
        home.mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "home", return_value=home):
                with patch.object(sys, "_MEIPASS", str(Path(self.tempdir.name) / "bundle"), create=True):
                    root = default_sandbox_root()
        self.assertEqual(root, (home / "psyker_sandbox").resolve())


if __name__ == "__main__":
    unittest.main()
