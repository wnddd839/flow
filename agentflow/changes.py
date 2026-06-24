"""轻量本地变更记录：``.agentflow/changes/<id>/README.md``。

创建变更时会设为 ``state.yaml`` 里的 ``active_change``，便于多步骤任务在工具间切换时对齐范围。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from .state import update_state


def create_change(
    project_dir: str | Path,
    *,
    title: str,
    summary: str = "",
    change_id: str | None = None,
) -> dict[str, str]:
    """Create a local change record and mark it active."""

    root = Path(project_dir)
    identifier = change_id or _slug(title)
    change_dir = root / ".agentflow" / "changes" / identifier
    change_dir.mkdir(parents=True, exist_ok=False)
    readme = change_dir / "README.md"
    readme.write_text(_change_readme(title, summary), encoding="utf-8")
    update_state(
        root,
        active_change=identifier,
        current_goal=title,
        next_action=f"Work through .agentflow/changes/{identifier}/README.md",
    )
    return {"id": identifier, "path": str(change_dir)}


def list_changes(project_dir: str | Path) -> list[dict[str, str]]:
    """List local change records with lightweight README metadata."""

    changes_dir = Path(project_dir) / ".agentflow" / "changes"
    if not changes_dir.is_dir():
        return []

    changes: list[dict[str, str]] = []
    for change_dir in sorted(changes_dir.iterdir(), key=lambda path: path.name):
        readme = change_dir / "README.md"
        if not change_dir.is_dir() or not readme.is_file():
            continue
        content = readme.read_text(encoding="utf-8")
        changes.append(
            {
                "id": change_dir.name,
                "path": str(change_dir),
                "title": _readme_title(content) or change_dir.name,
                "summary": _readme_summary(content),
            }
        )
    return changes


def show_change(project_dir: str | Path, change_id: str) -> dict[str, str]:
    """Read one local change record."""

    change_dir = Path(project_dir) / ".agentflow" / "changes" / change_id
    readme = change_dir / "README.md"
    if not readme.is_file():
        raise FileNotFoundError(f"No change record found: {change_id}")
    return {
        "id": change_id,
        "path": str(change_dir),
        "content": readme.read_text(encoding="utf-8"),
    }


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "change"


def _readme_title(content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _readme_summary(content: str) -> str:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "## Summary":
            continue
        for summary_line in lines[index + 1 :]:
            summary = summary_line.strip()
            if summary:
                return summary
    return ""


def _change_readme(title: str, summary: str) -> str:
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    body = summary.strip() or "Describe the goal, scope, and acceptance criteria."
    return (
        f"# {title}\n\n"
        f"Created: {created}\n\n"
        "## Summary\n\n"
        f"{body}\n\n"
        "## Scope\n\n"
        "- Keep the work focused on this change.\n"
        "- Note non-goals before implementation.\n\n"
        "## Acceptance\n\n"
        "- Record the verification command and result before finishing.\n\n"
        "## Notes\n\n"
        "- Add decisions, risks, and handoff notes here.\n"
    )
