"""交互式工作台（``flow`` 无参数时进入）。"""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .core import doctor_project, init_project
from .diagnostics import detect_tools
from .templates import AGENT_INSTRUCTIONS

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.history import InMemoryHistory
except ImportError:  # pragma: no cover
    PromptSession = None
    WordCompleter = None
    InMemoryHistory = None

console = Console()

SLASH_COMMANDS = ["/init", "/check", "/doctor", "/tools", "/instructions", "/help", "/quit"]


def run_repl(project_dir: str | Path | None = None) -> int:
    root = Path(project_dir or Path.cwd())
    _print_banner(root)
    session = _make_session()

    while True:
        try:
            line = _read_prompt(session).strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            console.print("[dim]Bye.[/]")
            return 0

        if not line:
            continue

        if line == "1":
            _run_init(root)
            continue
        if line == "2":
            _print_check(root)
            continue
        if line == "3":
            _print_instructions(root)
            continue
        if line in {"0", "/quit", "/exit", "/q"}:
            console.print("[dim]Bye.[/]")
            return 0

        if line == "/help":
            _print_help()
            continue
        if line in {"/check", "/doctor"}:
            _print_check(root)
            continue
        if line == "/init":
            _run_init(root)
            continue
        if line == "/tools":
            _print_tools()
            continue
        if line == "/instructions":
            _print_instructions(root)
            continue

        console.print(f"[yellow]Unknown command:[/] {line}")
        console.print("[dim]Try /help[/]")


def _make_session():
    if PromptSession is None or not sys.stdin.isatty() or not sys.stdout.isatty():
        return None
    return PromptSession(
        history=InMemoryHistory() if InMemoryHistory else None,
        completer=WordCompleter(SLASH_COMMANDS, ignore_case=True) if WordCompleter else None,
        complete_while_typing=True,
    )


def _read_prompt(session) -> str:
    if session is not None:
        return session.prompt("flow > ")
    return console.input("flow > ")


def _print_banner(root: Path) -> None:
    report = doctor_project(root)
    initialized = (root / ".agentflow" / "AGENTS.md").exists()
    phase = "ready" if report["ok"] else ("initialized" if initialized else "not initialized")
    console.print(
        Panel(
            f"Project: [bold]{root}[/]\n"
            f"Status: [bold]{phase}[/]\n"
            f"Missing: [bold]{len(report['missing'])}[/]",
            title="[bold cyan]Flow — 项目规范初始化器[/]",
            border_style="cyan",
        )
    )
    console.print("[dim]Shortcuts: [1] init  [2] check  [3] instructions  [0] quit[/]")
    console.print("[dim]Commands: /init  /check  /tools  /instructions  /help[/]\n")


def _print_help() -> None:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Command")
    table.add_column("Description")
    table.add_row("/init", "生成 .agentflow/ 规范文档骨架")
    table.add_row("/check", "检查规范文件是否齐全")
    table.add_row("/tools", "检测本机 AI 编码工具")
    table.add_row("/instructions", "打印 agent 工作说明")
    table.add_row("/quit", "退出")
    console.print(table)


def _run_init(root: Path) -> None:
    result = init_project(root)
    console.print(
        Panel(
            f"Created: [bold]{len(result['created'])}[/]\n"
            f"Skipped: [dim]{len(result['skipped'])}[/]",
            title="[green]Init complete[/]",
            border_style="green",
        )
    )


def _print_check(root: Path) -> None:
    report = doctor_project(root)
    if report["ok"]:
        console.print("[green]Check: OK — all required files present[/]")
        return
    console.print("[yellow]Check: missing files[/]")
    for path in report["missing"]:
        console.print(f"  - {path}")


def _print_tools() -> None:
    for tool in detect_tools():
        status = "[green]ok[/]" if tool.status == "ok" else "[yellow]missing[/]"
        console.print(f"{status} {tool.display} ({tool.path or 'not on PATH'})")


def _print_instructions(root: Path) -> None:
    if not (root / ".agentflow" / "AGENTS.md").exists():
        console.print("[yellow]Not initialized. Run /init first.[/]")
        return
    console.print(Panel(AGENT_INSTRUCTIONS.strip(), title="Instructions", border_style="cyan"))
