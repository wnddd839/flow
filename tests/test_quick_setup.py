"""Tests for the one-shot interactive setup flow."""

import tempfile
import unittest
from pathlib import Path

from agentflow.editors import get_enabled_editors, load_editor_config
from agentflow.quick_setup import run_quick_setup


class QuickSetupTests(unittest.TestCase):
    def _picker_returning(self, value):
        def _picker(defaults):
            # Record the defaults so a test can assert them.
            _picker.last_defaults = list(defaults)
            return value
        return _picker

    def test_persists_selection_and_initializes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = Path(directory) / "home"

            result = run_quick_setup(
                root,
                project_name="Demo",
                home=home,
                picker=self._picker_returning(["qoder", "cursor"]),
            )

            self.assertFalse(result["cancelled"])
            self.assertEqual(result["editors"], ["qoder", "cursor"])

            # Selection persisted to the user config.
            enabled = [spec.name for spec in get_enabled_editors(home=home)]
            self.assertEqual(enabled, ["qoder", "cursor"])

            # init_project ran and created the base skeleton + agent entrypoints.
            created = result["init"]["created"]
            self.assertIn("AGENTS.md", created)
            self.assertIn(".agentflow/constitution.md", created)
            self.assertIn(".qoder/skills/agentflow/SKILL.md", created)
            self.assertIn(".cursor/skills/agentflow/SKILL.md", created)

    def test_defaults_reflect_current_enabled_editors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = Path(directory) / "home"

            picker = self._picker_returning(["codex"])
            run_quick_setup(
                root,
                home=home,
                picker=self._picker_returning(["kiro"]),
            )
            # Now kiro is enabled; a second setup should offer it as default.
            run_quick_setup(
                root,
                home=home,
                picker=picker,
            )
            self.assertEqual(picker.last_defaults, ["kiro"])

    def test_cancel_does_not_touch_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = Path(directory) / "home"

            result = run_quick_setup(
                root,
                home=home,
                picker=self._picker_returning(None),
            )

            self.assertTrue(result["cancelled"])
            self.assertNotIn("init", result)
            # No agentflow skeleton and no editors config written.
            self.assertFalse((root / ".agentflow").exists())
            self.assertEqual(load_editor_config(home=home)["enabled"], [])

    def test_empty_selection_is_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = Path(directory) / "home"

            result = run_quick_setup(
                root,
                home=home,
                picker=self._picker_returning([]),
            )

            self.assertTrue(result["cancelled"])
            self.assertTrue(result["empty"])
            self.assertFalse((root / ".agentflow").exists())

    def test_unknown_names_are_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = Path(directory) / "home"

            result = run_quick_setup(
                root,
                home=home,
                picker=self._picker_returning(["qoder", "not-a-real-agent", "QODER"]),
            )

            # Deduped + validated against the catalog; only "qoder" survives.
            self.assertFalse(result["cancelled"])
            self.assertEqual(result["editors"], ["qoder"])


if __name__ == "__main__":
    unittest.main()
