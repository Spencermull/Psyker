from __future__ import annotations

import unittest
from pathlib import Path

from lsprotocol.types import Position

from psyker.model import WorkerDef, WorkerDocument
from psyker_lsp.server import (
    OpenDocument,
    completion_context_for_position,
    definition_target_kind_for_position,
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
        self.assertEqual(
            hover_text_for_word("fs.open"),
            "Read a file from sandbox scope (requires worker allow fs.open).",
        )
        self.assertEqual(
            hover_text_for_word("@access"),
            "Access gate for a task. Limits which agents/workers can run the task.",
        )
        self.assertIsNone(hover_text_for_word("not_a_keyword"))

    def test_completion_context_for_access_and_worker_usage(self) -> None:
        psy_text = (
            "@access { agents: [alp], workers: [w1] }\n"
            "task hello {\n"
            '  fs.open "sandbox/input.txt";\n'
            "}\n"
        )
        self.assertEqual(
            completion_context_for_position(psy_text, Position(line=0, character=21), ".psy"),
            "access_agents",
        )
        self.assertEqual(
            completion_context_for_position(psy_text, Position(line=0, character=35), ".psy"),
            "access_workers",
        )
        self.assertEqual(
            completion_context_for_position("task hel", Position(line=0, character=8), ".psy"),
            "task_name",
        )
        self.assertEqual(
            completion_context_for_position("use worker w", Position(line=0, character=12), ".psya"),
            "use_worker",
        )
        self.assertEqual(
            completion_context_for_position("allow fs.", Position(line=0, character=9), ".psyw"),
            "allow_capability",
        )

    def test_definition_target_kind_for_position(self) -> None:
        self.assertEqual(
            definition_target_kind_for_position("use worker w1 count = 1;", Position(line=0, character=11), ".psya"),
            "worker",
        )
        self.assertEqual(
            definition_target_kind_for_position(
                "@access { agents: [alpha], workers: [w1] }", Position(line=0, character=19), ".psy"
            ),
            "agent",
        )
        self.assertEqual(
            definition_target_kind_for_position(
                "@access { agents: [alpha], workers: [w1] }", Position(line=0, character=37), ".psy"
            ),
            "worker",
        )
        self.assertIsNone(
            definition_target_kind_for_position("task hello {", Position(line=0, character=2), ".psy")
        )


if __name__ == "__main__":
    unittest.main()
