"""Text templates for AgentFlow project scaffolding."""

from __future__ import annotations

from textwrap import dedent
from typing import Iterable


DEFAULT_PLATFORMS = ("codex", "claude", "cursor", "kiro", "qoder", "antigravity")

PLATFORM_DISPLAY = {
    "codex": "Codex",
    "claude": "Claude Code",
    "cursor": "Cursor",
    "kiro": "Kiro",
    "qoder": "Qoder",
    "antigravity": "Antigravity",
}

PLATFORM_ENTRYPOINTS = {
    "codex": ".codex/skills/agentflow/SKILL.md",
    "claude": ".claude/skills/agentflow/SKILL.md",
    "cursor": ".cursor/skills/agentflow/SKILL.md",
    "kiro": ".kiro/steering/agentflow.md",
    "qoder": ".qoder/skills/agentflow/SKILL.md",
    "antigravity": ".agent/skills/agentflow/SKILL.md",
}


def constitution(project_name: str) -> str:
    return dedent(
        f"""\
        # {project_name} AI Coding Constitution

        ## Purpose

        This file defines the project rules every AI coding assistant must follow.
        Keep it short, concrete, and current. The goal is repeatable engineering,
        not clever one-off prompting.

        ## Working Agreement

        - Read `.agentflow/README.md`, `.agentflow/state.yaml`, and
          `.agentflow/skills/SKILL.md` before project work.
        - Restate the target in 1-2 lines before making changes.
        - Choose the smallest matching workflow: clarify, spec, plan, implement,
          verify, or finish.
        - Prefer deterministic local checks and scripts before model judgment.
        - Keep implementation scoped to the active request.
        - Do not modify unrelated files.
        - Do not invent new architecture, tools, or abstractions unless the task
          requires them and the reason is written down.

        ## Task Gates

        Before implementation, the agent must know:

        - scope: what will change
        - non-goals: what will not change
        - acceptance: how completion will be judged
        - likely files or areas touched

        If any gate is unclear, stop and ask for clarification or create a
        lightweight spec before coding.

        ## Project Boundaries

        - Define what this project is responsible for.
        - Define what this project deliberately does not do.
        - Define directories or files that require extra caution.

        ## Verification Ladder

        Use the closest meaningful check. Move down the ladder when risk is high:

        1. Static sanity: read the affected files and existing docs.
        2. Compile/typecheck/lint: run the project command if available.
        3. Unit tests: run focused tests first, broader tests when risk expands.
        4. Integration or CLI/UI smoke test: exercise the changed workflow.
        5. Manual acceptance notes: only when automation is unavailable.

        Do not claim success without verification evidence. If verification is
        blocked, say exactly what blocked it and what remains risky.

        ## Quality Cleanup Pass

        Before finishing, remove obvious AI slop:

        - unused code, dead branches, debug prints, and stale comments
        - overbroad abstractions for small local changes
        - duplicated helper logic that already exists nearby
        - TODOs that are not explicitly part of the accepted scope

        Prefer the repository's existing patterns over new style.

        ## Completion Report

        Every implementation handoff must include:

        - files changed
        - commands run
        - verification result
        - acceptance evidence
        - unresolved risks
        - recommended next step
        """
    )


def config(api_key_env: str, provider: str, model: str) -> str:
    return dedent(
        f"""\
        provider: "{provider}"
        model: "{model}"
        api_key_env: "{api_key_env}"
        mode: "offline-by-default"
        """
    )


def state(project_name: str) -> str:
    return dedent(
        f"""\
        project: "{project_name}"
        phase: "initialized"
        current_goal: ""
        active_change: ""
        next_action: "Run `flow instructions` and paste the output into your AI coding tool."
        blocked: false
        """
    )


