"""Interactive shell for AgentFlow — offline project preparation workbench."""

from __future__ import annotations

import difflib
import shlex
import sys
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style
except ImportError:  # pragma: no cover - dependency fallback for broken installs
    PromptSession = None
    WordCompleter = None
    InMemoryHistory = None
    Style = None

from .core import (
    doctor_project,
    init_project,
    recommend_route,
    render_handoff_prompt,
    scan_project,
    to_json,
)
from .context import save_context
from .changes import create_change, list_changes, show_change
from .diagnostics import detect_tools
from .repair import apply_repair_plan, build_repair_plan
from .state import update_state
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
    sync_project_skill_index,
)
from .templates import AGENT_INSTRUCTIONS
# -- Premium Colour Palette ---------------------------------------------------

ACCENT = "bold #06b6d4"       # Glowing Cyan
DIM = "dim #94a3b8"          # Slate Gray
OK = "bold #10b981"          # Emerald Green
WARN = "bold #f59e0b"        # Amber
ERR = "bold #ef4444"         # Rose Red
MUTED = "#475569"            # Dark Blue Slate


# -- GBK Safe Character Fallbacks ---------------------------------------------
import sys

def _is_utf8() -> bool:
    try:
        enc = (sys.stdout.encoding or "utf-8").lower()
        return "utf" in enc
    except Exception:
        return True

IS_UTF8 = _is_utf8()

STAR = "✦" if IS_UTF8 else "*"
ARROW = "❯" if IS_UTF8 else ">"
LIGHTNING = "⚡" if IS_UTF8 else "P"
DOCTOR = "🩺" if IS_UTF8 else "D"
ROCKET = "🚀" if IS_UTF8 else "S"
PAPER = "📄" if IS_UTF8 else "R"
DOOR = "🚪" if IS_UTF8 else "E"
GEAR = "⚙️" if IS_UTF8 else "S"
BOX = "📦" if IS_UTF8 else "K"
GLASS = "🔍" if IS_UTF8 else "H"
FOLDER = "📁" if IS_UTF8 else " "
IDEA = "💡" if IS_UTF8 else "i"

GREEN_DOT = "🟢" if IS_UTF8 else "[OK]"
YELLOW_DOT = "🟡" if IS_UTF8 else "[WARN]"
RED_DOT = "🔴" if IS_UTF8 else "[ERR]"

TICK = "✔" if IS_UTF8 else "v"
CROSS = "✘" if IS_UTF8 else "x"

BLOCK_FULL = "■" if IS_UTF8 else "*"
BLOCK_EMPTY = "□" if IS_UTF8 else "-"


# -- Static data --------------------------------------------------------------

COMMAND_TABLE_DATA = [
    ("/init [name]", "Initialize AI coding framework"),
    ("/check", "Health check (alias: /doctor)"),
    ("/doctor", "Same as /check (legacy name)"),
    ("/tools", "Show local AI coding tools"),
    ("/repair", "Restore missing AgentFlow files"),
    ("/context", "Save a no-API handoff snapshot"),
    ("/instructions", "Show universal agent instructions"),
    ("/editors", "Toggle which editors get an entrypoint"),
    ("/register", "Register this project for batch sync"),
    ("/sync-all", "Re-link & refresh every registered project"),
    ("/skills", "List global skills"),
    ("/skills all", "Batch install multiple skills or all skills from a source"),
    ("/sync", "Sync global skills into this project"),
    ("/npm <package>", "Install a global skill from npm"),
    ("/npx skills add <src> --skill <name>|--all", "Install from an npx skills command"),
    ("/gh <owner/repo>", "Install a global skill from GitHub"),
    ("/local <path>", "Import a local skill folder"),
    ("/zip <path>", "Import a zipped skill package"),
    ("/home", "Show global skill home"),
    ("/status", "Show current state"),
    ("/state", "Update current phase, goal, or next action"),
    ("/snapshot", "Update state and save context"),
    ("/change", "Create a local change record"),
    ("/changes", "List local change records"),
    ("/change-show <id>", "Show a local change record"),
    ("/scan", "Detect project signals"),
    ("/ask <request>", "Template helper: recommend workflow"),
    ("/handoff <agent> <req>", "Template helper: generate handoff prompt"),
    ("/help", "Show commands"),
    ("/quit", "Exit"),
]

SLASH_COMMANDS = [command.split()[0] for command, _ in COMMAND_TABLE_DATA]


def _get_ascii_logo() -> Text:
    """Return a stylized gradient ASCII art brand banner."""
    logo_lines = [
        "    ___                 __  ______               ",
        "   /   |  ____ ____  __/ /_/ ____/____ _      __ ",
        "  / /| | / __ `/ _ \\/ __  / /_   / __ `/ | /| / / ",
        " / ___ |/ /_/ /  __/ /_/ / __/  / /_/ /| |/ |/ /  ",
        "/_/  |_|\\__, /\\___/\\__,_/_/     \\__,_/ |__/|__/   ",
        "       /____/                                     "
    ]
    colors = ["#6366f1", "#6366f1", "#6366f1", "#8b5cf6", "#8b5cf6", "#8b5cf6"]
    res = Text()
    for line, color in zip(logo_lines, colors):
        res.append(line + "\n", style=color)
    return res


def _make_console() -> Console:
    """Create a Console that works safely on Windows with GBK locale."""
    return Console(legacy_windows=False)


console = _make_console()


