"""No-API local diagnostics for Flow."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

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

    for command, label in KNOWN_TOOLS:
        path = shutil.which(command)
        status = "ok" if path else "missing"
        message = path or "not found on PATH"
        items.append(DiagnosticItem("Tools", label, status, message))

    return items
