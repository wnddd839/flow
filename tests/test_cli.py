import subprocess
import sys
import tempfile
import unittest
import os
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_DEPS = ROOT / ".test-deps"


def run_cli(
    project_dir: Path,
    *args: str,
    input_text: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-m", "agentflow.cli", *args]
    env = os.environ.copy()
    pythonpath_parts = [str(ROOT)]
    if TEST_DEPS.exists():
        pythonpath_parts.append(str(TEST_DEPS))
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    if extra_env:
        env.update(extra_env)
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
    # -- Direct CLI subcommands -----------------------------------------------

    def test_cli_init_and_doctor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            init_result = run_cli(project_dir, "init", "--name", "CLI Demo")

            self.assertEqual(init_result.returncode, 0, init_result.stderr)
            self.assertIn("Initialized AgentFlow", init_result.stdout)
            self.assertTrue((project_dir / ".agentflow/constitution.md").is_file())
            self.assertTrue((project_dir / ".agentflow/README.md").is_file())

            doctor_result = run_cli(project_dir, "doctor")

            self.assertEqual(doctor_result.returncode, 0, doctor_result.stderr)
            self.assertIn("AgentFlow doctor: OK", doctor_result.stdout)

    def test_cli_init_creates_agentflow_readme(self) -> None:
        """flow init generates .agentflow/README.md."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "Demo")

            readme = project_dir / ".agentflow" / "README.md"
            self.assertTrue(readme.is_file())
            content = readme.read_text(encoding="utf-8")
            self.assertIn("AgentFlow", content)
            self.assertIn("source of truth", content)

    def test_cli_ask_outputs_route_advice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "CLI Demo")

            result = run_cli(project_dir, "ask", "修复分页切换后列表没有刷新的 bug")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Recommended workflow: simple-change", result.stdout)
            self.assertIn("Phase: bugfix", result.stdout)
            self.assertIn("flow handoff", result.stdout)

    def test_cli_handoff_outputs_platform_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "CLI Demo")

            result = run_cli(
                project_dir,
                "handoff",
                "cursor",
                "补充登录流程的集成测试",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Cursor", result.stdout)
            self.assertIn(".agentflow/constitution.md", result.stdout)
            self.assertIn("补充登录流程的集成测试", result.stdout)

    def test_cli_instructions_initialized(self) -> None:
        """flow instructions outputs agent instructions when initialized."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "Demo")

            result = run_cli(project_dir, "instructions")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("AgentFlow-initialized project", result.stdout)
            self.assertIn(".agentflow/README.md", result.stdout)
            self.assertIn(".agentflow/constitution.md", result.stdout)
            self.assertIn("recommended next step", result.stdout)

    def test_cli_instructions_not_initialized(self) -> None:
        """flow instructions fails gracefully when not initialized."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)

            result = run_cli(project_dir, "instructions")

            self.assertEqual(result.returncode, 1)
            self.assertIn("not initialized", result.stdout.lower())
            self.assertIn("flow init", result.stdout)

    def test_cli_status_not_initialized_uses_flow_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)

            result = run_cli(project_dir, "status")

            self.assertEqual(result.returncode, 1)
            self.assertIn("flow init", result.stdout)
            self.assertNotIn("agentflow init", result.stdout)

    def test_cli_repair_dry_run_reports_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "CLI Demo")
            (project_dir / "AGENTS.md").unlink()

            result = run_cli(project_dir, "repair", "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Repair plan", result.stdout)
            self.assertIn("create AGENTS.md", result.stdout)
            self.assertFalse((project_dir / "AGENTS.md").exists())

    def test_cli_repair_restores_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "CLI Demo")
            (project_dir / "AGENTS.md").unlink()

            result = run_cli(project_dir, "repair")
            doctor = run_cli(project_dir, "doctor")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Created: 1", result.stdout)
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)

    def test_cli_context_save_writes_context_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "CLI Demo")

            result = run_cli(project_dir, "context", "save")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Saved context:", result.stdout)
            context_file = project_dir / "FLOW_CONTEXT.md"
            self.assertTrue(context_file.is_file())
            self.assertIn("# Flow Context", context_file.read_text(encoding="utf-8"))

    def test_cli_tools_json_outputs_known_tool_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)

            result = run_cli(project_dir, "tools", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            names = {item["name"] for item in data["tools"]}
            self.assertIn("codex", names)
            self.assertIn("claude", names)
            self.assertIn("cursor", names)

    def test_cli_state_set_updates_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "CLI Demo")

            result = run_cli(
                project_dir,
                "state",
                "set",
                "--phase",
                "implement",
                "--goal",
                "improve local workflow",
                "--next",
                "save context",
            )
            status = run_cli(project_dir, "status")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Updated state", result.stdout)
            self.assertIn('phase: "implement"', status.stdout)
            self.assertIn('current_goal: "improve local workflow"', status.stdout)
            self.assertIn('next_action: "save context"', status.stdout)

    def test_cli_snapshot_updates_state_and_writes_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "CLI Demo")

            result = run_cli(
                project_dir,
                "snapshot",
                "--phase",
                "verify",
                "--goal",
                "prepare handoff",
                "--next",
                "open another tool",
            )
            status = run_cli(project_dir, "status")
            context_file = project_dir / "FLOW_CONTEXT.md"

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Updated state", result.stdout)
            self.assertIn("Saved context", result.stdout)
            self.assertTrue(context_file.is_file())
            self.assertIn('phase: "verify"', status.stdout)
            self.assertIn('current_goal: "prepare handoff"', status.stdout)
            self.assertIn('next_action: "open another tool"', status.stdout)
            self.assertIn("prepare handoff", context_file.read_text(encoding="utf-8"))

    def test_cli_changes_new_creates_change_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "CLI Demo")

            result = run_cli(
                project_dir,
                "changes",
                "new",
                "Improve Local Handoffs",
                "--summary",
                "Make context switching easier.",
            )
            status = run_cli(project_dir, "status")
            readme = project_dir / ".agentflow" / "changes" / "improve-local-handoffs" / "README.md"

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Created change: improve-local-handoffs", result.stdout)
            self.assertTrue(readme.is_file())
            self.assertIn("Make context switching easier.", readme.read_text(encoding="utf-8"))
            self.assertIn('active_change: "improve-local-handoffs"', status.stdout)

    def test_cli_changes_list_and_show_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "CLI Demo")
            run_cli(project_dir, "changes", "new", "First Change", "--summary", "Alpha")
            run_cli(project_dir, "changes", "new", "Second Change", "--summary", "Beta")

            list_result = run_cli(project_dir, "changes", "list")
            show_result = run_cli(project_dir, "changes", "show", "first-change")

            self.assertEqual(list_result.returncode, 0, list_result.stderr)
            self.assertIn("first-change", list_result.stdout)
            self.assertIn("First Change", list_result.stdout)
            self.assertIn("second-change", list_result.stdout)
            self.assertEqual(show_result.returncode, 0, show_result.stderr)
            self.assertIn("# First Change", show_result.stdout)
            self.assertIn("Alpha", show_result.stdout)

    def test_cli_skills_import_list_and_sync(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project_dir = root / "project"
            source_dir = root / "skill-src"
            project_dir.mkdir()
            source_dir.mkdir()
            (source_dir / "SKILL.md").write_text(
                "---\n"
                "name: review-loop\n"
                "description: Review another agent output.\n"
                "---\n\n"
                "# Review Loop\n",
                encoding="utf-8",
            )
            env = {"AGENTFLOW_HOME": str(home)}
            run_cli(project_dir, "init", "--name", "Demo", extra_env=env)

            bind_result = run_cli(
                project_dir,
                "skills",
                "bind",
                str(home / "skills"),
                extra_env=env,
            )
            import_result = run_cli(
                project_dir,
                "skills",
                "import",
                str(source_dir),
                extra_env=env,
            )
            list_result = run_cli(project_dir, "skills", "list", extra_env=env)
            sync_result = run_cli(project_dir, "skills", "sync", extra_env=env)

            self.assertEqual(bind_result.returncode, 0, bind_result.stderr)
            self.assertEqual(import_result.returncode, 0, import_result.stderr)
            self.assertIn("Installed skill: review-loop", import_result.stdout)
            self.assertIn("review-loop", list_result.stdout)
            self.assertIn("Synced project index", sync_result.stdout)
            self.assertIn(
                "review-loop",
                (project_dir / ".agentflow/skills/SKILL.md").read_text(encoding="utf-8"),
            )

    def test_cli_skills_all_installs_every_skill_from_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project_dir = root / "project"
            source_dir = root / "skill-pack"
            first = source_dir / "skills" / "batch-one"
            second = source_dir / "skills" / "batch-two"
            project_dir.mkdir()
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            (first / "SKILL.md").write_text(
                "---\n"
                "name: batch-one\n"
                "description: First batch import.\n"
                "---\n\n"
                "# Batch One\n",
                encoding="utf-8",
            )
            (second / "SKILL.md").write_text(
                "---\n"
                "name: batch-two\n"
                "description: Second batch import.\n"
                "---\n\n"
                "# Batch Two\n",
                encoding="utf-8",
            )
            env = {"AGENTFLOW_HOME": str(home)}
            run_cli(project_dir, "init", "--name", "Demo", extra_env=env)

            result = run_cli(project_dir, "skills", "all", str(source_dir), extra_env=env)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Installed skills: 2", result.stdout)
            self.assertIn("batch-one", result.stdout)
            self.assertIn("batch-two", result.stdout)
            self.assertTrue((home / "skills" / "batch-one" / "SKILL.md").is_file())
            self.assertTrue((home / "skills" / "batch-two" / "SKILL.md").is_file())
            index = (project_dir / ".agentflow/skills/SKILL.md").read_text(encoding="utf-8")
            self.assertIn("batch-one", index)
            self.assertIn("batch-two", index)

    # -- REPL dashboard tests -------------------------------------------------

    def test_dashboard_shows_workbench_branding(self) -> None:
        """Startup shows product branding and the framed command prompt."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(project_dir, input_text="0\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Flow", result.stdout)
            self.assertIn("AI Coding Workbench", result.stdout)
            self.assertIn('Try "/help" or type a task', result.stdout)
            self.assertIn("> ", result.stdout)
            self.assertIn("Bye.", result.stdout)
            # Status footer (Claude-Code-style) sits under the framed prompt.
            self.assertIn("not initialized", result.stdout)
            self.assertIn("missing", result.stdout)
            # The input must be wrapped: rule above and rule below the > line.
            lines = result.stdout.splitlines()
            input_indices = [i for i, ln in enumerate(lines) if ln.lstrip().startswith("> ")]
            self.assertTrue(input_indices, "expected a `> ` prompt line in output")
            i = input_indices[0]
            above = lines[i - 1].strip() if i > 0 else ""
            below = lines[i + 1].strip() if i + 1 < len(lines) else ""

            def _is_rule(text: str) -> bool:
                if len(text) < 20:
                    return False
                allowed = {"-", "\u2500"}
                return set(text) <= allowed

            self.assertTrue(_is_rule(above), f"expected rule above prompt, got: {above!r}")
            self.assertTrue(_is_rule(below), f"expected rule below prompt, got: {below!r}")

    def test_dashboard_shows_project_status(self) -> None:
        """Dashboard displays project path and doctor summary."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(project_dir, input_text="0\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Project", result.stdout)
            self.assertIn("missing", result.stdout)
            self.assertIn("not initialized", result.stdout)
            self.assertIn("Skills", result.stdout)

    def test_dashboard_shows_slash_command_hints(self) -> None:
        """Dashboard hints at slash commands instead of a numbered menu."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(project_dir, input_text="0\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("/init", result.stdout)
            self.assertIn("/check", result.stdout)
            self.assertIn("/skills", result.stdout)
            self.assertIn("/sync", result.stdout)
            self.assertIn("/npm", result.stdout)
            self.assertIn("/npx", result.stdout)
            self.assertIn("/local", result.stdout)

    def test_dashboard_does_not_show_menu_items(self) -> None:
        """Dashboard must not show the old numbered menu."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(project_dir, input_text="0\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("What do you want to do?", result.stdout)
            self.assertNotIn("Setup project", result.stdout)
            self.assertNotIn("Check setup", result.stdout)
            self.assertNotIn("Show agent instructions", result.stdout)
            self.assertNotIn("Route a task", result.stdout)
            self.assertNotIn("Generate handoff prompt", result.stdout)

    def test_dashboard_shows_hint(self) -> None:
        """Dashboard shows a tip about /help."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(project_dir, input_text="0\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("/help", result.stdout)

    def test_dashboard_recommends_setup_when_not_initialized(self) -> None:
        """When not initialized, the hint points to /init."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(project_dir, input_text="0\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("/init", result.stdout)

    def test_dashboard_recommends_check_when_initialized(self) -> None:
        """When initialized, the hint points to /check (alias /doctor)."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "Test")
            result = run_cli(project_dir, input_text="0\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("/check", result.stdout)

    def test_dashboard_distinguishes_initialized_with_missing_files(self) -> None:
        """Missing files in an initialized project should not read as uninitialized."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "Test")
            (project_dir / "AGENTS.md").unlink()

            result = run_cli(project_dir, input_text="0\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("needs attention", result.stdout)
            self.assertNotIn("not initialized  (run /init", result.stdout)

    # -- /help tests ----------------------------------------------------------

    def test_help_shows_full_command_table(self) -> None:
        """/help shows ALL commands including skill shortcuts."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(
                project_dir,
                input_text="/help\n/quit\n",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("/init", result.stdout)
            self.assertIn("/instructions", result.stdout)
            self.assertIn("/doctor", result.stdout)
            self.assertIn("/status", result.stdout)
            self.assertIn("/scan", result.stdout)
            self.assertIn("/ask", result.stdout)
            self.assertIn("/handoff", result.stdout)
            self.assertIn("/npm <package>", result.stdout)
            self.assertIn("/npx skills add", result.stdout)
            self.assertIn("/local <path>", result.stdout)
            self.assertIn("/skills", result.stdout)
            self.assertIn("/quit", result.stdout)

    # -- /menu tests ----------------------------------------------------------

    def test_menu_shows_numbered_shortcuts(self) -> None:
        """/menu should display numbered wizard menu."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(
                project_dir,
                input_text="/menu\n/quit\n",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Setup project", result.stdout)
            self.assertIn("Exit", result.stdout)

    # -- Wizard flow tests ----------------------------------------------------

    def test_wizard_setup_completes_init(self) -> None:
        """Input '1\\nMy Project\\n0\\n' completes initialization."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(project_dir, input_text="1\nMy Project\n0\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Setup Complete", result.stdout)
            self.assertIn("Initialized AgentFlow", result.stdout)
            self.assertIn("Doctor", result.stdout)
            self.assertTrue((project_dir / ".agentflow/constitution.md").is_file())
            self.assertTrue((project_dir / ".agentflow/README.md").is_file())

    def test_wizard_check_shows_doctor(self) -> None:
        """Input '2\\n0\\n' shows doctor output."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(project_dir, input_text="2\n0\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Doctor", result.stdout)
            self.assertIn("missing", result.stdout)

    def test_wizard_instructions_initialized(self) -> None:
        """Input '3\\n0\\n' shows agent instructions when initialized."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "Test")
            result = run_cli(project_dir, input_text="3\n0\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Agent Instructions", result.stdout)
            self.assertIn("AgentFlow-initialized project", result.stdout)

    def test_wizard_instructions_not_initialized(self) -> None:
        """Input '3\\n0\\n' prompts to init when not initialized."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(project_dir, input_text="3\n0\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("not initialized", result.stdout.lower())

    # -- /instructions in REPL ------------------------------------------------

    def test_interactive_instructions(self) -> None:
        """/instructions in REPL shows agent instructions."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "Test")
            result = run_cli(
                project_dir,
                input_text="/instructions\n/quit\n",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Agent Instructions", result.stdout)
            self.assertIn("AgentFlow-initialized project", result.stdout)

    # -- /ask and /handoff still work (legacy) --------------------------------

    def test_interactive_ask_bugfix(self) -> None:
        """/ask fix pagination bug still outputs simple-change."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(
                project_dir,
                input_text="/ask fix pagination bug\n/quit\n",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("simple-change", result.stdout)
            self.assertIn("bugfix", result.stdout)

    def test_interactive_handoff_codex(self) -> None:
        """/handoff codex still outputs Handoff for Codex."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(
                project_dir,
                input_text="/handoff codex fix pagination bug\n/quit\n",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Handoff for Codex", result.stdout)
            self.assertIn("fix pagination bug", result.stdout)

    def test_interactive_changes_list_and_show(self) -> None:
        """/changes and /change-show display local change records."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "Test")
            run_cli(project_dir, "changes", "new", "First Change", "--summary", "Alpha")

            result = run_cli(
                project_dir,
                input_text="/changes\n/change-show first-change\n/quit\n",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("first-change", result.stdout)
            self.assertIn("First Change", result.stdout)
            self.assertIn("# First Change", result.stdout)
            self.assertIn("Alpha", result.stdout)

    # -- /doctor in REPL ------------------------------------------------------

    def test_interactive_doctor_shows_file_table(self) -> None:
        """/doctor shows per-file OK/missing table."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            run_cli(project_dir, "init", "--name", "Test")

            result = run_cli(
                project_dir,
                input_text="/doctor\n/quit\n",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("OK", result.stdout)
            self.assertIn("Doctor", result.stdout)

    def test_unknown_command_suggests_closest_match(self) -> None:
        """/skill prompts the user about /skills."""
        with tempfile.TemporaryDirectory() as directory:
            project_dir = Path(directory)
            result = run_cli(
                project_dir,
                input_text="/skill\n/quit\n",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Unknown command:", result.stdout)
            self.assertIn("/skill", result.stdout)
            self.assertIn("Did you mean", result.stdout)
            self.assertIn("/skills", result.stdout)

    def test_repl_local_skill_shortcut_imports_and_syncs(self) -> None:
        """Typing 'local <path>' imports a skill and syncs the project index."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project_dir = root / "project"
            source_dir = root / "shortcut-skill"
            project_dir.mkdir()
            source_dir.mkdir()
            (source_dir / "SKILL.md").write_text(
                "---\n"
                "name: shortcut-review\n"
                "description: Imported from REPL shortcut.\n"
                "---\n\n"
                "# Shortcut Review\n",
                encoding="utf-8",
            )

            run_cli(project_dir, "init", "--name", "Test", extra_env={"AGENTFLOW_HOME": str(home)})
            result = run_cli(
                project_dir,
                input_text=f"local {source_dir}\nskills\n0\n",
                extra_env={"AGENTFLOW_HOME": str(home)},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Installed skill: shortcut-review", result.stdout)
            self.assertIn("shortcut-review", result.stdout)
            self.assertTrue((home / "skills" / "shortcut-review" / "SKILL.md").is_file())
            self.assertIn(
                "shortcut-review",
                (project_dir / ".agentflow/skills/SKILL.md").read_text(encoding="utf-8"),
            )

    def test_repl_npx_skills_add_shortcut_imports_named_skill(self) -> None:
        """Typing 'npx skills add <source> --skill <name>' imports that skill."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project_dir = root / "project"
            source_dir = root / "repo"
            skill_dir = source_dir / "skills" / "find-skills"
            project_dir.mkdir()
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: find-skills\n"
                "description: Find reusable skills.\n"
                "---\n\n"
                "# Find Skills\n",
                encoding="utf-8",
            )

            run_cli(project_dir, "init", "--name", "Test", extra_env={"AGENTFLOW_HOME": str(home)})
            result = run_cli(
                project_dir,
                input_text=f"npx skills add {source_dir} --skill find-skills\nskills\n0\n",
                extra_env={"AGENTFLOW_HOME": str(home)},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Installed skill: find-skills", result.stdout)
            self.assertIn("find-skills", result.stdout)
            self.assertTrue((home / "skills" / "find-skills" / "SKILL.md").is_file())
            self.assertIn(
                "find-skills",
                (project_dir / ".agentflow/skills/SKILL.md").read_text(encoding="utf-8"),
            )

    def test_repl_skill_all_batch_installs_multiple_skills(self) -> None:
        """Typing 'skill all' opens batch mode and installs all skills from lines."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project_dir = root / "project"
            source_dir = root / "pack"
            first = source_dir / "skills" / "alpha-skill"
            second = source_dir / "skills" / "beta-skill"
            project_dir.mkdir()
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            (first / "SKILL.md").write_text(
                "---\n"
                "name: alpha-skill\n"
                "description: Alpha batch skill.\n"
                "---\n\n"
                "# Alpha\n",
                encoding="utf-8",
            )
            (second / "SKILL.md").write_text(
                "---\n"
                "name: beta-skill\n"
                "description: Beta batch skill.\n"
                "---\n\n"
                "# Beta\n",
                encoding="utf-8",
            )

            run_cli(project_dir, "init", "--name", "Test", extra_env={"AGENTFLOW_HOME": str(home)})
            result = run_cli(
                project_dir,
                input_text=f"skill all\nnpx skills add {source_dir} --all\n\nskills\n0\n",
                extra_env={"AGENTFLOW_HOME": str(home)},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Batch Install", result.stdout)
            self.assertIn("Installed skills: 2", result.stdout)
            self.assertIn("alpha-skill", result.stdout)
            self.assertIn("beta-skill", result.stdout)
            self.assertTrue((home / "skills" / "alpha-skill" / "SKILL.md").is_file())
            self.assertTrue((home / "skills" / "beta-skill" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
