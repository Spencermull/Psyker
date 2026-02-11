from __future__ import annotations

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from psyker.cli import PsykerCLI
from psyker.runtime import RuntimeState
from psyker.sandbox import Sandbox


class CLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.sandbox = Sandbox(Path(self.temp.name) / "psyker_sandbox")
        self.sandbox.ensure_layout()
        self.runtime = RuntimeState(sandbox=self.sandbox)
        self.out = io.StringIO()
        self.err = io.StringIO()
        self.cli = PsykerCLI(self.runtime, out=self.out, err=self.err)
        self.grammar = Path("Grammar Context")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_load_list_and_inspect(self) -> None:
        self.assertEqual(self.cli.execute_line(f'load "{self.grammar / "valid" / "worker_basic.psyw"}"'), 0)
        self.assertEqual(self.cli.execute_line(f'load "{self.grammar / "valid" / "agent_basic.psya"}"'), 0)
        code = self.cli.execute_line("ls workers")
        self.assertEqual(code, 0)
        self.assertIn("w1", self.out.getvalue())
        code = self.cli.execute_line("stx agent alpha --output json")
        self.assertEqual(code, 0)
        self.assertIn('"name": "alpha"', self.out.getvalue())

    def test_run_success_with_custom_task(self) -> None:
        self.cli.execute_line(f'load "{self.grammar / "valid" / "worker_basic.psyw"}"')
        self.cli.execute_line(f'load "{self.grammar / "valid" / "agent_basic.psya"}"')
        input_file = self.sandbox.resolve_under_root("sandbox/input.txt")
        input_file.parent.mkdir(parents=True, exist_ok=True)
        input_file.write_text("hello-cli", encoding="utf-8")

        task_file = Path(self.temp.name) / "read_only.psy"
        task_file.write_text(
            '@access { agents: [alpha], workers: [w1] }\n'
            "task read_only {\n"
            '  fs.open "sandbox/input.txt";\n'
            "}\n",
            encoding="utf-8",
        )
        self.assertEqual(self.cli.execute_line(f'load "{task_file}"'), 0)
        code = self.cli.execute_line("run alpha read_only")
        self.assertEqual(code, 0)
        self.assertIn("hello-cli", self.out.getvalue())

    def test_exit_code_mapping(self) -> None:
        bad = self.grammar / "invalid" / "task_missing_semicolon.psy"
        self.assertEqual(self.cli.execute_line(f'load "{bad}"'), 2)

        self.cli.execute_line(f'load "{self.grammar / "valid" / "worker_basic.psyw"}"')
        self.cli.execute_line(f'load "{self.grammar / "valid" / "agent_basic.psya"}"')
        self.cli.execute_line(f'load "{self.grammar / "invalid" / "task_no_access_header.psy"}"')
        self.assertEqual(self.cli.execute_line("run alpha noaccess"), 3)

        self.cli.execute_line(f'load "{self.grammar / "invalid" / "task_path_traversal.psy"}"')
        self.assertEqual(self.cli.execute_line("run alpha escape"), 4)

    def test_dev_utilities_and_exec_error_code(self) -> None:
        self.assertEqual(self.cli.execute_line("mkdir logs"), 0)
        self.assertEqual(self.cli.execute_line("mkfile logs/out.txt"), 0)
        target = self.sandbox.resolve_in_workspace("logs/out.txt")
        target.write_text("utility", encoding="utf-8")
        self.assertEqual(self.cli.execute_line("open logs/out.txt"), 0)
        self.assertIn("utility", self.out.getvalue())

        with patch("psyker.cli.subprocess.run") as mocked:
            mocked.return_value.returncode = 1
            mocked.return_value.stdout = ""
            mocked.return_value.stderr = "bad"
            self.assertEqual(self.cli.execute_line('cmd "echo hi"'), 5)

    def test_sandbox_reset_preserves_or_clears_logs(self) -> None:
        workspace_file = self.sandbox.resolve_in_workspace("logs/out.txt")
        workspace_file.parent.mkdir(parents=True, exist_ok=True)
        workspace_file.write_text("utility", encoding="utf-8")

        tmp_file = self.sandbox.tmp / "tmp.txt"
        tmp_file.write_text("tmp", encoding="utf-8")
        self.sandbox.log("alpha", "w1", "fs.open", "ok")
        self.assertTrue(self.sandbox.log_file.exists())

        self.assertEqual(self.cli.execute_line("sandbox reset"), 0)
        self.assertFalse(workspace_file.exists())
        self.assertFalse(tmp_file.exists())
        self.assertTrue(self.sandbox.log_file.exists())

        workspace_file = self.sandbox.resolve_in_workspace("logs/out2.txt")
        workspace_file.parent.mkdir(parents=True, exist_ok=True)
        workspace_file.write_text("utility2", encoding="utf-8")
        tmp_file = self.sandbox.tmp / "tmp2.txt"
        tmp_file.write_text("tmp2", encoding="utf-8")

        self.assertEqual(self.cli.execute_line("sandbox reset --logs"), 0)
        self.assertFalse(workspace_file.exists())
        self.assertFalse(tmp_file.exists())
        self.assertFalse(self.sandbox.log_file.exists())


if __name__ == "__main__":
    unittest.main()
