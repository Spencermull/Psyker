from __future__ import annotations

import unittest
from pathlib import Path

from psyker.model import WorkerDef, WorkerDocument
from psyker_lsp.server import (
    OpenDocument,
    hover_text_for_word,
    keywords_for_suffix,
    worker_names_from_open_docs,
)


class PhaseBLspFeatureTests(unittest.TestCase):
    def test_keywords_for_suffix(self) -> None:
        self.assertEqual(
            keywords_for_suffix(".psy"),
            ["task", "@access", "agents", "workers", "fs.open", "fs.create", "exec.ps", "exec.cmd"],
        )
        self.assertEqual(
            keywords_for_suffix(".psya"),
            ["agent", "use", "worker", "count"],
        )
        self.assertEqual(
            keywords_for_suffix(".psyw"),
            ["worker", "allow", "sandbox", "cwd", "fs.open", "fs.create", "exec.ps", "exec.cmd"],
        )
        self.assertEqual(keywords_for_suffix(".txt"), [])

    def test_worker_names_from_open_docs(self) -> None:
        worker_alpha = WorkerDocument(
            worker=WorkerDef(
                name="w_alpha",
                sandbox=None,
                cwd=None,
                allows=(),
                source_path=None,
            )
        )
        worker_beta = WorkerDocument(
            worker=WorkerDef(
                name="w_beta",
                sandbox=None,
                cwd=None,
                allows=(),
                source_path=None,
            )
        )
        docs = {
            "file:///alpha.psyw": OpenDocument(path=Path("alpha.psyw"), ast=worker_alpha),
            "file:///beta.psyw": OpenDocument(path=Path("beta.psyw"), ast=worker_beta),
            "file:///dup.psyw": OpenDocument(path=Path("dup.psyw"), ast=worker_alpha),
            "file:///other.psya": OpenDocument(path=Path("other.psya"), ast=None),
        }
        self.assertEqual(worker_names_from_open_docs(docs), ["w_alpha", "w_beta"])

    def test_hover_text_for_word(self) -> None:
        self.assertEqual(hover_text_for_word("fs.open"), "Read a file (sandbox-restricted).")
        self.assertEqual(
            hover_text_for_word("@access"),
            "Restrict which agents and workers may run a task.",
        )
        self.assertIsNone(hover_text_for_word("not_a_keyword"))


if __name__ == "__main__":
    unittest.main()
