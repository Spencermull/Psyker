from __future__ import annotations

import unittest
from unittest.mock import patch

from psyker import __main__


class ExeEntryTests(unittest.TestCase):
    def test_main_delegates_to_entry_run(self) -> None:
        with patch("psyker.__main__.run", return_value=7) as mocked_run:
            result = __main__.main()
        self.assertEqual(result, 7)
        mocked_run.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
