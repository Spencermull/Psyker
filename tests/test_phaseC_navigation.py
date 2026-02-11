from __future__ import annotations

from pathlib import Path
import unittest

from lsprotocol.types import (
    DefinitionParams,
    DocumentSymbolParams,
    Position,
    TextDocumentIdentifier,
)

from psyker_lsp.server import (
    OpenDocument,
    PsykerLanguageServer,
    SymbolRecord,
    WorkspaceIndex,
    definition,
    document_symbol,
)


class PhaseCNavigationTests(unittest.TestCase):
    def test_definition_jumps_to_worker_from_agent_reference(self) -> None:
        ls = PsykerLanguageServer()
        uri = "file:///agent.psya"
        ls.open_documents[uri] = OpenDocument(
            path=Path("agent.psya"),
            text="agent alpha {\n  use worker w1 count = 1;\n}\n",
            ast=None,
        )
        ls._index = WorkspaceIndex(
            tasks={},
            agents={},
            workers={
                "w1": [
                    SymbolRecord(
                        name="w1",
                        kind="worker",
                        path=Path("defs/worker_w1.psyw").resolve(),
                        line=1,
                        column=8,
                        summary="worker definition",
                    )
                ]
            },
        )
        ls._index_dirty = False

        result = definition(
            ls,
            DefinitionParams(
                text_document=TextDocumentIdentifier(uri=uri),
                position=Position(line=1, character=13),
            ),
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].uri.endswith("/defs/worker_w1.psyw"))

    def test_definition_jumps_to_agent_from_access_reference(self) -> None:
        ls = PsykerLanguageServer()
        uri = "file:///task.psy"
        ls.open_documents[uri] = OpenDocument(
            path=Path("task.psy"),
            text='@access { agents: [alpha], workers: [w1] }\ntask hello { fs.open "x"; }\n',
            ast=None,
        )
        ls._index = WorkspaceIndex(
            tasks={},
            agents={
                "alpha": [
                    SymbolRecord(
                        name="alpha",
                        kind="agent",
                        path=Path("defs/alpha.psya").resolve(),
                        line=1,
                        column=7,
                        summary="agent definition",
                    )
                ]
            },
            workers={},
        )
        ls._index_dirty = False

        result = definition(
            ls,
            DefinitionParams(
                text_document=TextDocumentIdentifier(uri=uri),
                position=Position(line=0, character=20),
            ),
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].uri.endswith("/defs/alpha.psya"))

    def test_document_symbols_include_task_agent_and_worker_names(self) -> None:
        task_ls = PsykerLanguageServer()
        task_uri = "file:///task.psy"
        task_ls.open_documents[task_uri] = OpenDocument(
            path=Path("task.psy"),
            text='task t1 {\n  fs.open "a";\n}\n\ntask t2 {\n  fs.create "b";\n}\n',
            ast=None,
        )
        task_symbols = document_symbol(
            task_ls,
            DocumentSymbolParams(text_document=TextDocumentIdentifier(uri=task_uri)),
        )
        self.assertEqual([symbol.name for symbol in task_symbols], ["t1", "t2"])

        agent_ls = PsykerLanguageServer()
        agent_uri = "file:///agent.psya"
        agent_ls.open_documents[agent_uri] = OpenDocument(
            path=Path("agent.psya"),
            text="agent alpha {\n  use worker w1 count = 1;\n}\n",
            ast=None,
        )
        agent_symbols = document_symbol(
            agent_ls,
            DocumentSymbolParams(text_document=TextDocumentIdentifier(uri=agent_uri)),
        )
        self.assertEqual([symbol.name for symbol in agent_symbols], ["alpha"])

        worker_ls = PsykerLanguageServer()
        worker_uri = "file:///worker.psyw"
        worker_ls.open_documents[worker_uri] = OpenDocument(
            path=Path("worker.psyw"),
            text="worker w1 {\n  allow fs.open;\n}\n",
            ast=None,
        )
        worker_symbols = document_symbol(
            worker_ls,
            DocumentSymbolParams(text_document=TextDocumentIdentifier(uri=worker_uri)),
        )
        self.assertEqual([symbol.name for symbol in worker_symbols], ["w1"])


if __name__ == "__main__":
    unittest.main()