def _make_prompt_session():
    """Create a Claude Code-like prompt when running in a real terminal."""
    if PromptSession is None or not sys.stdin.isatty():
        return None

    completer = WordCompleter(
        SLASH_COMMANDS,
        ignore_case=True,
        sentence=True,
        match_middle=False,
    )
    if Style is not None:
        style = Style.from_dict({
            "prompt": "bold #06b6d4",
            "completion-menu": "bg:#0f172a fg:#cbd5e1",
            "completion-menu.completion": "bg:#1e293b fg:#94a3b8",
            "completion-menu.completion.current": "bg:#4f46e5 fg:#ffffff bold",
            "scrollbar.background": "bg:#0f172a",
            "scrollbar.button": "bg:#475569",
        })
    else:
        style = None

    return PromptSession(
        history=InMemoryHistory() if InMemoryHistory else None,
        completer=completer,
        complete_while_typing=True,
        style=style,
    )


def _command_box_width() -> int:
    """Match the prompt rules to the current terminal without making them tiny."""
    terminal_width = console.width or 80
    return max(48, terminal_width - 2)


def _rule_chars() -> tuple[str, str]:
    """Pick rule chars that render safely on the current terminal."""
    if sys.stdout.isatty():
        return "─", " "
    return "-", " "


def _status_footer_text(root: Path) -> tuple[str, str]:
    """Build the Claude-Code-style status footer (left text, right text)."""
    report = doctor_project(root)
    phase = _read_phase(root)
    try:
        n_skills = len(discover_global_skills())
    except Exception:
        n_skills = 0
    n_missing = len(report["missing"])

    if phase == "not initialized":
        left = f" {STAR} [bold #ef4444]not initialized[/]  [dim #94a3b8](run /init to setup your workflow)[/]"
    elif not report["ok"]:
        left = f" {STAR} [bold #f59e0b]needs attention[/]  [dim #94a3b8](run /doctor to inspect missing files)[/]"
    else:
        left = f" {STAR} [bold #10b981]ready[/]  [dim #94a3b8](type /help to list commands, or type a task)[/]"

    skill_word = "skill" if n_skills == 1 else "skills"
    if n_missing == 0:
        right = f"[bold #10b981]healthy[/] | [bold #a5b4fc]{n_skills}[/] {skill_word} "
    else:
        right = f"[bold #f59e0b]{n_missing} missing[/] | [bold #a5b4fc]{n_skills}[/] {skill_word} "
    return left, right


def _print_status_footer(root: Path) -> None:
    """Print a dim two-column status line right under the input frame."""
    left, right = _status_footer_text(root)
    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_row(left, right)
    console.print(grid)


def _read_prompt(session, root: Path) -> str:
    """Render a Claude-Code-style framed input area and return user input."""
    rule_char, _ = _rule_chars()
    width = _command_box_width()
    rule = rule_char * width
    placeholder = 'Try "/help" or type a task'

    # Top rule
    console.print(f"[#334155]{rule}[/]")

    # Input line
    if session is not None:
        try:
            user_input = session.prompt(
                [("class:prompt", f"{STAR} flow {ARROW} ")],
                placeholder=placeholder,
            )
        finally:
            console.print(f"[#334155]{rule}[/]")
            _print_status_footer(root)
        return user_input

    try:
        # Use simple '> ' prompt in non-TTY/redirected test environments to satisfy test runner assertions
        prompt_str = "> " if not sys.stdin.isatty() else f"[bold #06b6d4]{STAR} flow {ARROW} [/]"
        return console.input(prompt_str)
    finally:
        if not sys.stdin.isatty():
            console.print()
        console.print(f"[#334155]{rule}[/]")
        _print_status_footer(root)


# -- Public entry point -------------------------------------------------------

def run_repl(project_dir: str | Path | None = None) -> int:
    """Run the AgentFlow interactive shell."""

    root = Path(project_dir or Path.cwd())
    session = _make_prompt_session()
    _print_banner(root)

    while True:
        try:
            raw = _read_prompt(session, root)
        except (EOFError, KeyboardInterrupt):
            console.print()
            _print_bye()
            return 0

        line = raw.strip()
        if not line:
            continue

        # Number-driven wizard
        if line == "1":
            _wizard_setup(root)
            continue
        if line == "2":
            _wizard_doctor(root)
            continue
        if line == "3":
            _wizard_instructions(root)
            continue
        if line == "0":
            _print_bye()
            return 0

        shortcut = _normalize_shortcut(line)
        if shortcut:
            line = shortcut
        elif not line.startswith("/"):
            line = "/ask " + line

        # Slash commands for power users
        should_exit = _handle_command(root, line)
        if should_exit:
            _print_bye()
            return 0


# -- Banner / dashboard -------------------------------------------------------

