"""Tests for core doctor and editors safety."""

import tempfile
import unittest
from pathlib import Path

from agentflow.core import doctor_project, init_project
from agentflow.editors import apply_editors, save_editor_config, load_editor_config
from agentflow.templates import thin_entrypoint


class CoreTests(unittest.TestCase):
    def test_doctor_reports_missing_skeleton(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = doctor_project(directory)
            self.assertFalse(report["ok"])
            self.assertIn(".agentflow/AGENTS.md", report["missing"])

    def test_doctor_ok_after_init(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            init_project(root, home=home)
            report = doctor_project(root, home=home)
            self.assertTrue(report["ok"])

    def test_apply_editors_does_not_delete_user_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            cursor_dir = root / ".cursor" / "rules"
            cursor_dir.mkdir(parents=True)
            user_file = cursor_dir / "my-rules.mdc"
            user_file.write_text("custom", encoding="utf-8")

            entrypoint = root / ".cursor" / "rules" / "agentflow.mdc"
            entrypoint.write_text(thin_entrypoint("cursor"), encoding="utf-8")

            config = load_editor_config(home=home)
            save_editor_config([], config.get("custom", {}), home=home)
            result = apply_editors(root, home=home)

            self.assertIn(".cursor/rules/agentflow.mdc", result["removed"])
            self.assertTrue(user_file.exists())


if __name__ == "__main__":
    unittest.main()