def skill_index(
    global_skills: Iterable[object] | None = None,
    skill_roots: Iterable[object] | None = None,
) -> str:
    global_section = _global_skill_section(global_skills, skill_roots)
    return dedent(
        """\
        # AgentFlow Skill Index

        This is the single source of truth for workflow skills in this project.
        Platform-specific skill files should stay thin and point back here.

        ## Always Start Here

        1. Read `.agentflow/constitution.md`.
        2. Read `.agentflow/state.yaml`.
        3. Restate the task, scope, non-goals, and acceptance criteria.
        4. Select the skill that matches the current phase and request.
        5. Keep implementation scoped to the active change.
        6. End with verification evidence or explicit unresolved risk.

        ## Available Skills

        - `brainstorm`: clarify goals, scope, non-goals, and success criteria.
        - `spec`: create proposal/design artifacts before risky or ambiguous work.
        - `plan`: turn an approved design into small executable tasks.
        - `implement`: execute one scoped task at a time.
        - `verify`: run tests, inspect output, and collect acceptance evidence.
        - `finish`: summarize changes, risks, evidence, and next action.

        ## Routing Rules

        - New project or unclear goal: use `brainstorm`, then `spec`.
        - Security, architecture, data model, or cross-module work: use `spec`.
        - Small localized bugfix: use `implement`, then `verify`.
        - Compiler, typecheck, lint, CI, or GitHub Actions failure: reproduce
          locally if possible, then use `verify` before broad edits.
        - UI change: use `implement`, then run the closest UI or browser smoke.
        - CLI change: use `implement`, then run a command-level smoke test.
        - Testing, hardening, or regression work: use `verify`.
        - End of a session: use `finish`.

        ## Verification Rules

        - Prefer focused checks first, then broader checks when shared behavior changed.
        - If a check fails, fix the root cause or report the exact blocker.
        - Do not mark work complete from visual inspection alone when tests exist.

        ## Quality Cleanup Rules

        - Do a deslop pass before `finish`: remove unused code, debug output,
          stale comments, accidental duplication, and needless abstractions.
        - Preserve existing style and module boundaries.
        - Do not leave TODOs unless the user explicitly accepted them.
        """
    ) + global_section


def skill(name: str, purpose: str) -> str:
    return dedent(
        f"""\
        # {name.title()} Skill

        ## Purpose

        {purpose}

        ## Required Inputs

        - `.agentflow/constitution.md`
        - `.agentflow/state.yaml`
        - `.agentflow/skills/SKILL.md`
        - Current user request or active change folder

        ## Workflow

        1. Confirm the task, scope, non-goals, and acceptance criteria.
        2. Read the smallest relevant set of files before editing.
        3. Make the narrowest change that satisfies the acceptance criteria.
        4. Run the closest meaningful verification command.
        5. Do a quality cleanup pass before reporting completion.

        ## Stop Conditions

        - The request needs a spec or plan before safe implementation.
        - The task would require touching unrelated modules.
        - Verification cannot run and the risk is material.
        - Required files, credentials, or commands are unavailable.

        ## Output Contract

        - State what you did.
        - State what evidence exists, including exact commands when available.
        - State what remains unclear or risky.
        - State the next recommended action.
        """
    )


def prompt_template(platform: str) -> str:
    display = PLATFORM_DISPLAY.get(platform, platform.title())
    return dedent(
        f"""\
        # {display} Handoff Template

        Read these first:

        - `.agentflow/constitution.md`
        - `.agentflow/state.yaml`
        - `.agentflow/skills/SKILL.md`

        Work only on the scoped request. Do not broaden the task.

        Before editing:

        - restate the target
        - identify scope, non-goals, and acceptance criteria
        - choose the matching AgentFlow skill

        Before finishing:

        - run the closest meaningful verification command
        - remove debug output, unused code, stale comments, and needless abstraction
        - report files changed, commands run, verification result, acceptance
          evidence, unresolved risks, and recommended next step
        """
    )


def interfaces_readme() -> str:
    return dedent(
        """\
        # AgentFlow Interfaces

        This directory is the unified interface layer for AI coding tools.
        Platform-specific entrypoints should stay thin and point here.

        ## Canonical Files

        - `.agentflow/constitution.md`: project rules and boundaries.
        - `.agentflow/state.yaml`: current phase, goal, and next action.
        - `.agentflow/skills/SKILL.md`: skill index and routing rules.
        - `.agentflow/interfaces/*.md`: platform-specific handoff notes.

        ## Rule

        Update the canonical files first. Treat tool-specific folders such as
        `.codex/`, `.claude/`, `.cursor/`, `.kiro/`, `.qoder/`, and `.agent/`
        as adapters, not the source of truth.

        ## Adapter Contract

        Each platform adapter should:

        - point back to the canonical `.agentflow/` files
        - avoid duplicating long rules that can drift
        - require verification evidence before completion
        - preserve project boundaries and existing style
        """
    )


def platform_interface(platform: str) -> str:
    display = PLATFORM_DISPLAY.get(platform, platform.title())
    return dedent(
        f"""\
        # {display} Interface

        Use this file as the platform-facing adapter for {display}.

        ## Startup Contract

        1. Read `.agentflow/interfaces/README.md`.
        2. Read `.agentflow/constitution.md`.
        3. Read `.agentflow/state.yaml`.
        4. Read `.agentflow/skills/SKILL.md`.
        5. Select the matching skill before taking action.

        ## Completion Contract

        Finish with:

        - files changed
        - commands run
        - verification result
        - acceptance evidence
        - unresolved risk
        - next recommended action

        If checks were not run, say why. Do not claim success without evidence.
        """
    )