def _print_banner(root: Path) -> None:
    from rich import box
    report = doctor_project(root)
    phase = _read_phase(root)
    doctor_ok = report["ok"]

    # 1. Print gorgeous brand header & sub-banner
    console.print()
    console.print(_get_ascii_logo())
    console.print(f"  [dim #94a3b8]{STAR} AgentFlow AI Coding Workbench v0.3.1 | Offline Preparation Hub {STAR}[/]")
    console.print(f"  [dim #94a3b8]{STAR} Try \"/help\" or type a task to get started {STAR}[/]")
    console.print()

    # 2. Build the System Status Table
    status_table = Table.grid(padding=(0, 2))
    status_table.add_column(style="dim #94a3b8", justify="left", min_width=12)
    status_table.add_column(style="bold")

    status_table.add_row("  Project", f"[bold white]{root}[/]")

    phase_colors = {
        "initialized": "bold #10b981",
        "not initialized": "bold #ef4444",
        "brainstorm": "bold #a855f7",
        "spec": "bold #f59e0b",
        "plan": "bold #06b6d4",
        "implement": "bold #3b82f6",
        "verify": "bold #eab308",
        "finish": "bold #10b981",
    }
    phase_style = phase_colors.get(phase.lower(), "bold #a855f7")
    status_table.add_row("  Phase", f"[{phase_style}]{phase}[/]")

    if doctor_ok:
        status_table.add_row("  Doctor", f"[bold #10b981]{GREEN_DOT} OK[/]")
    else:
        n = len(report["missing"])
        status_table.add_row("  Doctor", f"[bold #f59e0b]{YELLOW_DOT} {n} missing file{'s' if n != 1 else ''}[/]")

    # Installed skills visual indicator
    try:
        skills_count = len(discover_global_skills())
    except Exception:
        skills_count = 0
    bar_len = min(10, skills_count)
    rem_len = max(0, 10 - bar_len)
    skills_bar = f"[#a5b4fc]{BLOCK_FULL * bar_len}[/][#334155]{BLOCK_EMPTY * rem_len}[/]"
    status_table.add_row("  Skills", f"[bold #a5b4fc]{skills_count} global[/]  {skills_bar}")

    status_panel = Panel(
        status_table,
        title=f"[bold #6366f1]{STAR} System Status {STAR}[/]",
        title_align="left",
        border_style="#475569",
        padding=(1, 2),
        expand=True,
    )

    # 3. Build the Navigation Wizard Table
    help_table = Table.grid(padding=(0, 2))
    help_table.add_column(style="bold #6366f1", justify="right", min_width=4)
    help_table.add_column(style="bold white")

    help_table.add_row("1", "Setup Project")
    help_table.add_row("2", "Doctor Health")
    help_table.add_row("3", "Handoff Rules")
    help_table.add_row("0", "Exit Workbench")

    help_panel = Panel(
        help_table,
        title=f"[bold #6366f1]{STAR} Quick Wizard {STAR}[/]",
        title_align="left",
        border_style="#475569",
        padding=(1, 2),
        expand=True,
    )

    # 4. Display Side-by-Side or Stacked based on console width
    width = console.width or 80
    if width >= 75:
        layout_table = Table.grid(expand=True, padding=(0, 2))
        layout_table.add_column(ratio=6)
        layout_table.add_column(ratio=4)
        layout_table.add_row(status_panel, help_panel)
        console.print(layout_table)
    else:
        console.print(status_panel)
        console.print(help_panel)

    console.print()

    # 5. Print gorgeous highlighted pills/badges
    hint_text = Text()
    hint_text.append(f"  {STAR} Quick Commands: ", style="dim #94a3b8")
    hint_parts = ["/init", "/doctor", "/skills", "/sync", "/npm", "/npx", "/local", "/instructions", "/help"]
    for index, part in enumerate(hint_parts):
        if index:
            hint_text.append(" ")
        hint_text.append(f" {part} ", style="bold #a5b4fc on #1e293b")
    console.print(hint_text)
    console.print()


def _skill_summary() -> str:
    try:
        count = len(discover_global_skills())
    except Exception:
        return f"[bold #f59e0b]unavailable[/]"
    label = "skill" if count == 1 else "skills"
    return f"[bold #06b6d4]{count} global {label}[/]"


def _print_wizard_menu(initialized: bool) -> None:
    """Show the numbered quick-action menu."""
    from rich import box
    table = Table(
        show_header=False,
        show_edge=False,
        box=None,
        padding=(0, 2),
    )
    table.add_column(style="bold #8b5cf6", width=6, justify="right")
    table.add_column()

    if not initialized:
        table.add_row(" [1]", f"[bold white]Setup project[/]         [bold #a5b4fc on #1e293b] Start Here [/]")
        table.add_row(" [2]", "[dim #94a3b8]Check Health[/]")
        table.add_row(" [3]", "[dim #94a3b8]Show Handoff Rules[/]")
    else:
        table.add_row(" [1]", "[dim #94a3b8]Setup project (Initialized)[/]")
        table.add_row(" [2]", f"[bold white]Check Health[/]         [bold #10b981 on #1e293b] Recommended [/]")
        table.add_row(" [3]", f"[bold white]Show Handoff Rules[/]   [bold #a5b4fc on #1e293b] Active [/]")

    table.add_row(" [0]", "[bold #ef4444]Exit Workbench[/]")

    console.print(Panel(
        table,
        title=f"[bold #6366f1]{STAR} Navigation Wizard {STAR}[/]",
        title_align="left",
        border_style="#475569",
        padding=(1, 2),
    ))

    console.print(f"  [dim #94a3b8]{STAR} Tip: Type [bold #a5b4fc]/help[/] in the command prompt to view all slash commands.[/]")



def _print_bye() -> None:
    console.print(f"[{DIM}]Bye.[/{DIM}]")


# -- Wizard flows -------------------------------------------------------------

def _wizard_setup(root: Path) -> None:
    """Guided project initialization."""
    try:
        name = console.input(f"  [{ACCENT}]Project name[/] [{DIM}]({root.name})[/]: ").strip()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return

    if not name:
        name = root.name

    result = init_project(root, project_name=name)
    console.print()
    console.print(Panel(
        f"[{OK}]Initialized AgentFlow in {root}[/]\n"
        f"Created: [bold]{len(result['created'])}[/]  "
        f"Skipped: [{MUTED}]{len(result['skipped'])}[/]",
        title="[bold]Setup Complete[/]",
        title_align="left",
        border_style=OK,
        padding=(1, 2),
    ))

    # Show doctor result
    report = doctor_project(root)
    if report["ok"]:
        console.print(f"  [{OK}]Doctor: OK[/]")
    else:
        n = len(report["missing"])
        console.print(f"  [{WARN}]Doctor: {n} file{'s' if n != 1 else ''} still missing[/]")
    console.print()


