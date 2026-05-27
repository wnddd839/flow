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
