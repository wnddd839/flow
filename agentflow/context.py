"""Context snapshot generation for no-API handoffs between coding tools."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .core import doctor_project, scan_project


def render_context_markdown(project_dir: str | Path) -> str:
    """Render a local project context snapshot as Markdown."""

    root = Path(project_dir)
    scan = scan_project(root)
    doctor = doctor_project(root)
    git = _git_summary(root)
    state = _read_text(root / ".agentflow" / "state.yaml")
    commands = scan["test_commands"] or ["Identify the correct verification command first."]

    lines = [
        "# Flow Context",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "## Project",
        "",
        f"- Path: `{root}`",
        f"- Types: {', '.join(scan['project_types'])}",
        f"- Docs: {', '.join(scan['docs']) if scan['docs'] else 'none detected'}",
        f"- Doctor: {'OK' if doctor['ok'] else str(len(doctor['missing'])) + ' issue(s)'}",
        "",
        "## Verification Candidates",
        "",
    ]
    lines.extend(f"- `{command}`" for command in commands)
    lines.extend(
        [
            "",
            "## Git",
            "",
            f"- Branch: {git['branch']}",
            f"- Status: {git['status']}",
            "",
            "Recent commits:",
        ]
    )
    if git["commits"]:
        lines.extend(f"- {commit}" for commit in git["commits"])
    else:
        lines.append("- none detected")

    lines.extend(
        [
            "",
            "## AgentFlow State",
            "",
            "```yaml",
            state.rstrip() if state else "No .agentflow/state.yaml found.",
            "```",
            "",
            "## Next Handoff",
            "",
            "- Read `.agentflow/constitution.md` and `.agentflow/skills/SKILL.md` first.",
            "- Keep changes scoped to the current request.",
            "- Finish with files changed, commands run, evidence, risks, and next action.",
            "",
        ]
    )
    return "\n".join(lines)


def save_context(
    project_dir: str | Path,
    output: str | Path | None = None,
) -> dict[str, str]:
    """Write a context snapshot to disk."""

    root = Path(project_dir)
    target = Path(output) if output else root / "FLOW_CONTEXT.md"
    if not target.is_absolute():
        target = root / target
    target.parent.mkdir(parents=True, exist_ok=True)
    content = render_context_markdown(root)
    target.write_text(content, encoding="utf-8")
    return {"path": str(target), "content": content}


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _git_summary(root: Path) -> dict[str, object]:
    if _run_git(root, "rev-parse", "--is-inside-work-tree") != "true":
        return {"branch": "not a git repository", "status": "n/a", "commits": []}

    branch = _run_git(root, "branch", "--show-current") or "detached"
    status = _run_git(root, "status", "--short") or "clean"
    commits_text = _run_git(root, "log", "--oneline", "--max-count=5")
    commits = [line for line in commits_text.splitlines() if line.strip()]
    return {"branch": branch, "status": status, "commits": commits}


def _run_git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()
