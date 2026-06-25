"""命令行入口：``flow init`` / ``flow check`` / ``flow editors`` 等。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import doctor_project, init_project
from .diagnostics import collect_diagnostics, detect_tools
from .editors import normalize_editor_names
from .init_ui import pick_editors
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flow",
        description="Initialize strict project specification docs for AI coding tools.",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"flow {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create .agentflow specification skeleton.")
    init_parser.add_argument(
        "editor_names",
        nargs="*",
        metavar="editor",
        help="Editors to enable, e.g. flow init cursor claude",
    )
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    init_parser.add_argument(
        "--editors",
        default=None,
        help="Comma-separated editors (same as positional names).",
    )
    init_parser.add_argument(
        "--skeleton-only",
        action="store_true",
        help="Only create .agentflow/; do not generate any thin entrypoints.",
    )

    subparsers.add_parser("check", help="Check specification skeleton files.")
    subparsers.add_parser("doctor", help="Alias for check.")
    subparsers.add_parser("instructions", help="Show agent instructions summary.")
    tools_parser = subparsers.add_parser("tools", help="Show local AI coding tool availability.")
    tools_parser.add_argument("--json", action="store_true")

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

    return parser


def _cmd_init(args: argparse.Namespace, cwd: Path) -> int:
    try:
        editor_list = _resolve_init_editors(args)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    result = init_project(cwd, editors=editor_list, force=args.force)
    print(f"Initialized specification skeleton in {cwd}")
    if editor_list:
        print(f"Editors: {', '.join(editor_list)}")
    else:
        print("Editors: (none — .agentflow/ skeleton only)")
    print(f"Created: {len(result['created'])}")
    print(f"Skipped: {len(result['skipped'])}")
    if result.get("editors_removed"):
        print(f"Removed disabled editor entrypoints: {', '.join(result['editors_removed'])}")
    return 0


def _resolve_init_editors(args: argparse.Namespace) -> list[str]:
    if args.skeleton_only:
        return []
    if args.editor_names:
        return normalize_editor_names(args.editor_names)
    if args.editors is not None:
        return normalize_editor_names(
            [item.strip() for item in args.editors.split(",") if item.strip()]
        )
    return pick_editors()


def _cmd_check(args: argparse.Namespace, cwd: Path) -> int:
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


def _cmd_instructions(args: argparse.Namespace, cwd: Path) -> int:
    if not (cwd / ".agentflow" / "AGENTS.md").exists():
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


def _cmd_editors(args: argparse.Namespace, cwd: Path) -> int:
    return _handle_editors_command(args, cwd)


COMMANDS = {
    "init": _cmd_init,
    "check": _cmd_check,
    "doctor": _cmd_check,
    "instructions": _cmd_instructions,
    "tools": _cmd_tools,
    "editors": _cmd_editors,
}


def _print_diagnostics(cwd: Path) -> None:
    print()
    print("Local diagnostics:")
    current_section = ""
    for item in collect_diagnostics(cwd):
        if item.section != current_section:
            current_section = item.section
            print(f"{current_section}:")
        print(f"- [{item.status}] {item.name}: {item.message}")


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
            print(f"Removed entrypoints: {', '.join(result['removed'])}")
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
            print(f"Removed entrypoints: {', '.join(result['removed'])}")
        return 0

    if args.editors_command == "apply":
        result = apply_editors(cwd, force=args.force)
        print(f"Created:  {len(result['created'])}")
        print(f"Kept:     {len(result['kept'])}")
        print(f"Removed:  {len(result['removed'])}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
