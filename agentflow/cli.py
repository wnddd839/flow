"""命令行入口（``flow`` / ``agentflow`` 控制台脚本指向此处）。

## 职责

- 无参数 → 委托 ``repl.run_repl`` 进入交互工作台
- 有参数 → ``argparse`` 解析子命令，经 ``COMMANDS`` 分发表调用 ``_cmd_*`` 处理函数

## 结构约定

- ``_build_parser``  — 注册所有子命令与参数
- ``_cmd_<name>``     — 薄包装，尽量把逻辑放在 ``core`` / ``skills`` 等模块
- ``_handle_*``       — skills / editors / projects 等**多级子命令**的共用实现
- ``COMMANDS``        — 子命令名 → 处理函数 的映射表（新增命令时改这里）

## 与其它模块

- 初始化/体检：``core``、``quick_setup``、``repair``、``diagnostics``
- 交接输出：``core.render_handoff_prompt``、``context.save_context``、``clipboard``
- 全局 skill / 编辑器：``skills``、``editors``、``projects``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import (
    doctor_project,
    init_project,
    recommend_route,
    render_handoff_prompt,
    scan_project,
    to_json,
)
from .clipboard import copy_to_clipboard, print_clipboard_notice
from .context import save_context
from .changes import create_change, list_changes, show_change
from .diagnostics import collect_diagnostics, detect_tools
from .repair import apply_repair_plan, build_repair_plan
from .state import update_state
from .quick_setup import run_quick_setup
from .skills import (
    bind_skill_root,
    describe_skill_home,
    discover_global_skills,
    import_local_skill,
    import_zip_skill,
    install_all_skill_source,
    install_github_skill,
    install_npm_skill,
    install_npx_skill_command,
    install_skill_source,
    sync_project_skill_index,
)
from .templates import AGENT_INSTRUCTIONS


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        from .repl import run_repl

        return run_repl(Path.cwd())

    parser = _build_parser()
    args = parser.parse_args(argv)
    cwd = Path.cwd()

    handler = COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args, cwd)


# -- Argument parser ----------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flow",
        description="Initialize and guide a lightweight AI coding workflow.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create .agentflow workflow files.")
    init_parser.add_argument("--name", default=None, help="Project display name.")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    init_parser.add_argument(
        "--editors",
        default=None,
        help="Comma-separated editor names to enable (codex,claude,cursor,kiro,qoder,antigravity).",
    )
    init_parser.add_argument(
        "--no-link",
        action="store_true",
        help="Skip creating .agentflow/skills/_global link to the global skill folder.",
    )
    init_parser.add_argument("--api-key-env", default="AGENTFLOW_API_KEY")
    init_parser.add_argument("--provider", default="openai-compatible")
    init_parser.add_argument("--model", default="gpt-5.2")

    setup_parser = subparsers.add_parser(
        "setup",
        help="Pick agents interactively and initialize in one step.",
    )
    setup_parser.add_argument("--name", default=None, help="Project display name.")
    setup_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing files."
    )

    subparsers.add_parser("scan", help="Print detected project signals.")
    state_parser = subparsers.add_parser("state", help="Update AgentFlow session state.")
    state_subparsers = state_parser.add_subparsers(dest="state_command", required=True)
    state_set_parser = state_subparsers.add_parser("set", help="Set state fields.")
    state_set_parser.add_argument("--phase", default=None)
    state_set_parser.add_argument("--goal", default=None, help="Current goal.")
    state_set_parser.add_argument("--change", default=None, help="Active change id or folder.")
    state_set_parser.add_argument("--next", default=None, help="Next action.")
    state_set_parser.add_argument("--blocked", choices=["true", "false"], default=None)
    snapshot_parser = subparsers.add_parser(
        "snapshot",
        help="Update state and save a handoff context in one step.",
    )
    snapshot_parser.add_argument("--phase", default=None)
    snapshot_parser.add_argument("--goal", default=None, help="Current goal.")
    snapshot_parser.add_argument("--change", default=None, help="Active change id or folder.")
    snapshot_parser.add_argument("--next", default=None, help="Next action.")
    snapshot_parser.add_argument("--blocked", choices=["true", "false"], default=None)
    snapshot_parser.add_argument("--output", default=None, help="Output path, default FLOW_CONTEXT.md.")
    changes_parser = subparsers.add_parser("changes", help="Manage local AgentFlow change records.")
    changes_subparsers = changes_parser.add_subparsers(dest="changes_command", required=True)
    changes_new_parser = changes_subparsers.add_parser("new", help="Create a new change record.")
    changes_new_parser.add_argument("title")
    changes_new_parser.add_argument("--summary", default="")
    changes_new_parser.add_argument("--id", default=None, help="Override the generated change id.")
    changes_subparsers.add_parser("list", help="List local change records.")
    changes_show_parser = changes_subparsers.add_parser("show", help="Show a local change record.")
    changes_show_parser.add_argument("id", help="Change id or folder name.")

    ask_parser = subparsers.add_parser("ask", help="Recommend a workflow for a request.")
    ask_parser.add_argument("request", help="What you want to build or fix.")

    handoff_parser = subparsers.add_parser("handoff", help="Generate a prompt for an agent.")
    handoff_parser.add_argument("platform", help="codex, claude, cursor, kiro, qoder, ...")
    handoff_parser.add_argument("request", help="What the target agent should work on.")

    subparsers.add_parser("status", help="Print .agentflow/state.yaml.")
    subparsers.add_parser("doctor", help="Check required workflow files (alias: check).")
    subparsers.add_parser("check", help="Alias for doctor.")
    repair_parser = subparsers.add_parser("repair", help="Restore missing AgentFlow files.")
    repair_parser.add_argument("--dry-run", action="store_true", help="Show the repair plan only.")
    repair_parser.add_argument("--name", default=None, help="Project display name for recreated files.")
    subparsers.add_parser("instructions", help="Show universal agent instructions.")
    tools_parser = subparsers.add_parser("tools", help="Show local AI coding tool availability.")
    tools_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    context_parser = subparsers.add_parser("context", help="Create local handoff context snapshots.")
    context_subparsers = context_parser.add_subparsers(dest="context_command", required=True)
    context_save_parser = context_subparsers.add_parser("save", help="Write FLOW_CONTEXT.md.")
    context_save_parser.add_argument("--output", default=None, help="Output path, default FLOW_CONTEXT.md.")
    npx_parser = subparsers.add_parser("npx", help="Install from an npx skills add command.")
    npx_parser.add_argument("args", nargs=argparse.REMAINDER)

    skills_parser = subparsers.add_parser("skills", help="Manage global AgentFlow skills.")
    skills_subparsers = skills_parser.add_subparsers(dest="skills_command", required=True)
    skills_subparsers.add_parser("home", help="Show global skill home.")
    bind_parser = skills_subparsers.add_parser("bind", help="Bind global skill root.")
    bind_parser.add_argument("path")
    skills_subparsers.add_parser("list", help="List installed global skills.")
    import_parser = skills_subparsers.add_parser("import", help="Import a local skill folder.")
    import_parser.add_argument("path")
    install_parser = skills_subparsers.add_parser("install", help="Install a skill source.")
    install_parser.add_argument("source", help="npm:<pkg>, gh:<repo>, zip:<path>, local:<path>")
    npm_parser = skills_subparsers.add_parser("npm", help="Install from npm.")
    npm_parser.add_argument("package")
    gh_parser = skills_subparsers.add_parser("gh", help="Install from GitHub.")
    gh_parser.add_argument("repo")
    zip_parser = skills_subparsers.add_parser("zip", help="Import a zip skill package.")
    zip_parser.add_argument("path")
    npx_skills_parser = skills_subparsers.add_parser("npx", help="Install from npx skills add.")
    npx_skills_parser.add_argument("args", nargs=argparse.REMAINDER)
    all_parser = skills_subparsers.add_parser(
        "all", help="Install every skill found in one or more sources."
    )
    all_parser.add_argument("sources", nargs="+")
    skills_subparsers.add_parser("sync", help="Sync global skills into this project index.")

    editors_parser = subparsers.add_parser("editors", help="Manage editor entrypoints.")
    editors_subparsers = editors_parser.add_subparsers(dest="editors_command", required=True)
    editors_subparsers.add_parser("list", help="Show editors and their enabled state.")
    add_editor_parser = editors_subparsers.add_parser("add", help="Enable a known editor.")
    add_editor_parser.add_argument("name")
    remove_editor_parser = editors_subparsers.add_parser("remove", help="Disable an editor.")
    remove_editor_parser.add_argument("name")
    add_custom_parser = editors_subparsers.add_parser(
        "add-custom", help="Register a custom editor entrypoint path."
    )
    add_custom_parser.add_argument("name")
    add_custom_parser.add_argument("path")
    add_custom_parser.add_argument("--display", default=None)
    remove_custom_parser = editors_subparsers.add_parser(
        "remove-custom", help="Remove a custom editor."
    )
    remove_custom_parser.add_argument("name")
    apply_parser = editors_subparsers.add_parser(
        "apply", help="Reconcile this project's editor entrypoints with the config."
    )
    apply_parser.add_argument("--force", action="store_true")

    projects_parser = subparsers.add_parser("projects", help="Manage registered projects.")
    projects_subparsers = projects_parser.add_subparsers(dest="projects_command", required=True)
    projects_subparsers.add_parser("list", help="List registered projects.")
    register_parser = projects_subparsers.add_parser("register", help="Register the current project.")
    register_parser.add_argument("--name", default=None)
    unregister_parser = projects_subparsers.add_parser(
        "unregister", help="Unregister a project by name."
    )
    unregister_parser.add_argument("name")
    projects_subparsers.add_parser(
        "sync-all", help="Re-link the global skill folder and refresh the index in every registered project."
    )

    return parser


# -- Command handlers ---------------------------------------------------------


def _cmd_init(args: argparse.Namespace, cwd: Path) -> int:
    # Bare `flow init` (no name/editors/force/no-link) is the interactive path:
    # route it through the one-shot agent picker so there is a single primary
    # entry point. Any explicit flag keeps the original non-interactive behavior
    # for scripts and CI.
    if _init_is_bare(args):
        return _cmd_setup(args, cwd)

    editor_list: list[str] | None = None
    if args.editors is not None:
        editor_list = [item.strip() for item in args.editors.split(",") if item.strip()]
    result = init_project(
        cwd,
        project_name=args.name,
        editors=editor_list,
        force=args.force,
        api_key_env=args.api_key_env,
        provider=args.provider,
        model=args.model,
        link_global_skills=not args.no_link,
    )
    print(f"Initialized AgentFlow in {cwd}")
    print(f"Created: {len(result['created'])}")
    print(f"Skipped: {len(result['skipped'])}")
    if result.get("editors_removed"):
        print(f"Cleared disabled editor folders: {', '.join(result['editors_removed'])}")
    link = result.get("link") or {}
    if link.get("method") == "absolute":
        print("Note: created absolute fallback for global skills (symlink unavailable).")
    elif link.get("method") in {"symlink", "junction"}:
        print(f"Linked global skill folder via {link['method']}.")
    return 0


def _init_is_bare(args: argparse.Namespace) -> bool:
    """True when ``flow init`` was invoked with no customization flags."""

    return (
        getattr(args, "name", None) is None
        and getattr(args, "editors", None) is None
        and not getattr(args, "force", False)
        and not getattr(args, "no_link", False)
    )


def _cmd_setup(args: argparse.Namespace, cwd: Path) -> int:
    result = run_quick_setup(
        cwd,
        project_name=args.name,
        force=args.force,
    )
    if result.get("cancelled"):
        if result.get("empty"):
            print("No agents selected -- nothing changed.")
        else:
            print("Setup cancelled.")
        return 1
    editors = result["editors"]
    init_result = result["init"]
    print(f"Initialized AgentFlow in {cwd}")
    print(f"Agents: {', '.join(editors)}")
    print(f"Created: {len(init_result['created'])}")
    print(f"Skipped: {len(init_result['skipped'])}")
    link = init_result.get("link") or {}
    if link.get("method") in {"symlink", "junction"}:
        print(f"Linked global skill folder via {link['method']}.")
    elif link.get("method") == "absolute":
        print("Note: created absolute fallback for global skills (symlink unavailable).")
    return 0


def _cmd_scan(args: argparse.Namespace, cwd: Path) -> int:
    print(to_json(scan_project(cwd)))
    return 0


def _cmd_state(args: argparse.Namespace, cwd: Path) -> int:
    if args.state_command == "set":
        blocked = None if args.blocked is None else args.blocked == "true"
        updated = update_state(
            cwd,
            phase=args.phase,
            current_goal=args.goal,
            active_change=args.change,
            next_action=args.next,
            blocked=blocked,
        )
        print("Updated state:")
        for key in ("phase", "current_goal", "active_change", "next_action", "blocked"):
            if key in updated:
                print(f"- {key}: {updated[key]}")
        return 0
    return 1


def _cmd_snapshot(args: argparse.Namespace, cwd: Path) -> int:
    blocked = None if args.blocked is None else args.blocked == "true"
    updated = update_state(
        cwd,
        phase=args.phase,
        current_goal=args.goal,
        active_change=args.change,
        next_action=args.next,
        blocked=blocked,
    )
    result = save_context(cwd, output=args.output)
    print("Updated state:")
    for key in ("phase", "current_goal", "active_change", "next_action", "blocked"):
        if key in updated:
            print(f"- {key}: {updated[key]}")
    print(f"Saved context: {result['path']}")
    print_clipboard_notice(copy_to_clipboard(result["content"]))
    return 0


def _cmd_changes(args: argparse.Namespace, cwd: Path) -> int:
    if args.changes_command == "new":
        result = create_change(
            cwd,
            title=args.title,
            summary=args.summary,
            change_id=args.id,
        )
        print(f"Created change: {result['id']}")
        print(f"Path: {result['path']}")
        return 0
    if args.changes_command == "list":
        changes = list_changes(cwd)
        if not changes:
            print("No change records found.")
            return 0
        for change in changes:
            summary = f" - {change['summary']}" if change["summary"] else ""
            print(f"- {change['id']}: {change['title']}{summary}")
        return 0
    if args.changes_command == "show":
        try:
            result = show_change(cwd, args.id)
        except FileNotFoundError as error:
            print(str(error))
            return 1
        print(result["content"], end="")
        return 0
    return 1


def _cmd_ask(args: argparse.Namespace, cwd: Path) -> int:
    advice = recommend_route(args.request, scan_project(cwd))
    print(f"Phase: {advice['phase']}")
    print(f"Recommended workflow: {advice['workflow']}")
    print(f"Recommended agent: {advice['recommended_agent']}")
    print(f"Implementation allowed: {str(advice['implementation_allowed']).lower()}")
    print(f"Required skills: {', '.join(advice['required_skills'])}")
    print(f"Next artifacts: {', '.join(advice['next_artifacts'])}")
    print(f"Reason: {advice['reason']}")
    print()
    print(
        "Next: flow handoff "
        f"{advice['recommended_agent']} \"{args.request}\""
    )
    return 0


def _cmd_handoff(args: argparse.Namespace, cwd: Path) -> int:
    prompt = render_handoff_prompt(cwd, args.platform, args.request)
    print(prompt, end="" if prompt.endswith("\n") else "\n")
    print_clipboard_notice(copy_to_clipboard(prompt))
    return 0


def _cmd_status(args: argparse.Namespace, cwd: Path) -> int:
    state_path = cwd / ".agentflow" / "state.yaml"
    if not state_path.exists():
        print("No .agentflow/state.yaml found. Run `flow init` first.")
        return 1
    print(state_path.read_text(encoding="utf-8"))
    return 0


def _cmd_doctor(args: argparse.Namespace, cwd: Path) -> int:
    report = doctor_project(cwd)
    label = "check" if args.command == "check" else "doctor"
    if report["ok"]:
        print(f"AgentFlow {label}: OK")
    else:
        print(f"AgentFlow {label}: missing files")
        for relative in report["missing"]:
            print(f"- {relative}")
    _print_diagnostics(cwd)
    return 0 if report["ok"] else 1


def _cmd_repair(args: argparse.Namespace, cwd: Path) -> int:
    plan = build_repair_plan(cwd, project_name=args.name)
    if args.dry_run:
        print("Repair plan:")
        if not plan.actions:
            print("- nothing to repair")
            return 0
        for action in plan.actions:
            print(f"- create {action.relative_path}")
        return 0
    result = apply_repair_plan(plan)
    print(f"Created: {len(result['created'])}")
    for relative in result["created"]:
        print(f"- {relative}")
    if result["skipped"]:
        print(f"Skipped: {len(result['skipped'])}")
    return 0


def _cmd_instructions(args: argparse.Namespace, cwd: Path) -> int:
    state_path = cwd / ".agentflow" / "state.yaml"
    if not state_path.exists():
        print("Project not initialized. Run `flow init` first.")
        return 1
    print(AGENT_INSTRUCTIONS)
    return 0


def _cmd_tools(args: argparse.Namespace, cwd: Path) -> int:
    tools = detect_tools()
    if args.json:
        print(
            json.dumps(
                {
                    "tools": [
                        {
                            "name": tool.name,
                            "display": tool.display,
                            "command": tool.command,
                            "status": tool.status,
                            "path": tool.path,
                        }
                        for tool in tools
                    ]
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print("Local AI coding tools:")
    for tool in tools:
        location = tool.path or "not found on PATH"
        print(f"- [{tool.status}] {tool.display} ({tool.command}): {location}")
    return 0


def _cmd_context(args: argparse.Namespace, cwd: Path) -> int:
    if args.context_command == "save":
        result = save_context(cwd, output=args.output)
        print(f"Saved context: {result['path']}")
        print_clipboard_notice(copy_to_clipboard(result["content"]))
        return 0
    return 1


def _cmd_npx(args: argparse.Namespace, cwd: Path) -> int:
    installed = install_npx_skill_command(args.args)
    sync_project_skill_index(cwd)
    _print_install_result(installed)
    return 0


def _cmd_skills(args: argparse.Namespace, cwd: Path) -> int:
    return _handle_skills_command(args, cwd)


def _cmd_editors(args: argparse.Namespace, cwd: Path) -> int:
    return _handle_editors_command(args, cwd)


def _cmd_projects(args: argparse.Namespace, cwd: Path) -> int:
    return _handle_projects_command(args, cwd)


# 子命令分发表：新增顶层命令时在此注册，并在 _build_parser 里加 parser。
COMMANDS = {
    "init": _cmd_init,
    "setup": _cmd_setup,
    "scan": _cmd_scan,
    "state": _cmd_state,
    "snapshot": _cmd_snapshot,
    "changes": _cmd_changes,
    "ask": _cmd_ask,
    "handoff": _cmd_handoff,
    "status": _cmd_status,
    "doctor": _cmd_doctor,
    "check": _cmd_doctor,
    "repair": _cmd_repair,
    "instructions": _cmd_instructions,
    "tools": _cmd_tools,
    "context": _cmd_context,
    "npx": _cmd_npx,
    "skills": _cmd_skills,
    "editors": _cmd_editors,
    "projects": _cmd_projects,
}


# -- Shared helpers -----------------------------------------------------------


def _print_diagnostics(cwd: Path) -> None:
    print()
    print("Local diagnostics:")
    current_section = ""
    for item in collect_diagnostics(cwd):
        if item.section != current_section:
            current_section = item.section
            print(f"{current_section}:")
        print(f"- [{item.status}] {item.name}: {item.message}")


def _handle_skills_command(args: argparse.Namespace, cwd: Path) -> int:
    if args.skills_command == "home":
        info = describe_skill_home()
        print(f"AgentFlow home: {info['home']}")
        print("Skill roots:")
        for root in info["skill_roots"]:
            print(f"- {root}")
        print(f"Installed skills: {len(info['skills'])}")
        return 0

    if args.skills_command == "bind":
        root = bind_skill_root(args.path)
        print(f"Bound global skill root: {root}")
        return 0

    if args.skills_command == "list":
        skills = discover_global_skills()
        if not skills:
            print("No global skills installed.")
            return 0
        for skill in skills:
            print(f"- {skill.name}: {skill.description}")
            print(f"  {skill.path}")
        return 0

    if args.skills_command == "import":
        skill = import_local_skill(args.path)
        sync_project_skill_index(cwd)
        _print_install_result(skill)
        return 0

    if args.skills_command == "install":
        skill = install_skill_source(args.source)
        sync_project_skill_index(cwd)
        _print_install_result(skill)
        return 0

    if args.skills_command == "npm":
        skill = install_npm_skill(args.package)
        sync_project_skill_index(cwd)
        _print_install_result(skill)
        return 0

    if args.skills_command == "gh":
        skill = install_github_skill(args.repo)
        sync_project_skill_index(cwd)
        _print_install_result(skill)
        return 0

    if args.skills_command == "zip":
        skill = import_zip_skill(args.path)
        sync_project_skill_index(cwd)
        _print_install_result(skill)
        return 0

    if args.skills_command == "npx":
        installed = install_npx_skill_command(args.args)
        sync_project_skill_index(cwd)
        _print_install_result(installed)
        return 0

    if args.skills_command == "all":
        installed = []
        for source in args.sources:
            installed.extend(install_all_skill_source(source))
        sync_project_skill_index(cwd)
        _print_install_result(installed)
        return 0

    if args.skills_command == "sync":
        result = sync_project_skill_index(cwd)
        print(f"Synced project index: {result['path']}")
        print(f"Global skills: {result['synced']}")
        return 0

    return 1


def _skill_list(installed) -> list:
    if isinstance(installed, list):
        return installed
    return [installed]


def _print_install_result(installed) -> None:
    skills = _skill_list(installed)
    if len(skills) == 1:
        print(f"Installed skill: {skills[0].name}")
    else:
        print(f"Installed skills: {len(skills)}")
    for skill in skills:
        print(f"- {skill.name}: {skill.path.parent}")
    print("Synced project index: .agentflow/skills/SKILL.md")


def _handle_editors_command(args: argparse.Namespace, cwd: Path) -> int:
    from .editors import (
        all_editors,
        add_custom_editor,
        apply_editors,
        disable_editor,
        enable_editor,
        get_enabled_editors,
        remove_custom_editor,
    )

    if args.editors_command == "list":
        catalog = all_editors()
        enabled = {spec.name for spec in get_enabled_editors()}
        for name in sorted(catalog):
            spec = catalog[name]
            mark = "[x]" if name in enabled else "[ ]"
            tag = " (custom)" if spec.custom else ""
            print(f"{mark} {name:<14}{tag} -> {spec.entrypoint}")
        if not catalog:
            print("No editors known. Run `flow editors add-custom` to register one.")
        return 0

    if args.editors_command == "add":
        spec = enable_editor(args.name)
        apply_editors(cwd)
        print(f"Enabled editor: {spec.name} -> {spec.entrypoint}")
        return 0

    if args.editors_command == "remove":
        disable_editor(args.name)
        result = apply_editors(cwd)
        print(f"Disabled editor: {args.name}")
        if result["removed"]:
            print(f"Removed folders: {', '.join(result['removed'])}")
        return 0

    if args.editors_command == "add-custom":
        spec = add_custom_editor(args.name, args.path, display=args.display)
        apply_editors(cwd)
        print(f"Added custom editor: {spec.name} -> {spec.entrypoint}")
        return 0

    if args.editors_command == "remove-custom":
        remove_custom_editor(args.name)
        result = apply_editors(cwd)
        print(f"Removed custom editor: {args.name}")
        if result["removed"]:
            print(f"Removed folders: {', '.join(result['removed'])}")
        return 0

    if args.editors_command == "apply":
        result = apply_editors(cwd, force=args.force)
        print(f"Created:  {len(result['created'])}")
        print(f"Kept:     {len(result['kept'])}")
        print(f"Removed:  {len(result['removed'])}")
        return 0

    return 1


def _handle_projects_command(args: argparse.Namespace, cwd: Path) -> int:
    from .projects import (
        list_projects,
        register_project,
        sync_all_projects,
        unregister_project,
    )

    if args.projects_command == "list":
        entries = list_projects()
        if not entries:
            print("No projects registered.")
            return 0
        for entry in entries:
            print(f"- {entry.name}: {entry.path}")
        return 0

    if args.projects_command == "register":
        entry = register_project(cwd, name=args.name)
        print(f"Registered project: {entry.name} -> {entry.path}")
        return 0

    if args.projects_command == "unregister":
        if unregister_project(args.name):
            print(f"Unregistered: {args.name}")
            return 0
        print(f"No project registered as: {args.name}")
        return 1

    if args.projects_command == "sync-all":
        result = sync_all_projects()
        for entry in result["results"]:
            print(f"- {entry['name']} ({entry['link']['method']}): {entry['synced']} skills")
        if result["skipped"]:
            print(f"Skipped (no .agentflow): {', '.join(result['skipped'])}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
