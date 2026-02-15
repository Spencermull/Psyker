from __future__ import annotations

import unittest
from unittest.mock import patch

from psyker.update_check import check_for_update_notice, start_async_update_check


class UpdateCheckTests(unittest.TestCase):
    def test_check_for_update_notice_returns_message_when_newer(self) -> None:
        with patch("psyker.update_check.fetch_latest_version", return_value="0.1.1"):
            notice = check_for_update_notice("0.1.0")
        self.assertIsNotNone(notice)
        self.assertIn("v0.1.1", notice or "")

    def test_check_for_update_notice_returns_none_when_not_newer(self) -> None:
        with patch("psyker.update_check.fetch_latest_version", return_value="0.1.0"):
            notice = check_for_update_notice("0.1.0")
        self.assertIsNone(notice)

    def test_start_async_update_check_notifies_once(self) -> None:
        seen: list[str] = []

        with patch("psyker.update_check.check_for_update_notice", return_value="Update available: Psyker v0.1.1"):
            thread = start_async_update_check("0.1.0", seen.append)
            thread.join(timeout=1.0)

        self.assertEqual(seen, ["Update available: Psyker v0.1.1"])


if __name__ == "__main__":
    unittest.main()