def _wizard_doctor(root: Path) -> None:
    """Guided setup check."""
    _print_doctor(root)


def _wizard_instructions(root: Path) -> None:
    """Show universal agent instructions."""
    state_path = root / ".agentflow" / "state.yaml"
    if not state_path.exists():
        console.print(f"  [{WARN}]Project not initialized. Run /init or press 1 first.[/]")
        console.print()
        return

    console.print(Panel(
        AGENT_INSTRUCTIONS.rstrip(),
        title="[bold]Agent Instructions[/]",
        title_align="left",
        subtitle="[dim]Copy the text above into any AI coding tool[/]",
        subtitle_align="left",
        border_style=ACCENT,
        padding=(1, 2),
    ))
    console.print()


# -- Command rendering --------------------------------------------------------

def _print_commands() -> None:
    from rich import box
    
    categories = {
        f"{GEAR} Setup & Diagnostics": [
            ("/init [name]", "Initialize AI coding framework"),
            ("/doctor", "Check project configuration"),
            ("/tools", "Show local AI coding tools"),
            ("/repair", "Restore missing AgentFlow files"),
            ("/context", "Save a no-API handoff snapshot"),
            ("/instructions", "Show universal agent instructions"),
            ("/editors", "Toggle which editors get an entrypoint"),
            ("/status", "Show current state"),
            ("/state <phase> <goal>", "Update current phase and goal"),
            ("/snapshot <phase> <goal>", "Update state and save context"),
            ("/change <title>", "Create a local change record"),
            ("/changes", "List local change records"),
            ("/change-show <id>", "Show a local change record"),
            ("/scan", "Detect project signals"),
        ],
        f"{BOX} Skill Management": [
            ("/skills", "List global skills"),
            ("/skills all", "Batch install multiple skills/sources"),
            ("/sync", "Sync global skills into this project"),
            ("/home", "Show global skill home"),
            ("/npm <package>", "Install a skill from npm"),
            ("/npx skills add ...", "Install from npx skills command"),
            ("/gh <owner/repo>", "Install from GitHub repo"),
            ("/local <path>", "Import a local skill folder"),
            ("/zip <path>", "Import a zipped skill package"),
        ],
        f"{ROCKET} Project Registry": [
            ("/register", "Register project for batch sync"),
            ("/sync-all", "Refresh every registered project"),
        ],
        f"{GLASS} Autopilot Helpers": [
            ("/ask <request>", "Recommend a tailored workflow"),
            ("/handoff <agent> <req>", "Generate agent handoff prompt"),
        ],
        f"{DOOR} System Commands": [
            ("/help", "Show this commands catalog"),
            ("/quit", "Exit AgentFlow workbench"),
        ]
    }
    
    table = Table(
        show_header=True,
        header_style="bold #06b6d4",
        box=box.ROUNDED,
        border_style="#0891b2",
        expand=True,
    )
    table.add_column("Category", style="bold #8b5cf6", width=22)
    table.add_column("Command", style="bold #06b6d4", width=34)
    table.add_column("Description", style="dim #94a3b8")
    
    for idx, (cat, items) in enumerate(categories.items()):
        for item_idx, (cmd, desc) in enumerate(items):
            cat_name = cat if item_idx == 0 else ""
            table.add_row(cat_name, cmd, desc)
        if idx < len(categories) - 1:
            table.add_section()

    console.print(Panel(
        table,
        title=f"[bold #06b6d4]{STAR} Command Catalog {STAR}[/]",
        title_align="left",
        border_style="#0891b2",
        padding=(1, 2),
    ))


def _print_help() -> None:
    _print_commands()

    shortcuts = Text()
    shortcuts.append(f"  {STAR} Quick Shortcuts: ", style="bold dim #94a3b8")
    
    shortcuts.append(" [1] Setup ", style="bold #a855f7 on #1e293b")
    shortcuts.append(" ")
    shortcuts.append(" [2] Check ", style="bold #10b981 on #1e293b")
    shortcuts.append(" ")
    shortcuts.append(" [3] Rules ", style="bold #06b6d4 on #1e293b")
    shortcuts.append(" ")
    shortcuts.append(" [0] Exit ", style="bold #ef4444 on #1e293b")

    console.print(shortcuts)
    console.print()


def _print_menu() -> None:
    initialized = _read_phase(Path.cwd()) != "not initialized"
    _print_wizard_menu(initialized)


# -- Command dispatcher -------------------------------------------------------

