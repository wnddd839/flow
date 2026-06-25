"""``flow init`` 编辑器选择（交互式或回退为简单列表）。"""

from __future__ import annotations

import sys
from typing import Callable

from . import templates
from .diagnostics import detect_tools
from .editors import normalize_editor_names


def can_run_interactive_picker(is_tty: bool | None = None) -> bool:
    if is_tty is not None:
        return is_tty
    return sys.stdin.isatty() and sys.stdout.isatty()


def pick_editors(
    *,
    input_func: Callable[[str], str] | None = None,
    is_tty: bool | None = None,
) -> list[str]:
    """交互式多选编辑器；非 TTY 时返回空列表（仅骨架）。"""
    if not can_run_interactive_picker(is_tty):
        return []

    try:
        return _pick_with_prompt_toolkit()
    except Exception:
        return _pick_with_fallback(input_func=input_func)


def _pick_with_prompt_toolkit() -> list[str]:
    from prompt_toolkit.shortcuts import checkboxlist_dialog

    detected = {tool.name for tool in detect_tools() if tool.status == "ok"}
    values: list[tuple[str, str]] = []
    for name in templates.DEFAULT_PLATFORMS:
        spec_display = templates.PLATFORM_DISPLAY[name]
        entry = templates.PLATFORM_ENTRYPOINTS[name]
        on_path = "on PATH" if name in detected else "not on PATH"
        label = f"{spec_display:<14} ({name}) -> {entry}  [{on_path}]"
        values.append((name, label))

    result = checkboxlist_dialog(
        title="Flow init — 选择编辑器",
        text=(
            "勾选要生成薄入口的平台（Space 切换，Enter 确认）。\n"
            "不选则只生成 .agentflow/ 规范骨架，根目录不会多出 CLAUDE.md 等文件。"
        ),
        values=values,
    ).run()

    if result is None:
        return []
    return normalize_editor_names(result)


def _pick_with_fallback(
    *,
    input_func: Callable[[str], str] | None = None,
) -> list[str]:
    reader = input_func or input
    print("Select editors (comma-separated names; empty = skeleton only):")
    for index, name in enumerate(templates.DEFAULT_PLATFORMS, start=1):
        display = templates.PLATFORM_DISPLAY[name]
        entry = templates.PLATFORM_ENTRYPOINTS[name]
        print(f"  {index}. {name:<12} {display} -> {entry}")
    print("  Names:", ", ".join(templates.DEFAULT_PLATFORMS))
    line = reader("Editors: ").strip()
    if not line:
        return []
    parts = [part.strip() for part in line.replace(" ", ",").split(",") if part.strip()]
    return normalize_editor_names(parts)
