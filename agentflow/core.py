"""Core AgentFlow operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from . import templates


SKILL_PURPOSES = {
    "brainstorm": "Clarify ambiguous goals before writing implementation code.",
    "spec": "Create proposal and design artifacts for risky or unclear changes.",
    "plan": "Break approved work into small implementation and verification tasks.",
    "implement": "Execute one scoped task while obeying project boundaries.",
    "verify": "Run checks and collect acceptance evidence before claiming completion.",
    "finish": "Close a session with summary, evidence, risks, and next action.",
}

# Files that are always part of the .agentflow skeleton, regardless of which
# editors the user has enabled. Editor entrypoints are checked separately so
# doctor only complains about editors the user actually enabled.
BASE_REQUIRED_FILES = [
    ".agentflow/README.md",
    ".agentflow/constitution.md",
    ".agentflow/config.yaml",
    ".agentflow/state.yaml",
    ".agentflow/skills/SKILL.md",
    "AGENTS.md",
]


def init_project(
    project_dir: str | Path,
    project_name: str | None = None,
    editors: Iterable[str] | None = None,
    force: bool = False,
    api_key_env: str = "AGENTFLOW_API_KEY",
    provider: str = "openai-compatible",
    model: str = "gpt-5.2",
    link_global_skills: bool = True,
    home: str | Path | None = None,
) -> dict[str, list[str]]:
    """Create the AgentFlow workflow skeleton.

    Editor entrypoints (``.codex/``, ``.claude/``, ...) are no longer generated
    by default. The set of enabled editors is read from the user config at
    ``~/.agentflow/editors.yaml``; pass ``editors=...`` to override for one
    invocation, or use ``flow editors`` / the ``/editors`` REPL wizard to
    persist a selection.
    """

    root = Path(project_dir)
    name = project_name or root.name or "Project"
    created: list[str] = []
    skipped: list[str] = []

    skill_index_content = templates.skill_index()
    try:
        from .skills import CONFIG_FILE, agentflow_home, discover_global_skills, get_skill_roots

        if (agentflow_home(home) / CONFIG_FILE).exists():
            skill_index_content = templates.skill_index(
                global_skills=discover_global_skills(home=home),
                skill_roots=get_skill_roots(home=home),
            )
    except Exception:
        # Project init must stay offline and resilient even if global skill
        # configuration is broken. Users can repair with `flow skills sync`.
        skill_index_content = templates.skill_index()

    files: dict[str, str] = {
        ".agentflow/README.md": templates.agentflow_readme(),
        ".agentflow/constitution.md": templates.constitution(name),
        ".agentflow/config.yaml": templates.config(api_key_env, provider, model),
        ".agentflow/state.yaml": templates.state(name),
        ".agentflow/skills/SKILL.md": skill_index_content,
        ".agentflow/interfaces/README.md": templates.interfaces_readme(),
        ".agentflow/changes/.gitkeep": "",
        "AGENTS.md": templates.agents_md(),
    }

    for skill_name, purpose in SKILL_PURPOSES.items():
        files[f".agentflow/skills/{skill_name}.md"] = templates.skill(skill_name, purpose)

    # Resolve the editor selection.
    from .editors import (  # local import keeps core importable without editors module deps
        all_editors,
        apply_editors,
        get_enabled_editors,
        save_editor_config,
        load_editor_config,
    )

    if editors is not None:
        editor_names = [name for name in editors if name]
        config = load_editor_config(home=home)
        save_editor_config(editor_names, config["custom"], home=home)

    enabled_specs = get_enabled_editors(home=home)
    catalog = all_editors(home=home)

    # Per-editor prompt and interface notes are written for the canonical
    # platforms only (the built-in ones), so we don't litter on disk for
    # custom editors with arbitrary names.
    for spec in enabled_specs:
        if spec.name in templates.PLATFORM_DISPLAY:
            files[f".agentflow/prompts/{spec.name}.md"] = templates.prompt_template(spec.name)
            files[f".agentflow/interfaces/{spec.name}.md"] = templates.platform_interface(spec.name)

    for relative, content in files.items():
        status = _write_text(root / relative, content, force=force)
        if status == "created":
            created.append(relative)
        else:
            skipped.append(relative)

    # Materialize editor entrypoints based on the persisted config.
    editor_result = apply_editors(root, home=home, force=force)
    created.extend(editor_result["created"])
    skipped.extend(editor_result["kept"])

    # Best-effort link to the global skills folder so the index can use
    # in-workspace relative paths.
    link_info: dict[str, object] | None = None
    if link_global_skills:
        try:
            from .skills import link_global_skills_dir, sync_project_skill_index

            link_info = link_global_skills_dir(root, home=home)
            sync_project_skill_index(root, home=home)
        except Exception as exc:  # noqa: BLE001
            link_info = {"method": "error", "error": str(exc)}

    return {
        "created": created,
        "skipped": skipped,
        "editors_removed": editor_result["removed"],
        "link": link_info,
    }


def scan_project(project_dir: str | Path) -> dict[str, list[str] | int]:
    """Detect simple project signals without calling any model."""

    root = Path(project_dir)
    project_types: list[str] = []
    test_commands: list[str] = []
    docs: list[str] = []

    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        project_types.append("python")
        test_commands.append("python -m pytest")

    if (root / "package.json").exists():
        project_types.append("node")
        test_commands.append("npm test")

    if (root / "pom.xml").exists():
        project_types.append("java")
        test_commands.append("mvn test")

    if (root / "Cargo.toml").exists():
        project_types.append("rust")
        test_commands.append("cargo test")

    for candidate in ("README.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md"):
        if (root / candidate).exists():
            docs.append(candidate)

    change_count = len(list((root / ".agentflow" / "changes").glob("*"))) if (
        root / ".agentflow" / "changes"
    ).exists() else 0

    return {
        "project_types": project_types or ["unknown"],
        "test_commands": test_commands,
        "docs": docs,
        "change_count": change_count,
    }


def recommend_route(request: str, scan: dict[str, object] | None = None) -> dict[str, object]:
    """Recommend the next AI coding workflow for a request."""

    text = request.lower()
    scan = scan or {}

    if _contains_any(text, ("从零", "新项目", "开始做", "搭建", "初始化", "0 到 1")):
        return {
            "phase": "project-start",
            "workflow": "openspec-or-spec-kit",
            "recommended_agent": "codex",
            "implementation_allowed": False,
            "required_skills": ["brainstorm", "spec", "plan"],
            "next_artifacts": ["constitution", "proposal", "design", "tasks"],
            "reason": "New or broad work needs project rules and specification before coding.",
        }

    if _contains_any(
        text,
        (
            "安全",
            "权限",
            "认证",
            "架构",
            "重构",
            "数据模型",
            "策略",
            "policy",
            "security",
            "auth",
            "architecture",
        ),
    ):
        return {
            "phase": "design-required",
            "workflow": "openspec-change",
            "recommended_agent": "codex",
            "implementation_allowed": False,
            "required_skills": ["spec", "plan", "implement", "verify"],
            "next_artifacts": ["proposal", "design", "tasks", "verify"],
            "reason": "Risky or cross-cutting work should be specified before implementation.",
        }

    if _contains_any(text, ("测试", "验收", "验证", "test", "verify", "coverage")):
        return {
            "phase": "verify",
            "workflow": "verification-pass",
            "recommended_agent": "cursor",
            "implementation_allowed": True,
            "required_skills": ["verify", "finish"],
            "next_artifacts": ["verify"],
            "reason": "The request is primarily about evidence, tests, or hardening.",
        }

    if _contains_any(text, ("bug", "修复", "报错", "失败", "异常", "fix", "error")):
        return {
            "phase": "bugfix",
            "workflow": "simple-change",
            "recommended_agent": "codex",
            "implementation_allowed": True,
            "required_skills": ["implement", "verify"],
            "next_artifacts": ["task", "verify"],
            "reason": "A localized bugfix can usually start from a targeted task prompt.",
        }

    return {
        "phase": "feature-planning",
        "workflow": "openspec-change",
        "recommended_agent": "codex",
        "implementation_allowed": False,
        "required_skills": ["brainstorm", "spec", "plan"],
        "next_artifacts": ["proposal", "tasks"],
        "reason": "Default to a lightweight spec when scope is not obviously tiny.",
    }


def render_handoff_prompt(project_dir: str | Path, platform: str, request: str) -> str:
    """Render a platform-oriented prompt the user can paste into an AI coding agent."""

    root = Path(project_dir)
    scan = scan_project(root)
    advice = recommend_route(request, scan)
    display = templates.PLATFORM_DISPLAY.get(platform.lower(), platform.title())
    required_skills = ", ".join(str(item) for item in advice["required_skills"])
    next_artifacts = ", ".join(str(item) for item in advice["next_artifacts"])
    test_commands = scan["test_commands"] or ["Identify the correct verification command first."]

    guardrail = (
        "Do not start implementation before proposal/design/tasks are clear."
        if not advice["implementation_allowed"]
        else "Keep implementation limited to the requested change."
    )

    return (
        f"# Handoff for {display}\n\n"
        f"Request:\n{request}\n\n"
        "Read these files first:\n"
        "- `.agentflow/constitution.md`\n"
        "- `.agentflow/state.yaml`\n"
        "- `.agentflow/skills/SKILL.md`\n\n"
        f"Recommended workflow: {advice['workflow']}\n"
        f"Phase: {advice['phase']}\n"
        f"Required skills: {required_skills}\n"
        f"Next artifacts: {next_artifacts}\n\n"
        f"Guardrail: {guardrail}\n\n"
        "Verification candidates:\n"
        + "".join(f"- `{command}`\n" for command in test_commands)
        + "\nFinish by writing an acceptance summary with files changed, commands run, "
        "results, unverified risks, and the next action.\n"
    )


def doctor_project(
    project_dir: str | Path,
    home: str | Path | None = None,
) -> dict[str, object]:
    """Check whether the AgentFlow skeleton exists.

    The required-files list adapts to the user's enabled editor selection so
    a project that opted out of, say, Claude doesn't fail doctor for not having
    ``.claude/skills/agentflow/SKILL.md``.
    """

    from .editors import get_enabled_editors  # local import to avoid cycle

    root = Path(project_dir)
    enabled = get_enabled_editors(home=home)
    required = list(BASE_REQUIRED_FILES) + [spec.entrypoint for spec in enabled]
    missing = [relative for relative in required if not (root / relative).exists()]
    return {
        "ok": not missing,
        "missing": missing,
        "checked": required,
        "editors": [spec.name for spec in enabled],
    }


# Backwards compatibility: the original module exposed a static REQUIRED_FILES
# list. Keep it as the base skeleton; tests asserting against editor entrypoints
# are now expected to read ``doctor_project()['checked']`` instead.
REQUIRED_FILES = list(BASE_REQUIRED_FILES)


def _write_text(path: Path, content: str, force: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return "skipped"
    path.write_text(content, encoding="utf-8")
    return "created"


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def to_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
