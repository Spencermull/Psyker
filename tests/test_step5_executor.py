from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from psyker.errors import AccessError, ExecError, PermissionError, SandboxError
from psyker.runtime import RuntimeState
from psyker.sandbox import Sandbox


class ExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.grammar = Path("Grammar Context")
        self.temp = tempfile.TemporaryDirectory()
        self.sandbox = Sandbox(Path(self.temp.name) / "psyker_sandbox")
        self.sandbox.ensure_layout()
        self.runtime = RuntimeState(sandbox=self.sandbox)
        self.runtime.load_file(self.grammar / "valid" / "worker_basic.psyw")
        self.runtime.load_file(self.grammar / "valid" / "agent_basic.psya")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_run_valid_task(self) -> None:
        self.runtime.load_file(self.grammar / "valid" / "task_basic.psy")
        input_file = self.sandbox.resolve_in_workspace("input.txt")
        input_file.parent.mkdir(parents=True, exist_ok=True)
        input_file.write_text("hello", encoding="utf-8")

        result = self.runtime.run_task("alpha", "hello")
        self.assertEqual(result.status_code, 0)
        self.assertEqual(result.agent, "alpha")
        self.assertEqual(result.worker, "w1")
        self.assertEqual(result.task, "hello")
        self.assertIn("hello", result.stdout)

    def test_access_deny_all_without_header(self) -> None:
        self.runtime.load_file(self.grammar / "invalid" / "task_no_access_header.psy")
        with self.assertRaises(AccessError):
            self.runtime.run_task("alpha", "noaccess")

    def test_path_traversal_is_blocked(self) -> None:
        self.runtime.load_file(self.grammar / "invalid" / "task_path_traversal.psy")
        with self.assertRaises(SandboxError):
            self.runtime.run_task("alpha", "escape")

    def test_missing_capability_raises_permission_error(self) -> None:
        self.runtime.load_file(self.grammar / "valid" / "task_multiple_stmts.psy")
        with self.assertRaises(PermissionError):
            self.runtime.run_task("alpha", "multi")

    def test_cancelled_task_raises_exec_error(self) -> None:
        self.runtime.load_file(self.grammar / "valid" / "task_basic.psy")
        self.runtime.set_cancel_check(lambda: True)
        with self.assertRaises(ExecError):
            self.runtime.run_task("alpha", "hello")

    def test_runtime_exec_uses_hidden_windows_subprocess_when_available(self) -> None:
        if sys.platform != "win32":
            self.skipTest("Windows-specific subprocess behavior")

        self.runtime.load_file(self.grammar / "valid" / "task_basic.psy")
        input_file = self.sandbox.resolve_in_workspace("input.txt")
        input_file.parent.mkdir(parents=True, exist_ok=True)
        input_file.write_text("hello", encoding="utf-8")

        class _Proc:
            returncode = 0

            def poll(self):
                return 0

            def communicate(self, timeout=None):
                return ("ok\n", "")

        with patch("psyker.runtime.subprocess.Popen", return_value=_Proc()) as mocked:
            self.runtime.run_task("alpha", "hello")

        kwargs = mocked.call_args.kwargs
        self.assertIn("creationflags", kwargs)
        self.assertIn("startupinfo", kwargs)


if __name__ == "__main__":
    unittest.main()
