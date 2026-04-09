from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from psyker.errors import DialectError, SyntaxError
from psyker.model import AgentDocument, TaskDocument, WorkerDocument
from psyker.parser import parse_path


class ParserCorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("Grammar Context")

    def test_valid_files_parse_to_correct_ast_type(self) -> None:
        expected = {
            ".psy": TaskDocument,
            ".psya": AgentDocument,
            ".psyw": WorkerDocument,
        }
        for path in sorted((self.root / "valid").iterdir()):
            with self.subTest(path=path):
                ast = parse_path(path)
                self.assertIsInstance(ast, expected[path.suffix.lower()])

    def test_invalid_parse_time_fixtures_raise(self) -> None:
        expectations = {
            "task_missing_semicolon.psy": SyntaxError,
            "task_with_worker_def.psy": DialectError,
            "worker_invalid_capability.psyw": SyntaxError,
        }
        for filename, error_type in expectations.items():
            path = self.root / "invalid" / filename
            with self.subTest(path=path):
                with self.assertRaises(error_type):
                    parse_path(path)

    def test_runtime_invalid_files_still_parse(self) -> None:
        for filename in ["task_no_access_header.psy", "task_path_traversal.psy", "agent_missing_access_header.psya"]:
            path = self.root / "invalid" / filename
            with self.subTest(path=path):
                ast = parse_path(path)
                self.assertIsNotNone(ast)

    def test_extended_task_operations_parse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "extended_ops.psy"
            path.write_text(
                (
                    '@access { agents: [alpha], workers: [w1] }\n'
                    "task ext {\n"
                    '  fs.write "a.txt" "x";\n'
                    '  fs.update "a.txt" "y";\n'
                    '  fs.append "a.txt" "z";\n'
                    '  fs.delete "a.txt";\n'
                    '  fs.list ".";\n'
                    "}\n"
                ),
                encoding="utf-8",
            )
            ast = parse_path(path)
            self.assertIsInstance(ast, TaskDocument)
            self.assertEqual(len(ast.tasks[0].statements), 5)


if __name__ == "__main__":
    unittest.main()
