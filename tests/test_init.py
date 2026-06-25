"""Tests for flow init / init_project."""

import tempfile
import unittest
from pathlib import Path

from agentflow.core import BASE_REQUIRED_FILES, init_project
from agentflow.editors import get_enabled_editors, normalize_editor_names


class InitTests(unittest.TestCase):
    def test_init_creates_skeleton_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            result = init_project(root, home=home)

            for relative in BASE_REQUIRED_FILES:
                self.assertTrue((root / relative).exists(), relative)

            self.assertIn(".agentflow/AGENTS.md", result["created"])
            self.assertNotIn("AGENTS.md", result["created"])

    def test_init_skeleton_only_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            init_project(root, home=home)

            self.assertFalse((root / "AGENTS.md").exists())
            self.assertFalse((root / "CLAUDE.md").exists())
            enabled = get_enabled_editors(home=home)
            self.assertEqual(enabled, [])

    def test_init_creates_selected_editor_entrypoints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            init_project(root, editors=["qoder", "cursor"], home=home)

            enabled = {spec.name for spec in get_enabled_editors(home=home)}
            self.assertEqual(enabled, {"qoder", "cursor"})
            self.assertTrue((root / ".qoder/skills/agentflow/SKILL.md").exists())
            self.assertTrue((root / ".cursor/rules/agentflow.mdc").exists())
            self.assertFalse((root / "AGENTS.md").exists())

    def test_agents_md_contains_maintenance_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_project(root, home=Path(directory) / "home")
            content = (root / ".agentflow" / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("文档维护契约", content)
            self.assertIn("每条信息只出现在一个文档里", content)

    def test_init_is_idempotent_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = init_project(root, home=root / "home")
            second = init_project(root, home=root / "home")
            self.assertGreater(len(first["created"]), 0)
            self.assertEqual(len(second["created"]), 0)

    def test_normalize_editor_names_rejects_unknown(self) -> None:
        with self.assertRaises(ValueError):
            normalize_editor_names(["not-a-real-editor"])


class InitUiTests(unittest.TestCase):
    def test_pick_editors_non_tty_returns_empty(self) -> None:
        from agentflow.init_ui import pick_editors

        self.assertEqual(pick_editors(is_tty=False), [])


class InitCliEditorTests(unittest.TestCase):
    def test_cli_init_cursor_only(self) -> None:
        import os
        import subprocess
        import sys

        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(root)
            result = subprocess.run(
                [sys.executable, "-m", "agentflow.cli", "init", "cursor"],
                cwd=project_dir,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Editors: cursor", result.stdout)
            self.assertTrue((project_dir / ".cursor/rules/agentflow.mdc").is_file())
            self.assertFalse((project_dir / "AGENTS.md").is_file())

    def test_cli_init_skeleton_only_flag(self) -> None:
        import os
        import subprocess
        import sys

        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(root)
            result = subprocess.run(
                [sys.executable, "-m", "agentflow.cli", "init", "--skeleton-only"],
                cwd=project_dir,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("skeleton only", result.stdout)
            self.assertTrue((project_dir / ".agentflow/AGENTS.md").is_file())
            self.assertFalse((project_dir / "CLAUDE.md").is_file())


if __name__ == "__main__":
    unittest.main()
