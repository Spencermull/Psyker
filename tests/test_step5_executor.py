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

    def test_fs_write_update_append_delete_and_list(self) -> None:
        worker_path = Path(self.temp.name) / "worker_ext.psyw"
        worker_path.write_text(
            (
                "worker w_ext {\n"
                f'  sandbox "{self.sandbox.root}";\n'
                f'  cwd "{self.sandbox.workspace}";\n'
                "  allow fs.write;\n"
                "  allow fs.update;\n"
                "  allow fs.append;\n"
                "  allow fs.delete;\n"
                "  allow fs.list;\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        agent_path = Path(self.temp.name) / "agent_ext.psya"
        agent_path.write_text("agent alpha_ext {\n  use worker w_ext count = 1;\n}\n", encoding="utf-8")

        write_task = Path(self.temp.name) / "write_ext.psy"
        write_task.write_text(
            (
                "@access { agents: [alpha_ext], workers: [w_ext] }\n"
                "task write_ext {\n"
                '  fs.write "notes.txt" "alpha";\n'
                '  fs.append "notes.txt" "-beta";\n'
                '  fs.update "notes.txt" "gamma";\n'
                "}\n"
            ),
            encoding="utf-8",
        )

        list_task = Path(self.temp.name) / "list_ext.psy"
        list_task.write_text(
            (
                "@access { agents: [alpha_ext], workers: [w_ext] }\n"
                "task list_ext {\n"
                '  fs.list ".";\n'
                "}\n"
            ),
            encoding="utf-8",
        )

        delete_task = Path(self.temp.name) / "delete_ext.psy"
        delete_task.write_text(
            (
                "@access { agents: [alpha_ext], workers: [w_ext] }\n"
                "task delete_ext {\n"
                '  fs.delete "notes.txt";\n'
                "}\n"
            ),
            encoding="utf-8",
        )

        self.runtime.load_file(worker_path)
        self.runtime.load_file(agent_path)
        self.runtime.load_file(write_task)
        self.runtime.load_file(list_task)
        self.runtime.load_file(delete_task)

        self.runtime.run_task("alpha_ext", "write_ext")
        target = self.sandbox.resolve_in_workspace("notes.txt")
        self.assertEqual(target.read_text(encoding="utf-8"), "gamma")

        result = self.runtime.run_task("alpha_ext", "list_ext")
        self.assertIn("notes.txt", result.stdout)

        self.runtime.run_task("alpha_ext", "delete_ext")
        self.assertFalse(target.exists())

    def _make_worker_and_agent(self, caps: list[str], worker_name: str = "w_ext", agent_name: str = "a_ext") -> tuple[Path, Path]:
        worker_path = Path(self.temp.name) / f"{worker_name}.psyw"
        caps_text = "".join(f"  allow {c};\n" for c in caps)
        worker_path.write_text(
            f'worker {worker_name} {{\n  sandbox "{self.sandbox.root}";\n  cwd "{self.sandbox.workspace}";\n{caps_text}}}\n',
            encoding="utf-8",
        )
        agent_path = Path(self.temp.name) / f"{agent_name}.psya"
        agent_path.write_text(f"agent {agent_name} {{\n  use worker {worker_name} count = 1;\n}}\n", encoding="utf-8")
        self.runtime.load_file(worker_path)
        self.runtime.load_file(agent_path)
        return worker_path, agent_path

    def test_fs_mkdir_creates_directory(self) -> None:
        self._make_worker_and_agent(["fs.mkdir"], "w_mkdir", "a_mkdir")
        task_path = Path(self.temp.name) / "mkdir_task.psy"
        task_path.write_text(
            '@access { agents: [a_mkdir], workers: [w_mkdir] }\ntask do_mkdir {\n  fs.mkdir "newdir";\n}\n',
            encoding="utf-8",
        )
        self.runtime.load_file(task_path)
        self.runtime.run_task("a_mkdir", "do_mkdir")
        self.assertTrue((self.sandbox.workspace / "newdir").is_dir())

    def test_fs_mkdir_is_idempotent(self) -> None:
        self._make_worker_and_agent(["fs.mkdir"], "w_mkdir2", "a_mkdir2")
        task_path = Path(self.temp.name) / "mkdir2_task.psy"
        task_path.write_text(
            '@access { agents: [a_mkdir2], workers: [w_mkdir2] }\ntask do_mkdir2 {\n  fs.mkdir "idempotent";\n}\n',
            encoding="utf-8",
        )
        self.runtime.load_file(task_path)
        self.runtime.run_task("a_mkdir2", "do_mkdir2")
        self.runtime.run_task("a_mkdir2", "do_mkdir2")  # second call must not raise
        self.assertTrue((self.sandbox.workspace / "idempotent").is_dir())

    def test_path_var_workspace_expands(self) -> None:
        self._make_worker_and_agent(["fs.mkdir"], "w_pv", "a_pv")
        task_path = Path(self.temp.name) / "pv_task.psy"
        task_path.write_text(
            '@access { agents: [a_pv], workers: [w_pv] }\ntask do_pv {\n  fs.mkdir $WORKSPACE/pvdir;\n}\n',
            encoding="utf-8",
        )
        self.runtime.load_file(task_path)
        self.runtime.run_task("a_pv", "do_pv")
        self.assertTrue((self.sandbox.workspace / "pvdir").is_dir())

    def test_path_var_sandbox_expands(self) -> None:
        self._make_worker_and_agent(["fs.list"], "w_pvs", "a_pvs")
        task_path = Path(self.temp.name) / "pvs_task.psy"
        task_path.write_text(
            '@access { agents: [a_pvs], workers: [w_pvs] }\ntask do_pvs {\n  fs.list $SANDBOX;\n}\n',
            encoding="utf-8",
        )
        self.runtime.load_file(task_path)
        result = self.runtime.run_task("a_pvs", "do_pvs")
        self.assertEqual(result.status_code, 0)

    def test_path_var_traversal_still_blocked(self) -> None:
        self._make_worker_and_agent(["fs.mkdir"], "w_pvt", "a_pvt")
        task_path = Path(self.temp.name) / "pvt_task.psy"
        task_path.write_text(
            '@access { agents: [a_pvt], workers: [w_pvt] }\ntask do_pvt {\n  fs.mkdir $WORKSPACE/../../escape;\n}\n',
            encoding="utf-8",
        )
        self.runtime.load_file(task_path)
        from psyker.errors import SandboxError
        with self.assertRaises(SandboxError):
            self.runtime.run_task("a_pvt", "do_pvt")

    def test_run_batch_executes_steps_in_order(self) -> None:
        import os
        self._make_worker_and_agent(["fs.mkdir", "fs.write"], "w_batch", "a_batch")
        task1 = Path(self.temp.name) / "bt1.psy"
        task1.write_text(
            '@access { agents: [a_batch], workers: [w_batch] }\ntask step1 {\n  fs.mkdir "batch_out";\n}\n',
            encoding="utf-8",
        )
        task2 = Path(self.temp.name) / "bt2.psy"
        task2.write_text(
            '@access { agents: [a_batch], workers: [w_batch] }\ntask step2 {\n  fs.write "batch_out/done.txt" "ok";\n}\n',
            encoding="utf-8",
        )
        batch_file = Path(self.temp.name) / "mybatch.psy"
        batch_file.write_text(
            '@access { agents: [a_batch], workers: [w_batch] }\nbatch pipeline {\n  run step1;\n  run step2 after step1;\n}\n',
            encoding="utf-8",
        )
        self.runtime.load_file(task1)
        self.runtime.load_file(task2)
        with patch.dict(os.environ, {"PSYKER_FEATURE_BATCH": "1"}):
            self.runtime.load_file(batch_file)
            results = self.runtime.run_batch("a_batch", "pipeline")
        self.assertEqual(len(results), 2)
        self.assertTrue((self.sandbox.workspace / "batch_out" / "done.txt").exists())

    def test_run_batch_unknown_task_raises(self) -> None:
        import os
        self._make_worker_and_agent(["fs.mkdir"], "w_bu", "a_bu")
        batch_file = Path(self.temp.name) / "bad_batch.psy"
        batch_file.write_text(
            '@access { agents: [a_bu], workers: [w_bu] }\nbatch bad {\n  run nonexistent;\n}\n',
            encoding="utf-8",
        )
        from psyker.errors import ReferenceError
        with patch.dict(os.environ, {"PSYKER_FEATURE_BATCH": "1"}):
            self.runtime.load_file(batch_file)
            with self.assertRaises(ReferenceError):
                self.runtime.run_batch("a_bu", "bad")

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
