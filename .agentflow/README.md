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
