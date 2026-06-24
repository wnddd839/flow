"""Tests for flow init / init_project."""

import tempfile
import unittest
from pathlib import Path

from agentflow.core import BASE_REQUIRED_FILES, init_project
from agentflow.editors import get_enabled_editors
from agentflow import templates


class InitTests(unittest.TestCase):
    def test_init_creates_skeleton_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            result = init_project(root, home=home)

            for relative in BASE_REQUIRED_FILES:
                self.assertTrue((root / relative).exists(), relative)

            self.assertIn("AGENTS.md", result["created"])
            self.assertIn(".agentflow/AGENTS.md", result["created"])

    def test_init_creates_all_editor_entrypoints_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            init_project(root, home=home)

            for name in templates.DEFAULT_PLATFORMS:
                spec = next(s for s in get_enabled_editors(home=home) if s.name == name)
                self.assertTrue((root / spec.entrypoint).exists(), spec.entrypoint)

    def test_agents_md_contains_maintenance_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_project(root, home=Path(directory) / "home")
            content = (root / ".agentflow" / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("文档维护契约", content)
            self.assertIn("每条信息**只出现在一个文档里**", content)

    def test_init_is_idempotent_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = init_project(root, home=root / "home")
            second = init_project(root, home=root / "home")
            self.assertGreater(len(first["created"]), 0)
            self.assertEqual(len(second["created"]), 0)

    def test_init_with_editors_subset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            init_project(root, editors=["qoder", "cursor"], home=home)
            enabled = {spec.name for spec in get_enabled_editors(home=home)}
            self.assertEqual(enabled, {"qoder", "cursor"})
            self.assertTrue((root / ".qoder/skills/agentflow/SKILL.md").exists())
            self.assertTrue((root / ".cursor/rules/agentflow.mdc").exists())


if __name__ == "__main__":
    unittest.main()
