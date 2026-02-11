from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from psyker.errors import SandboxError
from psyker.sandbox import Sandbox


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
        self.assertTrue(str(resolved).startswith(str(self.root)))

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


if __name__ == "__main__":
    unittest.main()
