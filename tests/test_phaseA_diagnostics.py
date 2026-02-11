from __future__ import annotations

from pathlib import Path
import unittest

from psyker.errors import DialectError, SourceSpan, SyntaxError
from psyker_lsp.server import to_lsp_diagnostic


class PhaseADiagnosticTests(unittest.TestCase):
    def test_psyker_error_to_diagnostic_includes_hint_when_present(self) -> None:
        exc = DialectError(
            "Unsupported file extension '.txt'",
            SourceSpan(Path("sample.psy"), 2, 5),
            hint="Use .psy, .psya, or .psyw.",
        )
        message = exc.to_diagnostic()

        self.assertIn("error[DialectError]: Unsupported file extension '.txt'", message)
        self.assertIn("--> sample.psy:2:5", message)
        self.assertIn("hint: Use .psy, .psya, or .psyw.", message)

    def test_lsp_diagnostic_uses_full_message_with_path_fallback(self) -> None:
        exc = SyntaxError(
            "Expected ';'",
            SourceSpan(None, 4, 7),
            hint="Add ';' at the end of the statement.",
        )

        diagnostic = to_lsp_diagnostic(exc, Path("fallback.psy"))
        expected_message = SyntaxError(
            "Expected ';'",
            SourceSpan(Path("fallback.psy"), 4, 7),
            hint="Add ';' at the end of the statement.",
        ).to_diagnostic()

        self.assertEqual(diagnostic.message, expected_message)
        self.assertEqual(diagnostic.range.start.line, 3)
        self.assertEqual(diagnostic.range.start.character, 6)


if __name__ == "__main__":
    unittest.main()