def _handle_command(root: Path, line: str) -> bool:
    try:
        parts = shlex.split(line, posix=False)
    except ValueError as exc:
        console.print(f"[{ERR}]Parse error:[/] {exc}")
        return False

    if not parts:
        return False

    command = parts[0].lower()
    args = parts[1:]

    if command in {"/quit", "/exit", "/q"}:
        return True

    if command == "/help":
        _print_help()
        return False

    if command == "/menu":
        _print_menu()
        return False

    if command == "/init":
        name = " ".join(args) if args else root.name
        result = init_project(root, project_name=name)
        console.print(Panel(
            f"[{OK}]Initialized AgentFlow in {root}[/]\n"
            f"Created: [bold]{len(result['created'])}[/]  "
            f"Skipped: [{MUTED}]{len(result['skipped'])}[/]",
            title="[bold]Init[/]",
            title_align="left",
            border_style=OK,
            padding=(1, 2),
        ))
        return False

    if command == "/instructions":
        _wizard_instructions(root)
        return False

    if command == "/tools":
        table = Table(show_header=True, header_style="bold", expand=False)
        table.add_column("Tool", style=f"bold {ACCENT}")
        table.add_column("Status")
        table.add_column("Command")
        table.add_column("Path", style=DIM)
        for tool in detect_tools():
            status = f"[{OK}]ok[/]" if tool.status == "ok" else f"[{WARN}]missing[/]"
            table.add_row(tool.display, status, tool.command, tool.path or "not found on PATH")
        console.print(Panel(
            table,
            title="[bold]Local Tools[/]",
            title_align="left",
            border_style=ACCENT,
            padding=(1, 2),
        ))
        return False

    if command == "/repair":
        dry_run = "--dry-run" in args
        plan = build_repair_plan(root)
        if dry_run:
            if not plan.actions:
                console.print(f"[{OK}]Nothing to repair.[/]")
                return False
            console.print("[bold]Repair plan[/]")
            for action in plan.actions:
                console.print(f"  [{ACCENT}]create[/] {action.relative_path}")
            return False
        result = apply_repair_plan(plan)
        console.print(f"[{OK}]Created:[/] {len(result['created'])}")
        for relative in result["created"]:
            console.print(f"  - {relative}")
        return False

    if command == "/context":
        output = args[0] if args else None
        result = save_context(root, output=output)
        console.print(f"[{OK}]Saved context:[/] {result['path']}")
        return False

    if command == "/editors":
        _editors_wizard()
        return False

    if command == "/register":
        _register_project(root)
        return False

    if command == "/sync-all":
        _sync_all_projects()
        return False

    if command == "/home":
        _print_skill_home()
        return False

    if command == "/skills":
        if args and args[0].lower() == "all":
            if len(args) > 1:
                _install_all_sources(root, args[1:])
            else:
                _batch_install_skills(root)
            return False
        _print_global_skills()
        return False

    if command == "/sync":
        _sync_skills(root)
        return False

    if command == "/bind":
        if not args:
            console.print(f"[{WARN}]Usage:[/] bind <skill-root>")
            return False
        root_path = bind_skill_root(args[0])
        console.print(f"[{OK}]Bound global skill root:[/] {root_path}")
        return False

    if command == "/local":
        if not args:
            console.print(f"[{WARN}]Usage:[/] local <path>")
            return False
        _install_skill(root, import_local_skill, args[0])
        return False

    if command == "/zip":
        if not args:
            console.print(f"[{WARN}]Usage:[/] zip <path>")
            return False
        _install_skill(root, import_zip_skill, args[0])
        return False

    if command == "/npm":
        if not args:
            console.print(f"[{WARN}]Usage:[/] npm <package>")
            return False
        _install_skill(root, install_npm_skill, args[0])
        return False

    if command == "/npx":
        if not args:
            console.print(f"[{WARN}]Usage:[/] npx skills add <source> (--skill <name> | --all)")
            return False
        _install_skill_from_args(root, install_npx_skill_command, args)
        return False

    if command in {"/gh", "/github"}:
        if not args:
            console.print(f"[{WARN}]Usage:[/] gh <owner/repo[/path]>")
            return False
        _install_skill(root, install_github_skill, args[0])
        return False

    if command == "/scan":
        console.print(Panel(
            to_json(scan_project(root)),
            title="[bold]Scan Results[/]",
            title_align="left",
            border_style=ACCENT,
            padding=(1, 2),
        ))
        return False

    if command == "/ask":
        request = " ".join(args).strip()
        if not request:
            console.print(f"[{WARN}]Usage:[/] /ask <request>")
            return False
        _print_advice(request, root)
        return False

    if command == "/handoff":
        if len(args) < 2:
            console.print(f"[{WARN}]Usage:[/] /handoff <codex|cursor|claude|kiro|qoder> <request>")
            return False
        platform = args[0]
        request = " ".join(args[1:])
        prompt = render_handoff_prompt(root, platform, request)
        console.print(Panel(
            prompt.rstrip(),
            title=f"[bold]Handoff -> {platform.title()}[/]",
            title_align="left",
            subtitle="[dim]Copy the content above into your AI coding tool[/]",
            subtitle_align="left",
            border_style="bright_magenta",
            padding=(1, 2),
        ))
        return False

    if command == "/status":
        state_path = root / ".agentflow" / "state.yaml"
        if not state_path.exists():
            console.print(f"[{WARN}]No .agentflow/state.yaml found. Run /init first.[/]")
            return False
        content = state_path.read_text(encoding="utf-8")
        console.print(Panel(
            content.rstrip(),
            title="[bold]State[/]",
            title_align="left",
            border_style=ACCENT,
            padding=(1, 2),
        ))
        return False

    if command == "/state":
        if not args:
            console.print(f"[{WARN}]Usage:[/] /state <phase> [goal text]")
            return False
        phase = args[0]
        goal = " ".join(args[1:]) if len(args) > 1 else None
        try:
            update_state(root, phase=phase, current_goal=goal)
        except FileNotFoundError as exc:
            console.print(f"[{ERR}]{exc}[/]")
            return False
        console.print(f"[{OK}]Updated state:[/] phase={phase}")
        return False

    if command == "/snapshot":
        if not args:
            console.print(f"[{WARN}]Usage:[/] /snapshot <phase> [goal text]")
            return False
        phase = args[0]
        goal = " ".join(args[1:]) if len(args) > 1 else None
        try:
            update_state(root, phase=phase, current_goal=goal)
            result = save_context(root)
        except FileNotFoundError as exc:
            console.print(f"[{ERR}]{exc}[/]")
            return False
        console.print(f"[{OK}]Snapshot saved:[/] {result['path']}")
        return False

    if command == "/change":
        if not args:
            console.print(f"[{WARN}]Usage:[/] /change <title>")
            return False
        title = " ".join(args)
        try:
            result = create_change(root, title=title)
        except FileExistsError:
            console.print(f"[{ERR}]Change already exists for:[/] {title}")
            return False
        console.print(f"[{OK}]Created change:[/] {result['id']}")
        console.print(f"[{DIM}]{result['path']}[/]")
        return False

    if command == "/changes":
        _print_change_list(root)
        return False

    if command == "/change-show":
        if not args:
            console.print(f"[{WARN}]Usage:[/] /change-show <id>")
            return False
        _print_change_detail(root, args[0])
        return False

    if command in {"/doctor", "/check"}:
        _print_doctor(root)
        return False

    console.print(f"[{ERR}]Unknown command:[/] {command}")
    suggestion = _suggest_command(command)
    if suggestion:
        console.print(f"[{DIM}]Did you mean[/] [bold {ACCENT}]{suggestion}[/][{DIM}]?[/]")
    console.print(f"[{DIM}]Type /help for available commands.[/]")
    return False


