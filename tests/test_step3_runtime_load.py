from __future__ import annotations

from pathlib import Path
import unittest

from psyker.errors import DialectError, ReferenceError, SyntaxError
from psyker.runtime import RuntimeState


class RuntimeLoadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("Grammar Context")
        self.runtime = RuntimeState()

    def test_valid_load_sequence_populates_registries(self) -> None:
        self.runtime.load_file(self.root / "valid" / "worker_basic.psyw")
        self.runtime.load_file(self.root / "valid" / "agent_basic.psya")
        self.runtime.load_file(self.root / "valid" / "task_basic.psy")

        self.assertIn("w1", self.runtime.workers)
        self.assertIn("alpha", self.runtime.agents)
        self.assertIn("hello", self.runtime.tasks)

    def test_load_failure_does_not_mutate_registries(self) -> None:
        self.runtime.load_file(self.root / "valid" / "worker_basic.psyw")
        before = (dict(self.runtime.workers), dict(self.runtime.agents), dict(self.runtime.tasks))
        with self.assertRaises(ReferenceError):
            self.runtime.load_file(self.root / "valid" / "agent_two_workers.psya")
        after = (dict(self.runtime.workers), dict(self.runtime.agents), dict(self.runtime.tasks))
        self.assertEqual(before, after)

    def test_invalid_parse_fixtures_fail_load(self) -> None:
        fixtures = {
            "task_missing_semicolon.psy": SyntaxError,
            "task_with_worker_def.psy": DialectError,
            "worker_invalid_capability.psyw": SyntaxError,
        }
        for filename, error_type in fixtures.items():
            with self.subTest(filename=filename):
                with self.assertRaises(error_type):
                    self.runtime.load_file(self.root / "invalid" / filename)


if __name__ == "__main__":
    unittest.main()
