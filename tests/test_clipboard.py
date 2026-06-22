"""Tests for clipboard helpers."""

import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

from agentflow.clipboard import copy_to_clipboard, print_clipboard_notice


class ClipboardTests(unittest.TestCase):
    def test_empty_text_returns_false(self) -> None:
        self.assertFalse(copy_to_clipboard(""))
        self.assertFalse(copy_to_clipboard("   "))

    @patch("agentflow.clipboard.sys.platform", "win32")
    @patch("agentflow.clipboard.subprocess.Popen")
    def test_windows_uses_clip_with_utf16le(self, popen_mock: MagicMock) -> None:
        process = MagicMock()
        process.returncode = 0
        popen_mock.return_value = process

        self.assertTrue(copy_to_clipboard("hello"))

        popen_mock.assert_called_once_with(
            ["clip"],
            stdin=subprocess.PIPE,
            close_fds=True,
        )
        process.communicate.assert_called_once_with(
            input="hello".encode("utf-16le"),
            timeout=5,
        )

    @patch("agentflow.clipboard.sys.platform", "darwin")
    @patch("agentflow.clipboard._run_input_command", return_value=True)
    def test_macos_uses_pbcopy(self, run_mock: MagicMock) -> None:
        self.assertTrue(copy_to_clipboard("handoff text"))
        run_mock.assert_called_once_with(["pbcopy"], "handoff text")

    @patch("agentflow.clipboard.sys.platform", "linux")
    @patch("agentflow.clipboard.shutil.which")
    @patch("agentflow.clipboard._run_bytes_command", return_value=True)
    def test_linux_prefers_wl_copy(
        self,
        run_bytes_mock: MagicMock,
        which_mock: MagicMock,
    ) -> None:
        which_mock.side_effect = lambda name: name == "wl-copy"

        self.assertTrue(copy_to_clipboard("context"))

        run_bytes_mock.assert_called_once_with(
            ["wl-copy"],
            "context".encode("utf-8"),
        )

    @patch("agentflow.clipboard.sys.platform", "linux")
    @patch("agentflow.clipboard.shutil.which", return_value=None)
    def test_linux_without_backend_returns_false(self, _which_mock: MagicMock) -> None:
        self.assertFalse(copy_to_clipboard("no clipboard tool"))

    def test_print_clipboard_notice_only_on_success(self) -> None:
        import io

        stream = io.StringIO()
        print_clipboard_notice(False, stream=stream)
        self.assertEqual(stream.getvalue(), "")

        print_clipboard_notice(True, stream=stream)
        self.assertIn("Copied to clipboard.", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