def agents_md() -> str:
    return dedent(
        """\
        # AgentFlow Entry

        Before doing project work, read:

        - `.agentflow/interfaces/README.md`
        - `.agentflow/constitution.md`
        - `.agentflow/state.yaml`
        - `.agentflow/skills/SKILL.md`

        Follow the skill routing rules in `.agentflow/skills/SKILL.md`.
        Do not start implementation when the request needs a spec or plan first.
        Keep edits scoped. Prefer deterministic checks. Finish with verification
        evidence, acceptance notes, unresolved risks, and next action.
        """
    )


AGENTFLOW_GENERATED_MARKER = "<!-- Generated by AgentFlow. Safe to delete. -->"


def thin_entrypoint(platform: str, display: str | None = None) -> str:
    display_name = display or PLATFORM_DISPLAY.get(platform, platform.title())
    return dedent(
        f"""\
        {AGENTFLOW_GENERATED_MARKER}
        # AgentFlow for {display_name}

        This is a thin platform entrypoint. The canonical workflow lives in:

        - `.agentflow/interfaces/README.md`
        - `.agentflow/interfaces/{platform}.md`
        - `.agentflow/constitution.md`
        - `.agentflow/state.yaml`
        - `.agentflow/skills/SKILL.md`

        Read those files before project work and follow the selected skill.
        Do not claim completion without verification evidence.
        """
    )


def agentflow_readme() -> str:
    return dedent(
        """\
        # AgentFlow

        This project uses AgentFlow to provide a unified context layer for
        AI coding assistants.

        ## Start Here

        1. Read `.agentflow/constitution.md` for project rules and boundaries.
        2. Read `.agentflow/state.yaml` for the current phase and next action.
        3. Read `.agentflow/skills/SKILL.md` for workflow routing rules.
        4. Read `.agentflow/interfaces/README.md` for platform adapter notes.

        ## Rule

        The `.agentflow/` directory is the source of truth.
        Tool-specific folders (`.codex/`, `.claude/`, `.cursor/`, `.kiro/`,
        `.qoder/`, `.agent/`) are thin adapters that point back here.

        Do not start implementation until the current task has clear scope
        and acceptance criteria.

        ## Work Loop

        1. Clarify scope, non-goals, and acceptance criteria.
        2. Pick the smallest matching workflow from `.agentflow/skills/SKILL.md`.
        3. Implement only the active request.
        4. Run the closest meaningful verification.
        5. Do a quality cleanup pass.
        6. Finish with evidence, risks, and next step.

        ## Evidence Standard

        A task is not done because code changed. It is done when the agent can
        show what changed, what was checked, what passed or failed, and what risk
        remains.
        """
    )


def _global_skill_section(
    global_skills: Iterable[object] | None,
    skill_roots: Iterable[object] | None,
) -> str:
    roots = list(skill_roots or [])
    skills = list(global_skills or [])
    if not roots and not skills:
        return ""

    lines = [
        "",
        "## Global Skill Roots",
        "",
    ]
    if roots:
        for root in roots:
            lines.append(f"- `{root}`")
    else:
        lines.append("- No global skill root configured.")

    lines.extend(
        [
            "",
            "## Global Skills",
            "",
            "When a request matches one of these skills, read the referenced",
            "`SKILL.md` before taking action. If the file is outside the current",
            "workspace and cannot be read, say so and continue with the closest",
            "project-local workflow skill.",
            "",
        ]
    )

    if not skills:
        lines.append("- No global skills installed yet. Use `flow skills import <path>` or `npm <package>`.")
    else:
        for skill in skills:
            name = getattr(skill, "name", "unknown")
            description = getattr(skill, "description", "")
            path = getattr(skill, "path", "")
            lines.append(f"- `{name}`")
            if description:
                lines.append(f"  - Use when: {description}")
            lines.append(f"  - Path: `{path}`")

    return "\n".join(lines) + "\n"


AGENT_INSTRUCTIONS = dedent(
    """\
    You are working in an AgentFlow-initialized project.

    Before doing any project work, read:
    - .agentflow/README.md
    - .agentflow/constitution.md
    - .agentflow/state.yaml
    - .agentflow/skills/SKILL.md
    - .agentflow/interfaces/README.md

    Follow the workflow rules in .agentflow/skills/SKILL.md.
    Restate the task, scope, non-goals, and acceptance criteria before editing.
    Do not start implementation until the current task has clear scope and acceptance criteria.
    Prefer deterministic local checks over guessing.
    Keep edits scoped to the active request.
    Do a quality cleanup pass before completion.
    When finished, report:
    - files changed
    - commands run
    - verification result
    - acceptance evidence
    - unresolved risks
    - recommended next step
    """
)
