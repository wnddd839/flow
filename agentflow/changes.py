"""Lightweight local change records for AgentFlow."""

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


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "change"


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
