from __future__ import annotations

import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from psyker.errors import ExecError
from psyker import __version__
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

    def test_load_dir_loads_worker_agent_task_in_dependency_order(self) -> None:
        bundle = Path(self.temp.name) / "bundle"
        bundle.mkdir(parents=True, exist_ok=True)

        worker_path = bundle / "m_worker.psyw"
        agent_path = bundle / "a_agent.psya"
        task_path = bundle / "z_task.psy"
        worker_path.write_text((self.grammar / "valid" / "worker_basic.psyw").read_text(encoding="utf-8"), encoding="utf-8")
        agent_path.write_text((self.grammar / "valid" / "agent_basic.psya").read_text(encoding="utf-8"), encoding="utf-8")
        task_path.write_text((self.grammar / "valid" / "task_basic.psy").read_text(encoding="utf-8"), encoding="utf-8")

        code = self.cli.execute_line(f'load --dir "{bundle}"')
        self.assertEqual(code, 0)
        self.assertIn("w1", self.runtime.workers)
        self.assertIn("alpha", self.runtime.agents)
        self.assertIn("hello", self.runtime.tasks)

        output = self.out.getvalue()
        worker_idx = output.find(f"loaded: {worker_path}")
        agent_idx = output.find(f"loaded: {agent_path}")
        task_idx = output.find(f"loaded: {task_path}")
        self.assertGreaterEqual(worker_idx, 0)
        self.assertGreater(agent_idx, worker_idx)
        self.assertGreater(task_idx, agent_idx)

    def test_load_glob_loads_matching_files_in_dependency_order(self) -> None:
        bundle = Path(self.temp.name) / "glob_bundle"
        bundle.mkdir(parents=True, exist_ok=True)
        worker_path = bundle / "worker_x.psyw"
        agent_path = bundle / "agent_x.psya"
        task_path = bundle / "task_x.psy"
        worker_path.write_text((self.grammar / "valid" / "worker_basic.psyw").read_text(encoding="utf-8"), encoding="utf-8")
        agent_path.write_text((self.grammar / "valid" / "agent_basic.psya").read_text(encoding="utf-8"), encoding="utf-8")
        task_path.write_text((self.grammar / "valid" / "task_basic.psy").read_text(encoding="utf-8"), encoding="utf-8")

        code = self.cli.execute_line(f'load "{bundle}/*.psy*"')
        self.assertEqual(code, 0)
        self.assertIn("w1", self.runtime.workers)
        self.assertIn("alpha", self.runtime.agents)
        self.assertIn("hello", self.runtime.tasks)

    def test_verbose_mode_logs_load_path_to_stderr(self) -> None:
        cli = PsykerCLI(self.runtime, out=self.out, err=self.err, verbose=True)
        code = cli.execute_line(f'load "{self.grammar / "valid" / "worker_basic.psyw"}"')
        self.assertEqual(code, 0)
        self.assertIn("[verbose] load path=", self.err.getvalue())

    def test_default_mode_does_not_log_verbose_messages(self) -> None:
        code = self.cli.execute_line(f'load "{self.grammar / "valid" / "worker_basic.psyw"}"')
        self.assertEqual(code, 0)
        self.assertNotIn("[verbose]", self.err.getvalue())

    def test_run_cancellation_prints_message_and_returns_130(self) -> None:
        self.cli.runtime.load_file(self.grammar / "valid" / "worker_basic.psyw")
        self.cli.runtime.load_file(self.grammar / "valid" / "agent_basic.psya")
        with patch.object(self.cli.runtime, "run_task", side_effect=ExecError("Task cancelled by user.")):
            code = self.cli.execute_line("run alpha hello")
        self.assertEqual(code, 130)
        self.assertIn("task cancelled", self.out.getvalue())

    def test_run_success_with_custom_task(self) -> None:
        self.cli.execute_line(f'load "{self.grammar / "valid" / "worker_basic.psyw"}"')
        self.cli.execute_line(f'load "{self.grammar / "valid" / "agent_basic.psya"}"')
        input_file = self.sandbox.resolve_in_workspace("input.txt")
        input_file.parent.mkdir(parents=True, exist_ok=True)
        input_file.write_text("hello-cli", encoding="utf-8")

        task_file = Path(self.temp.name) / "read_only.psy"
        task_file.write_text(
            '@access { agents: [alpha], workers: [w1] }\n'
            "task read_only {\n"
            '  fs.open "input.txt";\n'
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

    def test_cmd_exec_uses_hidden_windows_subprocess_when_available(self) -> None:
        if sys.platform != "win32":
            self.skipTest("Windows-specific subprocess behavior")

        with patch("psyker.cli.subprocess.run") as mocked:
            mocked.return_value.returncode = 0
            mocked.return_value.stdout = ""
            mocked.return_value.stderr = ""
            code = self.cli.execute_line('cmd "echo hi"')

        self.assertEqual(code, 0)
        kwargs = mocked.call_args.kwargs
        self.assertIn("creationflags", kwargs)
        self.assertIn("startupinfo", kwargs)

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
        self.assertIn(f"Psyker v{__version__} - DSL runtime for terminal automation", output)
        self.assertIn("By Spencer Muller", output)
        self.assertIn("____  _____ __  __ _____ ______", output)
        self.assertIn("/ ____/___/ /  / /  ___/ / /___", output)

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
        self.assertIn(f"Psyker v{__version__}", self.out.getvalue())

    def test_help_about(self) -> None:
        self.assertEqual(self.cli.execute_line("help --about"), 0)
        output = self.out.getvalue()
        self.assertIn(f"Psyker v{__version__} - DSL runtime for terminal automation", output)
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
        self.assertIn("history", mocked_prompt.call_args.kwargs)
        self.assertEqual(mocked_prompt.call_args.kwargs["include_default_pygments_style"], False)
        self.assertEqual(_FakeStyle.captured["prompt"], "ansibrightblue bold")
        self.assertEqual(_FakeStyle.captured["command"], "ansibrightblue bold")
        self.assertEqual(_FakeStyle.captured["flag"], "ansired bold")

    def test_run_repl_reuses_prompt_toolkit_history_across_prompts(self) -> None:
        cli = PsykerCLI(self.runtime)

        class _FakeStyle:
            @staticmethod
            def from_dict(style_dict: dict[str, str]) -> str:
                return "style-object"

        history_ids: list[int] = []

        def _fake_prompt(*args, **kwargs):
            history_ids.append(id(kwargs["history"]))
            if len(history_ids) == 1:
                return "help --version"
            raise EOFError

        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("psyker.cli._pt_Style", new=_FakeStyle):
                    with patch("psyker.cli._pt_prompt", side_effect=_fake_prompt):
                        code = cli.run_repl()

        self.assertEqual(code, 0)
        self.assertGreaterEqual(len(history_ids), 2)
        self.assertEqual(len(set(history_ids)), 1)

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


class CLIv013Tests(unittest.TestCase):
    """Tests for v0.1.3 features: batch run, fs.mkdir via CLI, --script mode."""

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

    def _load_basic(self) -> None:
        self.cli.execute_line(f'load "{self.grammar / "valid" / "worker_basic.psyw"}"')
        self.cli.execute_line(f'load "{self.grammar / "valid" / "agent_basic.psya"}"')

    def _write_task(self, name: str, body: str, caps: list[str] | None = None) -> Path:
        """Write a .psy task file to temp dir and return path."""
        task_path = Path(self.temp.name) / f"{name}.psy"
        task_path.write_text(
            f"@access {{ agents: [alpha], workers: [w1] }}\ntask {name} {{\n  {body}\n}}\n",
            encoding="utf-8",
        )
        return task_path

    def test_run_multiple_tasks_in_order(self) -> None:
        self._load_basic()
        # Use fs.open for both tasks since w1 only allows fs.open / exec.ps
        input_file = self.sandbox.workspace / "input.txt"
        input_file.write_text("hi", encoding="utf-8")
        t1 = self._write_task("multi1", 'fs.open "input.txt";')
        t2_path = Path(self.temp.name) / "multi2.psy"
        t2_path.write_text(
            '@access { agents: [alpha], workers: [w1] }\ntask multi2 {\n  fs.open "input.txt";\n}\n',
            encoding="utf-8",
        )
        self.cli.execute_line(f'load "{t1}"')
        self.cli.execute_line(f'load "{t2_path}"')
        code = self.cli.execute_line("run alpha multi1 multi2")
        self.assertEqual(code, 0)
        out = self.out.getvalue()
        self.assertIn("task=multi1", out)
        self.assertIn("task=multi2", out)

    def test_run_batch_stops_on_first_failure(self) -> None:
        self._load_basic()
        t1 = self._write_task("fail_task", 'fs.open "missing_file.txt";')
        t2 = self._write_task("after_fail", 'fs.create "should_not_exist";')
        self.cli.execute_line(f'load "{t1}"')
        self.cli.execute_line(f'load "{t2}"')
        code = self.cli.execute_line("run alpha fail_task after_fail")
        self.assertNotEqual(code, 0)
        self.assertFalse((self.sandbox.workspace / "should_not_exist").exists())

    def test_run_requires_at_least_two_args(self) -> None:
        code = self.cli.execute_line("run alpha")
        self.assertEqual(code, 1)
        self.assertIn("Usage", self.err.getvalue())

    def test_batch_cli_command_gated_by_feature_flag(self) -> None:
        import os
        # Without flag, 'batch' command should not be registered
        self.assertNotIn("batch", self.cli.commands)
        # With flag, it should be present
        with patch.dict(os.environ, {"PSYKER_FEATURE_BATCH": "1"}):
            rt = RuntimeState(sandbox=self.sandbox)
            cli2 = PsykerCLI(rt, out=io.StringIO(), err=io.StringIO())
            self.assertIn("batch", cli2.commands)

    def test_batch_command_runs_steps(self) -> None:
        import os
        # Use fs.open since w1 only allows fs.open / exec.ps
        input_file = self.sandbox.workspace / "input.txt"
        input_file.write_text("batch-test", encoding="utf-8")
        t1 = Path(self.temp.name) / "bs1.psy"
        t1.write_text(
            '@access { agents: [alpha], workers: [w1] }\ntask bs1 {\n  fs.open "input.txt";\n}\n',
            encoding="utf-8",
        )
        batch_file = Path(self.temp.name) / "mybatch.psy"
        batch_file.write_text(
            '@access { agents: [alpha], workers: [w1] }\nbatch bp {\n  run bs1;\n}\n',
            encoding="utf-8",
        )
        with patch.dict(os.environ, {"PSYKER_FEATURE_BATCH": "1"}):
            rt = RuntimeState(sandbox=self.sandbox)
            rt.load_file(self.grammar / "valid" / "worker_basic.psyw")
            rt.load_file(self.grammar / "valid" / "agent_basic.psya")
            rt.load_file(t1)
            rt.load_file(batch_file)
            out2 = io.StringIO()
            err2 = io.StringIO()
            cli2 = PsykerCLI(rt, out=out2, err=err2)
            code = cli2.execute_line("batch alpha bp")
        self.assertEqual(code, 0)
        self.assertIn("bs1", out2.getvalue())

    def test_script_mode_loads_file_before_repl(self) -> None:
        from psyker.entry import run
        wpath = str(self.grammar / "valid" / "worker_basic.psyw")
        with patch("psyker.entry._parse_args") as mock_args:
            import types
            mock_args.return_value = types.SimpleNamespace(
                version=False, gui=False, verbose=False, check_updates=False,
                script=[wpath], run=[],
            )
            with patch("psyker.entry.create_default_cli") as mock_cli_factory:
                mock_cli = mock_cli_factory.return_value
                mock_cli.execute_line.return_value = 0
                mock_cli.run_repl.return_value = 0
                mock_cli._io = io.StringIO()
                run()
            mock_cli.execute_line.assert_any_call(f'load "{wpath}"')
            mock_cli.run_repl.assert_called_once()

    def test_run_flag_exits_without_repl(self) -> None:
        from psyker.entry import run
        wpath = str(self.grammar / "valid" / "worker_basic.psyw")
        with patch("psyker.entry._parse_args") as mock_args:
            import types
            mock_args.return_value = types.SimpleNamespace(
                version=False, gui=False, verbose=False, check_updates=False,
                script=[wpath], run=["myagent:mytask"],
            )
            with patch("psyker.entry.create_default_cli") as mock_cli_factory:
                mock_cli = mock_cli_factory.return_value
                mock_cli.execute_line.return_value = 0
                mock_cli._io = io.StringIO()
                run()
            mock_cli.run_repl.assert_not_called()
            mock_cli.execute_line.assert_any_call("run myagent mytask")


if __name__ == "__main__":
    unittest.main()