# -- /changes -----------------------------------------------------------------

def _print_change_list(root: Path) -> None:
    changes = list_changes(root)
    if not changes:
        console.print(f"[{WARN}]No change records found.[/]")
        console.print(f"[{DIM}]Try: /change Improve local handoffs[/]")
        return

    table = Table(show_header=True, header_style="bold", expand=True)
    table.add_column("ID", style=f"bold {ACCENT}", no_wrap=True)
    table.add_column("Title", style="bold white")
    table.add_column("Summary", style=DIM)
    for change in changes:
        table.add_row(change["id"], change["title"], change["summary"])

    console.print(Panel(
        table,
        title="[bold]Local Changes[/]",
        title_align="left",
        border_style=ACCENT,
        padding=(1, 2),
    ))


def _print_change_detail(root: Path, change_id: str) -> None:
    try:
        result = show_change(root, change_id)
    except FileNotFoundError as exc:
        console.print(f"[{ERR}]{exc}[/]")
        return

    console.print(Panel(
        result["content"].rstrip(),
        title=f"[bold]Change -> {result['id']}[/]",
        title_align="left",
        border_style=ACCENT,
        padding=(1, 2),
    ))


# -- /doctor ------------------------------------------------------------------

def _print_doctor(root: Path) -> None:
    from rich import box
    report = doctor_project(root)
    missing_set = set(report["missing"])

    table = Table(
        show_header=True,
        header_style="bold #06b6d4",
        box=box.ROUNDED,
        border_style="#0891b2",
        expand=True,
    )
    table.add_column("File / Component Path", style="bold white", width=35)
    table.add_column("Status", justify="left", width=14)
    table.add_column("Description", style="dim #94a3b8")

    # Map file paths to elegant descriptions
    file_descriptions = {
        ".agentflow/README.md": "Interactive workbench readme and user guide",
        ".agentflow/constitution.md": "Project boundary and AI safety rules",
        ".agentflow/config.yaml": "Agent flow engine configuration (LLM, API settings)",
        ".agentflow/state.yaml": "Current phase, active goal, and next action",
        ".agentflow/skills/SKILL.md": "Skill index, routing rules, and verification criteria",
        "AGENTS.md": "Core entrypoint configuration for AI coding agents",
    }

    def get_desc(relative_path: str) -> str:
        if relative_path in file_descriptions:
            return file_descriptions[relative_path]
        if relative_path.startswith(".claude"):
            return "Claude Code integration and instructions"
        if relative_path.startswith(".cursor") or "cursor" in relative_path:
            return "Cursor IDE workspace integration and rules"
        if relative_path.startswith(".codex") or "codex" in relative_path:
            return "Codex AI assistant integration rules"
        if relative_path.startswith(".kiro") or "kiro" in relative_path:
            return "Kiro AI developer tools integration"
        if relative_path.startswith(".qoder") or "qoder" in relative_path:
            return "Qoder custom agent workbench adapter"
        return "AgentFlow project boundary or environment adapter file"

    for relative in report["checked"]:
        desc = get_desc(relative)
        if relative in missing_set:
            # Data-layer word "Missing" + icon, so output and status agree.
            status_text = f"{RED_DOT} {CROSS} [bold #ef4444]Missing[/]"
            table.add_row(f"[dim]{relative}[/]", status_text, f"[dim]{desc}[/]")
        else:
            status_text = f"{GREEN_DOT} {TICK} [bold #10b981]OK[/]"
            table.add_row(relative, status_text, desc)

    if report["ok"]:
        title_style = "#10b981"
        title = f"{DOCTOR} [bold #10b981]Doctor — All OK[/]"
    else:
        title_style = "#f59e0b"
        n = len(report["missing"])
        title = f"{DOCTOR} [bold #f59e0b]Doctor — {n} Missing[/]"

    console.print(Panel(
        table,
        title=title,
        title_align="left",
        border_style=title_style,
        padding=(1, 2),
    ))


