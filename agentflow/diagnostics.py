"""本地环境诊断（不调用任何 AI API）。

- ``detect_tools`` — 检查 PATH 上是否存在 codex/cursor/qoder 等 CLI
- ``collect_diagnostics`` — 合并 doctor 结果与工具探测，供 ``flow doctor`` / ``flow tools`` 展示
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .core import doctor_project


KNOWN_TOOLS = (
    ("codex", "Codex"),
    ("claude", "Claude Code"),
    ("cursor", "Cursor"),
    ("kiro", "Kiro"),
    ("qoder", "Qoder"),
    ("gemini", "Gemini CLI"),
)


@dataclass(frozen=True)
class DiagnosticItem:
    section: str
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class ToolInfo:
    name: str
    display: str
    command: str
    status: str
    path: str


def detect_tools(
    path_resolver: Callable[[str], str | None] = shutil.which,
) -> list[ToolInfo]:
    """Detect known local AI coding tools without invoking them."""

    tools: list[ToolInfo] = []
    for command, label in KNOWN_TOOLS:
        path = path_resolver(command) or ""
        tools.append(
            ToolInfo(
                name=command,
                display=label,
                command=command,
                status="ok" if path else "missing",
                path=path,
            )
        )
    return tools


def collect_diagnostics(
    project_dir: str | Path,
    home: str | Path | None = None,
) -> list[DiagnosticItem]:
    """Collect local diagnostics without calling any API."""

    root = Path(project_dir)
    report = doctor_project(root, home=home)
    items: list[DiagnosticItem] = []

    if report["ok"]:
        items.append(DiagnosticItem("AgentFlow", "project files", "ok", "all required files exist"))
    else:
        for missing in report["missing"]:
            items.append(DiagnosticItem("AgentFlow", missing, "missing", "run `flow repair`"))

    for tool in detect_tools():
        message = tool.path or "not found on PATH"
        items.append(DiagnosticItem("Tools", tool.display, tool.status, message))

    return items
