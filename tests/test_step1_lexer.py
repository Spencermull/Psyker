from __future__ import annotations

from pathlib import Path
import unittest

from psyker.lexer import tokenize_file


class LexerCorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("Grammar Context")

    def test_tokenizes_all_corpus_files(self) -> None:
        files = sorted(self.root.rglob("*.psy*"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(path=path):
                tokens = tokenize_file(path)
                self.assertGreater(len(tokens), 1)
                self.assertEqual(tokens[-1].kind, "EOF")

    def test_task_file_contains_expected_tokens(self) -> None:
        path = self.root / "valid" / "task_basic.psy"
        tokens = tokenize_file(path)
        kinds = [token.kind for token in tokens]
        values = [token.value for token in tokens]
        self.assertIn("AT_ACCESS", kinds)
        self.assertIn("task", values)
        self.assertIn("fs.open", values)
        self.assertIn("exec.ps", values)


if __name__ == "__main__":
    unittest.main()
