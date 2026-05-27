import tempfile
import tarfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch

from agentflow.core import (
    doctor_project,
    init_project,
    recommend_route,
    render_handoff_prompt,
    scan_project,
)
from agentflow.repair import apply_repair_plan, build_repair_plan
from agentflow.context import render_context_markdown, save_context
from agentflow.diagnostics import detect_tools
from agentflow.state import load_state, update_state
from agentflow.changes import create_change, list_changes, show_change
from agentflow.skills import (
    bind_skill_root,
    discover_global_skills,
    import_local_skill,
    install_npm_skill,
    install_npx_skill_command,
    sync_project_skill_index,
)
from agentflow import templates


class CoreTests(unittest.TestCase):
    def test_init_project_creates_workflow_skeleton(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            home = Path(directory) / "home"
            result = init_project(
                project_dir,
                project_name="Sample App",
                editors=["codex", "claude", "cursor", "kiro", "qoder", "antigravity"],
                link_global_skills=False,
                home=home,
            )

            expected_files = [
                ".agentflow/README.md",
                ".agentflow/constitution.md",
                ".agentflow/state.yaml",
                ".agentflow/skills/SKILL.md",
                ".agentflow/skills/brainstorm.md",
                ".agentflow/skills/spec.md",
                ".agentflow/skills/plan.md",
                ".agentflow/skills/implement.md",
                ".agentflow/skills/verify.md",
                ".agentflow/skills/finish.md",
                ".agentflow/prompts/codex.md",
                ".agentflow/prompts/cursor.md",
                ".agentflow/prompts/claude.md",
                ".agentflow/prompts/kiro.md",
                ".agentflow/prompts/qoder.md",
                ".agentflow/interfaces/README.md",
                ".agentflow/interfaces/codex.md",
                ".agentflow/interfaces/claude.md",
                ".agentflow/interfaces/cursor.md",
                ".agentflow/interfaces/kiro.md",
                ".agentflow/interfaces/qoder.md",
                ".agentflow/interfaces/antigravity.md",
                ".agentflow/changes/.gitkeep",
                "AGENTS.md",
                ".codex/skills/agentflow/SKILL.md",
                ".claude/skills/agentflow/SKILL.md",
                ".cursor/skills/agentflow/SKILL.md",
                ".kiro/steering/agentflow.md",
                ".qoder/skills/agentflow/SKILL.md",
                ".agent/skills/agentflow/SKILL.md",
            ]

            self.assertTrue(result["created"])
            for relative in expected_files:
                self.assertTrue((project_dir / relative).is_file(), relative)

            constitution = (project_dir / ".agentflow/constitution.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Sample App", constitution)
            self.assertIn("AI Coding Constitution", constitution)

            state = (project_dir / ".agentflow/state.yaml").read_text(encoding="utf-8")
            self.assertIn("flow instructions", state)
            self.assertNotIn("agentflow ask", state)

    def test_constitution_includes_verification_and_cleanup_contracts(self) -> None:
        content = templates.constitution("Demo")

        self.assertIn("Task Gates", content)
        self.assertIn("Verification Ladder", content)
        self.assertIn("Do not claim success without verification evidence", content)
        self.assertIn("Quality Cleanup Pass", content)
        self.assertIn("files changed", content)
        self.assertIn("commands run", content)

    def test_skill_index_routes_failures_and_deslop_cleanup(self) -> None:
        content = templates.skill_index()

        self.assertIn("Compiler, typecheck, lint, CI", content)
        self.assertIn("UI change", content)
        self.assertIn("CLI change", content)
        self.assertIn("deslop pass", content)
        self.assertIn("Do not leave TODOs", content)

    def test_agent_instructions_require_scope_and_evidence(self) -> None:
        content = templates.AGENT_INSTRUCTIONS

        self.assertIn("scope, non-goals, and acceptance criteria", content)
        self.assertIn("Prefer deterministic local checks", content)
        self.assertIn("quality cleanup pass", content)
        self.assertIn("acceptance evidence", content)
        self.assertIn("recommended next step", content)

    def test_init_project_is_idempotent_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            init_project(project_dir, project_name="First")
            constitution_path = project_dir / ".agentflow/constitution.md"
            constitution_path.write_text("custom constitution", encoding="utf-8")

            init_project(project_dir, project_name="Second")

            self.assertEqual(
                constitution_path.read_text(encoding="utf-8"),
                "custom constitution",
            )

    def test_scan_project_detects_python_and_node_signals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            (project_dir / "pyproject.toml").write_text(
                "[project]\nname = 'demo'\n", encoding="utf-8"
            )
            (project_dir / "package.json").write_text(
                '{"scripts":{"test":"vitest"}}', encoding="utf-8"
            )
            (project_dir / "README.md").write_text("# Demo\n", encoding="utf-8")

            result = scan_project(project_dir)

            self.assertEqual(result["project_types"], ["python", "node"])
            self.assertIn("python -m pytest", result["test_commands"])
            self.assertIn("npm test", result["test_commands"])
            self.assertEqual(result["docs"], ["README.md"])

    def test_scan_project_suggests_unittest_when_tests_dir_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            (project_dir / "pyproject.toml").write_text(
                "[project]\nname = 'demo'\n", encoding="utf-8"
            )
            (project_dir / "tests").mkdir()

            result = scan_project(project_dir)

            self.assertIn("python -m pytest", result["test_commands"])
            self.assertIn("python -m unittest discover -s tests", result["test_commands"])

    def test_recommend_route_for_project_start_prefers_spec_first(self) -> None:
        advice = recommend_route("我要从零开始做一个 AI coding 工作流工具")

        self.assertEqual(advice["phase"], "project-start")
        self.assertEqual(advice["workflow"], "openspec-or-spec-kit")
        self.assertIn("constitution", advice["next_artifacts"])
        self.assertFalse(advice["implementation_allowed"])

    def test_recommend_route_for_small_bugfix_prefers_targeted_prompt(self) -> None:
        advice = recommend_route("修复分页切换后列表没有刷新的 bug")

        self.assertEqual(advice["phase"], "bugfix")
        self.assertEqual(advice["workflow"], "simple-change")
        self.assertIn(advice["recommended_agent"], {"codex", "cursor", "claude"})
        self.assertTrue(advice["implementation_allowed"])

    def test_recommend_route_for_security_change_requires_spec(self) -> None:
        advice = recommend_route("给运行时文件写入增加安全策略，禁止写出 workspace")

        self.assertEqual(advice["phase"], "design-required")
        self.assertEqual(advice["workflow"], "openspec-change")
        self.assertFalse(advice["implementation_allowed"])
        self.assertIn("verify", advice["required_skills"])

    def test_render_handoff_prompt_includes_agentflow_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            init_project(project_dir, project_name="Demo")

            prompt = render_handoff_prompt(
                project_dir,
                platform="codex",
                request="给运行时文件写入增加安全策略",
            )

            self.assertIn("Codex", prompt)
            self.assertIn(".agentflow/constitution.md", prompt)
            self.assertIn(".agentflow/state.yaml", prompt)
            self.assertIn(".agentflow/skills/SKILL.md", prompt)
            self.assertIn("给运行时文件写入增加安全策略", prompt)
            self.assertIn("Do not start implementation", prompt)
            self.assertIn("acceptance", prompt.lower())

    def test_doctor_reports_missing_entrypoints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            init_project(project_dir, project_name="Demo")
            (project_dir / "AGENTS.md").unlink()

            report = doctor_project(project_dir)

            self.assertFalse(report["ok"])
            self.assertIn("AGENTS.md", report["missing"])
            self.assertNotIn(".agentflow/skills/SKILL.md", report["missing"])

    def test_repair_plan_restores_missing_base_files_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            init_project(project_dir, project_name="Demo")
            agents_path = project_dir / "AGENTS.md"
            agents_path.unlink()

            plan = build_repair_plan(project_dir, project_name="Demo")

            self.assertEqual([action.relative_path for action in plan.actions], ["AGENTS.md"])
            result = apply_repair_plan(plan)

            self.assertEqual(result["created"], ["AGENTS.md"])
            self.assertTrue(agents_path.is_file())
            self.assertIn(".agentflow/interfaces/README.md", agents_path.read_text(encoding="utf-8"))
            self.assertTrue(doctor_project(project_dir)["ok"])

    def test_context_markdown_summarizes_project_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            init_project(project_dir, project_name="Demo")
            (project_dir / "pyproject.toml").write_text(
                "[project]\nname = 'demo'\n", encoding="utf-8"
            )
            (project_dir / "tests").mkdir()

            content = render_context_markdown(project_dir)

            self.assertIn("# Flow Context", content)
            self.assertIn("## Project", content)
            self.assertIn("python -m unittest discover -s tests", content)
            self.assertIn("## AgentFlow State", content)

    def test_save_context_writes_default_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            init_project(project_dir, project_name="Demo")

            result = save_context(project_dir)

            output = project_dir / "FLOW_CONTEXT.md"
            self.assertEqual(result["path"], str(output))
            self.assertTrue(output.is_file())
            self.assertIn("# Flow Context", output.read_text(encoding="utf-8"))

    def test_detect_tools_reports_installed_and_missing_tools(self) -> None:
        paths = {"codex": "C:/Tools/codex.exe", "cursor": "D:/Cursor/cursor.cmd"}

        tools = detect_tools(path_resolver=lambda command: paths.get(command))

        by_name = {tool.name: tool for tool in tools}
        self.assertEqual(by_name["codex"].status, "ok")
        self.assertEqual(by_name["codex"].path, "C:/Tools/codex.exe")
        self.assertEqual(by_name["cursor"].status, "ok")
        self.assertEqual(by_name["claude"].status, "missing")
        self.assertEqual(by_name["claude"].path, "")

    def test_update_state_changes_selected_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            init_project(project_dir, project_name="Demo")

            updated = update_state(
                project_dir,
                phase="implement",
                current_goal="ship local assistant",
                next_action="run flow context save",
            )

            self.assertEqual(updated["phase"], "implement")
            self.assertEqual(updated["current_goal"], "ship local assistant")
            self.assertEqual(updated["next_action"], "run flow context save")
            loaded = load_state(project_dir)
            self.assertEqual(loaded["phase"], "implement")
            self.assertEqual(loaded["current_goal"], "ship local assistant")

    def test_create_change_creates_change_folder_and_updates_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            init_project(project_dir, project_name="Demo")

            result = create_change(
                project_dir,
                title="Improve Local Handoffs",
                summary="Make context switching easier.",
            )

            readme = Path(result["path"]) / "README.md"
            self.assertEqual(result["id"], "improve-local-handoffs")
            self.assertTrue(readme.is_file())
            content = readme.read_text(encoding="utf-8")
            self.assertIn("# Improve Local Handoffs", content)
            self.assertIn("Make context switching easier.", content)
            state = load_state(project_dir)
            self.assertEqual(state["active_change"], "improve-local-handoffs")

    def test_list_and_show_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            init_project(project_dir, project_name="Demo")
            create_change(project_dir, title="First Change", summary="Alpha")
            create_change(project_dir, title="Second Change", summary="Beta")

            changes = list_changes(project_dir)
            shown = show_change(project_dir, "first-change")

            self.assertEqual([item["id"] for item in changes], ["first-change", "second-change"])
            self.assertIn("# First Change", shown["content"])
            self.assertIn("Alpha", shown["content"])

    def test_global_skill_import_and_sync_updates_project_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project_dir = root / "project"
            source_dir = root / "source-skill"
            project_dir.mkdir()
            source_dir.mkdir()
            init_project(project_dir, project_name="Demo")
            (source_dir / "SKILL.md").write_text(
                "---\n"
                "name: code-review\n"
                "description: Review worker output before accepting changes.\n"
                "---\n\n"
                "# Code Review\n",
                encoding="utf-8",
            )

            bind_skill_root(home / "skills", home=home)
            installed = import_local_skill(source_dir, home=home)
            skills = discover_global_skills(home=home)
            sync_result = sync_project_skill_index(project_dir, home=home)

            self.assertEqual(installed.name, "code-review")
            self.assertTrue((home / "skills" / "code-review" / "SKILL.md").is_file())
            self.assertEqual([skill.name for skill in skills], ["code-review"])
            self.assertEqual(sync_result["synced"], 1)

            index = (project_dir / ".agentflow" / "skills" / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Global Skill Roots", index)
            self.assertIn("code-review", index)
            self.assertIn("Review worker output", index)
            self.assertIn(str(home / "skills" / "code-review" / "SKILL.md"), index)

    def test_npm_skill_install_uses_pack_without_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            bind_skill_root(home / "skills", home=home)

            def fake_run(command, text, capture_output, check):
                self.assertEqual(command[:2], ["npm", "pack"])
                self.assertIn("--ignore-scripts", command)
                pack_destination = Path(command[command.index("--pack-destination") + 1])
                pack_destination.mkdir(parents=True, exist_ok=True)
                tarball = pack_destination / "agentflow-skill-npm-review-1.0.0.tgz"
                skill_file = Path(directory) / "SKILL.md"
                skill_file.write_text(
                    "---\n"
                    "name: npm-review\n"
                    "description: Installed from npm pack.\n"
                    "---\n\n"
                    "# NPM Review\n",
                    encoding="utf-8",
                )
                with tarfile.open(tarball, "w:gz") as tf:
                    tf.add(skill_file, arcname="package/SKILL.md")
                return subprocess.CompletedProcess(command, 0, str(tarball.name), "")

            with patch("agentflow.skills.subprocess.run", side_effect=fake_run):
                installed = install_npm_skill("npm-review", home=home)

            self.assertEqual(installed.name, "npm-review")
            self.assertTrue((home / "skills" / "npm-review" / "SKILL.md").is_file())

    def test_npx_skills_add_installs_named_skill_from_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            source = root / "repo"
            skill_dir = source / "skills" / "find-skills"
            skill_dir.mkdir(parents=True)
            bind_skill_root(home / "skills", home=home)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: find-skills\n"
                "description: Find useful coding skills.\n"
                "---\n\n"
                "# Find Skills\n",
                encoding="utf-8",
            )

            installed = install_npx_skill_command(
                ["skills", "add", str(source), "--skill", "find-skills"],
                home=home,
            )

            self.assertEqual(installed.name, "find-skills")
            self.assertTrue((home / "skills" / "find-skills" / "SKILL.md").is_file())

    def test_npx_skills_add_all_installs_every_skill_from_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            source = root / "repo"
            first = source / "skills" / "first-skill"
            second = source / "skills" / "second-skill"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            bind_skill_root(home / "skills", home=home)
            (first / "SKILL.md").write_text(
                "---\n"
                "name: first-skill\n"
                "description: First batch skill.\n"
                "---\n\n"
                "# First\n",
                encoding="utf-8",
            )
            (second / "SKILL.md").write_text(
                "---\n"
                "name: second-skill\n"
                "description: Second batch skill.\n"
                "---\n\n"
                "# Second\n",
                encoding="utf-8",
            )

            installed = install_npx_skill_command(
                ["skills", "add", str(source), "--all"],
                home=home,
            )

            self.assertEqual([skill.name for skill in installed], ["first-skill", "second-skill"])
            self.assertTrue((home / "skills" / "first-skill" / "SKILL.md").is_file())
            self.assertTrue((home / "skills" / "second-skill" / "SKILL.md").is_file())

    def test_skill_import_accepts_utf8_bom_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            source_dir = root / "bom-skill"
            source_dir.mkdir()
            bind_skill_root(home / "skills", home=home)
            (source_dir / "SKILL.md").write_text(
                "---\n"
                "name: bom-review\n"
                "description: Handles UTF-8 BOM files.\n"
                "---\n\n"
                "# BOM Review\n",
                encoding="utf-8-sig",
            )

            installed = import_local_skill(source_dir, home=home)

            self.assertEqual(installed.name, "bom-review")

    # -- Editor entrypoint safety tests ---------------------------------------

    def test_apply_editors_does_not_delete_user_files_in_editor_folder(self) -> None:
        """Disabling an editor must NOT remove user files like .cursor/settings.json."""
        from agentflow.editors import (
            apply_editors,
            save_editor_config,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "project"
            project.mkdir()

            # Simulate a user file in .cursor/
            cursor_dir = project / ".cursor"
            cursor_dir.mkdir(parents=True)
            user_file = cursor_dir / "settings.json"
            user_file.write_text('{"editor.fontSize": 14}', encoding="utf-8")

            # Put an AgentFlow-generated entrypoint in place
            entrypoint = project / ".cursor" / "skills" / "agentflow" / "SKILL.md"
            entrypoint.parent.mkdir(parents=True)
            from agentflow.templates import thin_entrypoint
            entrypoint.write_text(thin_entrypoint("cursor"), encoding="utf-8")

            # Configure: cursor is NOT enabled
            save_editor_config(["claude"], home=home)

            result = apply_editors(project, home=home)

            # The entrypoint was removed
            self.assertFalse(entrypoint.exists())
            self.assertIn(".cursor/skills/agentflow/SKILL.md", result["removed"])

            # The user file is still there
            self.assertTrue(user_file.exists())
            self.assertEqual(user_file.read_text(encoding="utf-8"), '{"editor.fontSize": 14}')

            # The .cursor top-level directory still exists
            self.assertTrue(cursor_dir.exists())

    def test_apply_editors_skips_non_agentflow_entrypoint(self) -> None:
        """A file at the entrypoint path that wasn't generated by AgentFlow
        must NOT be deleted; it should be reported as skipped."""
        from agentflow.editors import apply_editors, save_editor_config

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "project"
            project.mkdir()

            # Put a user-written file at the entrypoint path
            entrypoint = project / ".cursor" / "skills" / "agentflow" / "SKILL.md"
            entrypoint.parent.mkdir(parents=True)
            entrypoint.write_text("# My custom cursor skill\n\nDo not delete.", encoding="utf-8")

            # cursor is NOT enabled
            save_editor_config(["claude"], home=home)

            result = apply_editors(project, home=home)

            # File was NOT removed
            self.assertTrue(entrypoint.exists())
            self.assertIn(".cursor/skills/agentflow/SKILL.md", result["skipped"])
            self.assertNotIn(".cursor/skills/agentflow/SKILL.md", result["removed"])

    def test_apply_editors_removes_agentflow_entrypoint_and_prunes_empty_dirs(self) -> None:
        """When the entrypoint and its parent dirs are empty after removal,
        they should be pruned — except the top-level editor folder."""
        from agentflow.editors import apply_editors, save_editor_config

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "project"
            project.mkdir()

            # Generate an entrypoint
            entrypoint = project / ".codex" / "skills" / "agentflow" / "SKILL.md"
            entrypoint.parent.mkdir(parents=True)
            from agentflow.templates import thin_entrypoint
            entrypoint.write_text(thin_entrypoint("codex"), encoding="utf-8")

            # codex NOT enabled
            save_editor_config([], home=home)

            result = apply_editors(project, home=home)

            self.assertIn(".codex/skills/agentflow/SKILL.md", result["removed"])
            # Empty parent dirs were pruned
            self.assertFalse((project / ".codex" / "skills" / "agentflow").exists())
            self.assertFalse((project / ".codex" / "skills").exists())
            # But .codex top-level folder IS kept (not deleted)
            self.assertTrue((project / ".codex").is_dir())

    def test_thin_entrypoint_contains_generated_marker(self) -> None:
        """The generated entrypoint must contain the safety marker."""
        from agentflow.templates import thin_entrypoint, AGENTFLOW_GENERATED_MARKER
        content = thin_entrypoint("codex")
        self.assertIn(AGENTFLOW_GENERATED_MARKER, content)

    # -- Project registry path-based dedup ------------------------------------

    def test_register_projects_dedup_by_path_not_name(self) -> None:
        """Two projects in different paths but same dir name can both register."""
        from agentflow.projects import list_projects, register_project

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project_a = root / "workspace-a" / "myapp"
            project_b = root / "workspace-b" / "myapp"
            project_a.mkdir(parents=True)
            project_b.mkdir(parents=True)

            register_project(project_a, home=home)
            register_project(project_b, home=home)

            entries = list_projects(home)
            paths = {str(entry.path) for entry in entries}

            self.assertEqual(len(entries), 2)
            self.assertIn(str(project_a.resolve()), paths)
            self.assertIn(str(project_b.resolve()), paths)

    # -- Editor entrypoint path safety ----------------------------------------

    def test_add_custom_editor_rejects_absolute_windows_path(self) -> None:
        from agentflow.editors import add_custom_editor

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            with self.assertRaises(ValueError):
                add_custom_editor("bad", "C:\\tmp\\x.md", home=home)
            with self.assertRaises(ValueError):
                add_custom_editor("bad", "/etc/passwd", home=home)

    def test_add_custom_editor_rejects_parent_traversal(self) -> None:
        from agentflow.editors import add_custom_editor

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            with self.assertRaises(ValueError):
                add_custom_editor("bad", "../outside/SKILL.md", home=home)
            with self.assertRaises(ValueError):
                add_custom_editor("bad", ".agentflow/../../etc/SKILL.md", home=home)

    def test_add_custom_editor_rejects_empty_or_directory_only(self) -> None:
        from agentflow.editors import add_custom_editor

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            with self.assertRaises(ValueError):
                add_custom_editor("bad", "", home=home)
            with self.assertRaises(ValueError):
                add_custom_editor("bad", "   ", home=home)
            with self.assertRaises(ValueError):
                add_custom_editor("bad", ".myeditor/skills/", home=home)

    def test_apply_editors_skips_unsafe_custom_path(self) -> None:
        """A persisted custom editor with an unsafe path must not write or delete
        anything outside the project root; it should be reported in skipped."""
        from agentflow.editors import apply_editors, save_editor_config

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "project"
            project.mkdir()

            # Bypass add_custom_editor and persist a malicious config directly
            # (simulating a hand-edited or pre-validation editors.yaml).
            save_editor_config(
                enabled=["bad"],
                custom={
                    "bad": {
                        "display": "Bad",
                        "path": "../outside/EVIL.md",
                    }
                },
                home=home,
            )

            result = apply_editors(project, home=home)

            outside = root / "outside" / "EVIL.md"
            self.assertFalse(outside.exists())
            self.assertIn("../outside/EVIL.md", result["skipped"])
            self.assertEqual(result["created"], [])
            self.assertEqual(result["removed"], [])

    # -- Project registry: unique keys & safe unregister ----------------------

    def test_register_same_name_different_paths_uses_unique_yaml_keys(self) -> None:
        from agentflow.projects import _registry_path, list_projects, register_project

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            a = root / "ws-a" / "myapp"
            b = root / "ws-b" / "myapp"
            a.mkdir(parents=True)
            b.mkdir(parents=True)

            register_project(a, home=home)
            register_project(b, home=home)

            text = _registry_path(home).read_text(encoding="utf-8")
            # The legacy single-key form `  myapp:` must NOT appear.
            self.assertNotIn("  myapp:\n", text)
            # Each entry must store its display name explicitly.
            self.assertEqual(text.count('name: "myapp"'), 2)

            entries = list_projects(home)
            self.assertEqual(len(entries), 2)
            for entry in entries:
                self.assertEqual(entry.name, "myapp")
            keys = {entry.key for entry in entries}
            self.assertEqual(len(keys), 2)

    def test_register_same_path_twice_keeps_single_entry(self) -> None:
        from agentflow.projects import list_projects, register_project

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "myapp"
            project.mkdir()

            register_project(project, home=home)
            register_project(project, home=home)

            entries = list_projects(home)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].path, project.resolve())

    def test_unregister_refuses_when_display_name_is_ambiguous(self) -> None:
        from agentflow.projects import list_projects, register_project, unregister_project

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            a = root / "ws-a" / "myapp"
            b = root / "ws-b" / "myapp"
            a.mkdir(parents=True)
            b.mkdir(parents=True)

            register_project(a, home=home)
            register_project(b, home=home)

            # Two entries share the display name -> refuse to delete.
            self.assertFalse(unregister_project("myapp", home=home))
            self.assertEqual(len(list_projects(home)), 2)

            # Unique key still resolves to a single entry.
            entries = list_projects(home)
            self.assertTrue(unregister_project(entries[0].key, home=home))
            self.assertEqual(len(list_projects(home)), 1)

    def test_list_projects_reads_legacy_format(self) -> None:
        from agentflow.projects import _registry_path, list_projects

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            path = _registry_path(home)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "projects:\n"
                "  myapp:\n"
                '    path: "D:/legacy/myapp"\n',
                encoding="utf-8",
            )

            entries = list_projects(home)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].name, "myapp")
            self.assertEqual(entries[0].key, "myapp")
            self.assertEqual(str(entries[0].path).replace("\\", "/"), "D:/legacy/myapp")


if __name__ == "__main__":
    unittest.main()
