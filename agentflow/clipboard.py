"""Best-effort clipboard helpers without third-party dependencies."""

from __future__ import annotations

import shutil
import subprocess
import sys


def copy_to_clipboard(text: str) -> bool:
    """Copy ``text`` to the system clipboard when a backend is available.

    Returns ``True`` on success and ``False`` when the text is empty, no
    backend exists, or the platform call fails. Never raises for expected
    failures.
    """

    if not text or not text.strip():
        return False

    if sys.platform == "win32":
        return _copy_windows(text)
    if sys.platform == "darwin":
        return _copy_macos(text)
    return _copy_linux(text)


def print_clipboard_notice(copied: bool, *, stream=None) -> None:
    """Emit a short notice when clipboard copy succeeds (stderr by default)."""

    if copied:
        target = stream if stream is not None else sys.stderr
        print("Copied to clipboard.", file=target)


def _copy_windows(text: str) -> bool:
    try:
        process = subprocess.Popen(
            ["clip"],
            stdin=subprocess.PIPE,
            close_fds=True,
        )
        process.communicate(input=text.encode("utf-16le"), timeout=5)
        return process.returncode == 0
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False


def _copy_macos(text: str) -> bool:
    return _run_input_command(["pbcopy"], text)


def _copy_linux(text: str) -> bool:
    if shutil.which("wl-copy"):
        return _run_bytes_command(["wl-copy"], text.encode("utf-8"))
    if shutil.which("xclip"):
        return _run_bytes_command(
            ["xclip", "-selection", "clipboard"],
            text.encode("utf-8"),
        )
    if shutil.which("xsel"):
        return _run_bytes_command(
            ["xsel", "--clipboard", "--input"],
            text.encode("utf-8"),
        )
    return False


def _run_input_command(command: list[str], text: str) -> bool:
    try:
        result = subprocess.run(
            command,
            input=text,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _run_bytes_command(command: list[str], payload: bytes) -> bool:
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        process.communicate(input=payload, timeout=5)
        return process.returncode == 0
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False
