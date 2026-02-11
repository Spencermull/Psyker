from __future__ import annotations

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from psyker.cli import PROMPT_TEXT, PsykerCLI
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

    def test_run_repl_prints_welcome_banner(self) -> None:
        with patch("builtins.input", side_effect=EOFError):
            code = self.cli.run_repl()
        self.assertEqual(code, 0)
        output = self.out.getvalue()
        self.assertIn("Psyker v0.1.0 - DSL runtime for terminal automation", output)
        self.assertIn("By Spencer Muller", output)
        self.assertIn("#########################", output)
        self.assertIn("##  ## ##  ##", output)

    def test_help_uses_no_color_when_not_tty(self) -> None:
        self.assertEqual(self.cli.execute_line("help"), 0)
        self.assertNotIn("\x1b[", self.out.getvalue())

    def test_help_colorizes_commands_and_flags_when_tty(self) -> None:
        class _TTYStringIO(io.StringIO):
            def isatty(self) -> bool:  # pragma: no cover - behavior exercised via CLI
                return True

        tty_out = _TTYStringIO()
        cli = PsykerCLI(self.runtime, out=tty_out, err=self.err)
        self.assertEqual(cli.execute_line("help"), 0)
        output = tty_out.getvalue()
        self.assertIn("\x1b[34mload\x1b[0m", output)
        self.assertIn("\x1b[31m--output\x1b[0m", output)

    def test_help_does_not_use_color_for_non_tty_output_even_if_stdout_is_tty(self) -> None:
        with patch("sys.stdout.isatty", return_value=True):
            self.assertEqual(self.cli.execute_line("help"), 0)
        self.assertNotIn("\x1b[", self.out.getvalue())

    def test_help_cmds_lists_commands(self) -> None:
        self.assertEqual(self.cli.execute_line("help --cmds"), 0)
        output = self.out.getvalue()
        self.assertIn("load", output)
        self.assertIn("run", output)
        self.assertIn("help", output)

    def test_help_version(self) -> None:
        self.assertEqual(self.cli.execute_line("help --version"), 0)
        self.assertIn("Psyker v0.1.0", self.out.getvalue())

    def test_help_about(self) -> None:
        self.assertEqual(self.cli.execute_line("help --about"), 0)
        output = self.out.getvalue()
        self.assertIn("Psyker v0.1.0 - DSL runtime for terminal automation", output)
        self.assertIn("By Spencer Muller", output)

    def test_help_unknown_option_is_clear_error(self) -> None:
        self.assertEqual(self.cli.execute_line("help --bad"), 1)
        self.assertIn("Unknown help option '--bad'", self.err.getvalue())

    def test_run_repl_uses_prompt_toolkit_theme_when_tty(self) -> None:
        cli = PsykerCLI(self.runtime)

        class _FakeStyle:
            captured: dict[str, str] | None = None

            @staticmethod
            def from_dict(style_dict: dict[str, str]) -> str:
                _FakeStyle.captured = style_dict
                return "style-object"

        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("psyker.cli._pt_Style", new=_FakeStyle):
                    with patch("psyker.cli._pt_prompt", side_effect=EOFError) as mocked_prompt:
                        code = cli.run_repl()

        self.assertEqual(code, 0)
        self.assertEqual(mocked_prompt.call_args.args[0], [("class:prompt", PROMPT_TEXT)])
        self.assertEqual(mocked_prompt.call_args.kwargs["style"], "style-object")
        self.assertIn("lexer", mocked_prompt.call_args.kwargs)
        self.assertEqual(mocked_prompt.call_args.kwargs["include_default_pygments_style"], False)
        self.assertEqual(_FakeStyle.captured["prompt"], "ansibrightblue bold")
        self.assertEqual(_FakeStyle.captured["command"], "ansibrightblue bold")
        self.assertEqual(_FakeStyle.captured["flag"], "ansired bold")

    def test_run_repl_falls_back_when_prompt_toolkit_is_unavailable(self) -> None:
        cli = PsykerCLI(self.runtime)
        with patch("psyker.cli._pt_prompt", new=None):
            with patch("sys.stdin.isatty", return_value=True):
                with patch("sys.stdout.isatty", return_value=True):
                    with patch("builtins.input", side_effect=EOFError) as mocked_input:
                        code = cli.run_repl()
        self.assertEqual(code, 0)
        mocked_input.assert_called_once_with(PROMPT_TEXT)

    def test_run_repl_falls_back_after_prompt_toolkit_error(self) -> None:
        cli = PsykerCLI(self.runtime)

        class _FakeStyle:
            @staticmethod
            def from_dict(style_dict: dict[str, str]) -> str:
                return "style-object"

        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("psyker.cli._pt_Style", new=_FakeStyle):
                    with patch("psyker.cli._pt_prompt", side_effect=RuntimeError("prompt failed")) as mocked_prompt:
                        with patch("builtins.input", side_effect=EOFError) as mocked_input:
                            code = cli.run_repl()

        self.assertEqual(code, 0)
        mocked_prompt.assert_called_once()
        mocked_input.assert_called_once_with(PROMPT_TEXT)


if __name__ == "__main__":
    unittest.main()