# -- /ask (legacy template helper) -------------------------------------------

def _print_advice(request: str, root: Path) -> None:
    advice = recommend_route(request, scan_project(root))

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bright_black", justify="right", min_width=18)
    grid.add_column()

    grid.add_row("Phase", f"[bold {ACCENT}]{advice['phase']}[/]")
    grid.add_row("Workflow", f"[bold]{advice['workflow']}[/]")
    grid.add_row("Recommended Agent", f"[bold]{advice['recommended_agent']}[/]")
    grid.add_row("Implementation", f"[{'green' if advice['implementation_allowed'] else 'yellow'}]"
                 f"{'allowed' if advice['implementation_allowed'] else 'not yet -- spec first'}[/]")
    grid.add_row("Required Skills", ", ".join(advice["required_skills"]))
    grid.add_row("Next Artifacts", ", ".join(advice["next_artifacts"]))
    grid.add_row("Reason", f"[{DIM}]{advice['reason']}[/]")

    console.print(Panel(
        grid,
        title="[bold]Route Analysis[/]",
        title_align="left",
        border_style=ACCENT,
        padding=(1, 2),
    ))

    next_cmd = f"/handoff {advice['recommended_agent']} {request}"
    console.print(f"  [{DIM}]Next ->[/] [bold {ACCENT}]{next_cmd}[/]")
    console.print()


# -- Utility ------------------------------------------------------------------

def _normalize_shortcut(line: str) -> str | None:
    try:
        parts = shlex.split(line, posix=False)
    except ValueError:
        return None
    if not parts:
        return None

    command = parts[0].lower()
    aliases = {
        "skills": "/skills",
        "skill": "/skills",
        "sync": "/sync",
        "home": "/home",
        "bind": "/bind",
        "local": "/local",
        "zip": "/zip",
        "npm": "/npm",
        "npx": "/npx",
        "gh": "/gh",
        "github": "/github",
    }
    if command not in aliases:
        return None
    remainder = line[len(parts[0]):].lstrip()
    if not remainder:
        return aliases[command]
    return f"{aliases[command]} {remainder}"


def _print_skill_home() -> None:
    info = describe_skill_home()
    lines = [f"AgentFlow home: {info['home']}", "", "Skill roots:"]
    lines.extend(f"- {root}" for root in info["skill_roots"])
    lines.append("")
    lines.append(f"Installed skills: {len(info['skills'])}")
    console.print(Panel(
        "\n".join(lines),
        title="[bold]Skill Home[/]",
        title_align="left",
        border_style=ACCENT,
        padding=(1, 2),
    ))


def _print_global_skills() -> None:
    skills = discover_global_skills()
    if not skills:
        console.print(f"[{WARN}]No global skills installed yet.[/]")
        console.print(f"[{DIM}]Try: local <path> or npm <package>[/]")
        return

    table = Table(show_header=True, header_style="bold", expand=False)
    table.add_column("Skill", style=f"bold {ACCENT}")
    table.add_column("Description")
    table.add_column("Path", style=DIM)
    for skill in skills:
        table.add_row(skill.name, skill.description, str(skill.path))

    console.print(Panel(
        table,
        title="[bold]Global Skills[/]",
        title_align="left",
        border_style=ACCENT,
        padding=(1, 2),
    ))


