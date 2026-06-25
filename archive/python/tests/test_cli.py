"""CLI and REPL smoke tests."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(project_dir: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-m", "agentflow.cli", *args]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        command,
        cwd=project_dir,
        text=True,
        input=input_text,
        capture_output=True,
        check=False,
        env=env,
    )


class CliTests(unittest.TestCase):
    def test_cli_init_creates_skeleton(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(project_dir, "init", "--skeleton-only")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Initialized specification skeleton", result.stdout)
            self.assertTrue((project_dir / ".agentflow" / "AGENTS.md").is_file())
            self.assertFalse((project_dir / "AGENTS.md").is_file())

    def test_cli_check_after_init(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--skeleton-only")
            result = run_cli(project_dir, "check")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("AgentFlow check: OK", result.stdout)

    def test_cli_check_before_init_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_cli(Path(directory), "check")
            self.assertEqual(result.returncode, 1)
            self.assertIn("missing files", result.stdout)

    def test_cli_version(self) -> None:
        from agentflow import __version__

        with tempfile.TemporaryDirectory() as directory:
            result = run_cli(Path(directory), "--version")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(__version__, result.stdout + result.stderr)

    def test_cli_tools_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_cli(Path(directory), "tools", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"tools"', result.stdout)

    def test_cli_instructions_requires_init(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_cli(Path(directory), "instructions")
            self.assertEqual(result.returncode, 1)
            self.assertIn("not initialized", result.stdout.lower())

    def test_repl_init_and_quit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_cli(Path(directory), input_text="/init\n/quit\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Init complete", result.stdout)
            # Non-TTY stdin: picker skips editors, skeleton only
            self.assertFalse((Path(directory) / "AGENTS.md").exists())


if __name__ == "__main__":
    unittest.main()
