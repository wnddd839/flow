"""Local repair helpers for AgentFlow projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import templates
from .core import SKILL_PURPOSES, doctor_project


@dataclass(frozen=True)
class RepairAction:
    relative_path: str
    content: str
    reason: str


@dataclass(frozen=True)
class RepairPlan:
    root: Path
    actions: list[RepairAction]


def build_repair_plan(
    project_dir: str | Path,
    project_name: str | None = None,
    home: str | Path | None = None,
) -> RepairPlan:
    """Create a plan for restoring missing AgentFlow-owned files.

    The plan only creates files that are missing. It never overwrites user
    content, so it is safe to show as a dry run or apply directly.
    """

    root = Path(project_dir)
    name = project_name or _read_project_name(root) or root.name or "Project"
    report = doctor_project(root, home=home)
    missing = set(str(item) for item in report["missing"])

    files = _repairable_files(name, home=home)
    actions = [
        RepairAction(relative, content, "missing AgentFlow file")
        for relative, content in files.items()
        if relative in missing and not (root / relative).exists()
    ]
    return RepairPlan(root=root, actions=actions)


def apply_repair_plan(plan: RepairPlan) -> dict[str, list[str]]:
    """Apply a repair plan, creating missing files without overwriting."""

    created: list[str] = []
    skipped: list[str] = []
    for action in plan.actions:
        target = plan.root / action.relative_path
        if target.exists():
            skipped.append(action.relative_path)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(action.content, encoding="utf-8")
        created.append(action.relative_path)
    return {"created": created, "skipped": skipped}


def _repairable_files(project_name: str, home: str | Path | None = None) -> dict[str, str]:
    files: dict[str, str] = {
        ".agentflow/README.md": templates.agentflow_readme(),
        ".agentflow/constitution.md": templates.constitution(project_name),
        ".agentflow/config.yaml": templates.config(
            "AGENTFLOW_API_KEY", "openai-compatible", "gpt-5.2"
        ),
        ".agentflow/state.yaml": templates.state(project_name),
        ".agentflow/skills/SKILL.md": templates.skill_index(),
        ".agentflow/interfaces/README.md": templates.interfaces_readme(),
        "AGENTS.md": templates.agents_md(),
    }

    for skill_name, purpose in SKILL_PURPOSES.items():
        files[f".agentflow/skills/{skill_name}.md"] = templates.skill(skill_name, purpose)

    from .editors import get_enabled_editors

    for spec in get_enabled_editors(home=home):
        files[spec.entrypoint] = templates.thin_entrypoint(spec.name, display=spec.display)

    return files


def _read_project_name(root: Path) -> str | None:
    state_path = root / ".agentflow" / "state.yaml"
    if not state_path.exists():
        return None
    for line in state_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("project:"):
            return stripped.split(":", 1)[1].strip().strip('"') or None
    return None