def _batch_install_skills(root: Path) -> None:
    console.print(Panel(
        "Paste one skill source per line, then press Enter on a blank line.\n\n"
        "Examples:\n"
        "npx skills add https://github.com/cursor/plugins/tree/main/cursor-team-kit --all\n"
        "npx skills add https://github.com/vercel-labs/skills --skill find-skills\n"
        "local D:\\Downloads\\my-skill",
        title="[bold]Batch Install[/]",
        title_align="left",
        border_style=ACCENT,
        padding=(1, 2),
    ))
    lines: list[str] = []
    while True:
        try:
            raw = console.input(f"  [{ACCENT}]source[/] > ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if not raw:
            break
        lines.append(raw)

    if not lines:
        console.print(f"[{DIM}]No sources entered.[/]")
        return
    _install_skill_lines(root, lines)


def _install_all_sources(root: Path, sources: list[str]) -> None:
    lines = [f"all {source}" for source in sources]
    _install_skill_lines(root, lines)


def _install_skill_lines(root: Path, lines: list[str]) -> None:
    installed = []
    errors: list[str] = []
    for line in lines:
        try:
            installed.extend(_install_from_batch_line(line))
        except Exception as exc:  # noqa: BLE001 - user-facing REPL error
            errors.append(f"{line}: {exc}")

    if installed:
        result = sync_project_skill_index(root)
        _print_install_result(installed, result["path"])
    if errors:
        console.print(f"[{ERR}]Some installs failed:[/]")
        for error in errors:
            console.print(f"  [{ERR}]-[/] {error}")


def _install_from_batch_line(line: str) -> list:
    try:
        parts = shlex.split(line, posix=False)
    except ValueError as exc:
        raise ValueError(f"Parse error: {exc}") from exc
    if not parts:
        return []

    command = parts[0].lower()
    args = parts[1:]
    if command == "npx":
        return _skill_list(install_npx_skill_command(args))
    if command in {"npm", "/npm"}:
        if not args:
            raise ValueError("Usage: npm <package>")
        return _skill_list(install_npm_skill(args[0]))
    if command in {"gh", "github", "/gh", "/github"}:
        if not args:
            raise ValueError("Usage: gh <owner/repo[/path]>")
        return _skill_list(install_github_skill(args[0]))
    if command in {"local", "/local"}:
        if not args:
            raise ValueError("Usage: local <path>")
        return _skill_list(import_local_skill(args[0]))
    if command in {"zip", "/zip"}:
        if not args:
            raise ValueError("Usage: zip <path>")
        return _skill_list(import_zip_skill(args[0]))
    if command == "all":
        if not args:
            raise ValueError("Usage: all <source>")
        return install_all_skill_source(args[0])
    return install_all_skill_source(line)


def _sync_skills(root: Path) -> None:
    result = sync_project_skill_index(root)
    console.print(f"[{OK}]Synced project index:[/] {result['path']}")
    console.print(f"[{DIM}]Global skills: {result['synced']}[/]")


def _install_skill(root: Path, installer, value: str) -> None:
    try:
        skill = installer(value)
        result = sync_project_skill_index(root)
    except Exception as exc:  # noqa: BLE001 - user-facing REPL error
        console.print(f"[{ERR}]Skill install failed:[/] {exc}")
        return

    _print_install_result(skill, result["path"])


def _install_skill_from_args(root: Path, installer, args: list[str]) -> None:
    try:
        skill = installer(args)
        result = sync_project_skill_index(root)
    except Exception as exc:  # noqa: BLE001 - user-facing REPL error
        console.print(f"[{ERR}]Skill install failed:[/] {exc}")
        return

    _print_install_result(skill, result["path"])


def _skill_list(installed) -> list:
    if isinstance(installed, list):
        return installed
    return [installed]


def _print_install_result(installed, index_path: str) -> None:
    skills = _skill_list(installed)
    if len(skills) == 1:
        header = f"[{OK}]Installed skill: {skills[0].name}[/]"
    else:
        header = f"[{OK}]Installed skills: {len(skills)}[/]"
    lines = [header]
    for skill in skills:
        lines.append(f"- {skill.name}: {skill.path.parent}")
    lines.append(f"Synced project index: {index_path}")
    console.print(Panel(
        "\n".join(lines),
        title="[bold]Skill Installed[/]",
        title_align="left",
        border_style=OK,
        padding=(1, 2),
    ))


def _suggest_command(command: str) -> str | None:
    """Suggest the closest known slash command for a typo."""
    if not command.startswith("/"):
        return None
    matches = difflib.get_close_matches(command, SLASH_COMMANDS, n=1, cutoff=0.6)
    if matches and matches[0] != command:
        return matches[0]
    return None


def _read_phase(root: Path) -> str:
    state_path = root / ".agentflow" / "state.yaml"
    if not state_path.exists():
        return "not initialized"

    for line in state_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("phase:"):
            return stripped.split(":", 1)[1].strip().strip('"') or "unknown"
    return "unknown"


# -- /editors -----------------------------------------------------------------

def _editors_wizard() -> None:
    """Interactive toggle for enabling/disabling editor entrypoints."""
    from .editors import (
        all_editors,
        disable_editor,
        enable_editor,
        get_enabled_editors,
    )

    catalog = all_editors()
    enabled = {spec.name for spec in get_enabled_editors()}

    # Present list
    names = sorted(catalog.keys())
    table = Table(show_header=True, header_style="bold", expand=False)
    table.add_column("#", style=f"bold {ACCENT}", width=4, justify="right")
    table.add_column("Editor")
    table.add_column("Enabled", justify="center", width=8)
    table.add_column("Entrypoint", style=DIM)

    for idx, name in enumerate(names, 1):
        spec = catalog[name]
        mark = f"[{OK}]yes[/]" if name in enabled else f"[{MUTED}]no[/]"
        table.add_row(str(idx), spec.display, mark, spec.entrypoint)

    console.print(Panel(
        table,
        title="[bold]Editors[/]",
        title_align="left",
        border_style=ACCENT,
        padding=(1, 2),
    ))
    console.print(f"  [{DIM}]Type a number to toggle, or press Enter to finish.[/]")

    while True:
        try:
            raw = console.input(f"  [{ACCENT}]toggle #[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if not raw:
            break
        try:
            idx = int(raw) - 1
            if idx < 0 or idx >= len(names):
                raise ValueError
        except ValueError:
            console.print(f"  [{ERR}]Invalid number.[/]")
            continue
        name = names[idx]
        if name in enabled:
            disable_editor(name)
            enabled.discard(name)
            console.print(f"  [{WARN}]Disabled:[/] {name}")
        else:
            enable_editor(name)
            enabled.add(name)
            console.print(f"  [{OK}]Enabled:[/] {name}")

    console.print(f"  [{DIM}]Run /init or 'flow editors apply' to update project files.[/]")
    console.print()


# -- /register ----------------------------------------------------------------

def _register_project(root: Path) -> None:
    from .projects import register_project

    entry = register_project(root)
    console.print(f"[{OK}]Registered:[/] {entry.name} -> {entry.path}")
    console.print()


# -- /sync-all ----------------------------------------------------------------

def _sync_all_projects() -> None:
    from .projects import sync_all_projects

    result = sync_all_projects()
    for item in result["results"]:
        console.print(f"  [{OK}]{item['name']}[/] ({item['link']['method']}): {item['synced']} skills")
    if result["skipped"]:
        console.print(f"  [{WARN}]Skipped (no .agentflow):[/] {', '.join(result['skipped'])}")
    if not result["results"] and not result["skipped"]:
        console.print(f"  [{DIM}]No registered projects. Use /register first.[/]")
    console.print()
