from __future__ import annotations

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from psyker import __main__
from psyker.entry import _ensure_launch_working_directory, run


class ExeEntryTests(unittest.TestCase):
    def test_main_delegates_to_entry_run(self) -> None:
        with patch("psyker.__main__.run", return_value=7) as mocked_run:
            result = __main__.main()
        self.assertEqual(result, 7)
        mocked_run.assert_called_once_with()

    def test_ensure_launch_working_directory_preserves_existing_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            sandbox = SimpleNamespace(workspace=Path(temp) / "workspace")
            with patch("psyker.entry.Path.cwd", return_value=Path(temp)):
                with patch("psyker.entry.os.chdir") as mocked_chdir:
                    _ensure_launch_working_directory(sandbox)
            mocked_chdir.assert_not_called()

    def test_ensure_launch_working_directory_falls_back_to_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            sandbox = SimpleNamespace(workspace=workspace)
            with patch("psyker.entry.Path.cwd", side_effect=OSError("cwd unavailable")):
                with patch("psyker.entry.os.chdir") as mocked_chdir:
                    _ensure_launch_working_directory(sandbox)
            mocked_chdir.assert_called_once_with(workspace)

    def test_run_uses_default_cli_and_returns_repl_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            fake_cli = SimpleNamespace(
                runtime=SimpleNamespace(sandbox=SimpleNamespace(workspace=workspace)),
                run_repl=lambda: 5,
            )
            with patch("psyker.entry.create_default_cli", return_value=fake_cli) as mocked_create:
                with patch("psyker.entry.Path.cwd", return_value=Path(temp)):
                    result = run()
            self.assertEqual(result, 5)
            mocked_create.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
