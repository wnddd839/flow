# Flow

慢慢完善的工作流。

AgentFlow is a small local CLI for setting up a repeatable AI coding workflow in
any project. It creates project rules, skill routing, state files, and handoff
prompts that you can paste into Codex, Claude Code, Cursor, Kiro, Qoder, or
Antigravity.

## Quick Start

Start the interactive workbench from any project directory:

```bash
flow
```

You will see a compact terminal dashboard with project status and a real command
prompt framed like a small input box. Type `/` commands like Claude Code, or type
a task in natural language.

```text
+-- Flow ----------------------------------------+
| AI Coding Workbench                            |
|                                                |
| Project   ./my-project                         |
| Phase     not initialized                      |
| Doctor    12 missing files                     |
| Skills    0 global skills                      |
+------------------------------------------------+
/init  /doctor  /skills  /sync  /npm  /npx  /local  /instructions

+-- Command -------------------------------------+
| > Try "/help" or type a task
+------------------------------------------------+
```

If you mistype a command (`/skill` instead of `/skills`), Flow suggests the
closest match.

## Interactive Commands

### Getting Started

| Command           | Description                            |
| ----------------- | -------------------------------------- |
| `/setup`          | Pick agents and initialize in one step |
| `/init [name]`    | Initialize, keep current agent selection |
| `/check`          | Health check (alias: `/doctor`)        |
| `/instructions`   | Show universal agent instructions      |

### Project Configuration

| Command        | Description                              |
| -------------- | ---------------------------------------- |
| `/editors`     | Toggle which editors get an entrypoint   |
| `/tools`       | Show local AI coding tool availability   |
| `/repair`      | Restore missing AgentFlow files          |
| `/scan`        | Detect project signals                   |
| `/context`     | Save a no-API handoff snapshot           |

### Session State

| Command                  | Description                              |
| ------------------------ | ---------------------------------------- |
| `/status`                | Show `.agentflow/state.yaml`             |
| `/state <phase> [goal]`  | Update the current phase and goal        |
| `/snapshot <phase> [goal]` | Update state and save handoff context  |
| `/change <title>`        | Create a local change record             |
| `/changes`               | List local change records                |
| `/change-show <id>`      | Show a local change record               |

### Skills

| Command                                 | Description                            |
| --------------------------------------- | -------------------------------------- |
| `/skills`                               | List global skills                     |
| `/skills all`                           | Batch install multiple skills          |
| `/sync`                                 | Sync global skills into this project   |
| `/npm <package>`                        | Install a skill from npm               |
| `/npx skills add <src> --skill <name>`  | Install one skill from an npx command  |
| `/npx skills add <src> --all`           | Install every skill found in a source  |
| `/gh <owner/repo>`                      | Install a skill from GitHub            |
| `/local <path>`                         | Import a local skill folder            |
| `/zip <path>`                           | Import a zipped skill package          |
| `/home`                                 | Show global skill home                 |

### Workflow Helpers

| Command                       | Description                     |
| ----------------------------- | ------------------------------- |
| `/ask <request>`              | Recommend a workflow for a task |
| `/handoff <agent> <request>`  | Generate a handoff prompt       |

### System

| Command | Description                 |
| ------- | --------------------------- |
| `/menu` | Numbered shortcuts          |
| `/help` | Show all commands           |
| `/quit` | Exit                        |

Numbered shortcuts still work for compatibility: `1` setup, `2` check,
`3` instructions, `0` quit.

## Direct CLI Commands

Run commands directly without entering the interactive shell:

```bash
flow init --name "My Project"
flow setup
flow instructions
flow skills bind "C:\Users\27297\.agentflow\skills"
flow skills import "D:\Downloads\my-skill"
flow skills install npm:@agentflow-skill/code-review
flow npx skills add https://github.com/vercel-labs/skills --skill find-skills
flow npx skills add https://github.com/cursor/plugins/tree/main/cursor-team-kit --all
flow skills all https://github.com/cursor/plugins/tree/main/cursor-team-kit
flow skills sync
flow scan
flow ask "fix pagination bug"
flow handoff codex "fix pagination bug"
flow status
flow state set --phase implement --goal "ship local assistant" --next "save context"
flow snapshot --phase verify --goal "prepare handoff" --next "open another tool"
flow changes new "Improve local handoffs" --summary "Make context switching easier."
flow changes list
flow changes show improve-local-handoffs
flow doctor
flow check
flow tools
flow tools --json
flow repair --dry-run
flow repair
flow context save
```

## Quick Setup

```bash
flow setup
```

Opens a full-screen multiselect dialog where you tick the AI coding agents to
support (Codex, Claude Code, Cursor, Kiro, Qoder, Antigravity, plus any custom
editors), then initializes the project for the chosen set in a single step.
Use arrow keys to move, Space to toggle, Enter to confirm. The dialog pre-checks
your currently enabled editors, so adding one more (e.g. Qoder) is a single
Space press. This combines `/editors` and `/init` into one flow.

In the REPL, the same dialog is available as `/setup`.

## Local Assistant Commands

Flow is designed to solve local AI coding workflow pain without requiring a
model API key.

```bash
flow doctor
```

Checks the AgentFlow project files and prints local tool availability for common
AI coding CLIs such as Codex, Claude Code, Cursor, Kiro, Qoder, and Gemini.

```bash
flow tools
flow tools --json
```

Shows the local AI coding tools Flow can see on `PATH`. Use `--json` when another
script or dashboard needs machine-readable output.

```bash
flow repair --dry-run
flow repair
```

Shows or applies a safe repair plan for missing AgentFlow-owned files. Repair
only creates files that do not exist; it does not overwrite user content.

```bash
flow context save
```

Writes `FLOW_CONTEXT.md`, a portable handoff snapshot with project signals,
verification candidates, git state, and `.agentflow/state.yaml`. Paste it into
another coding tool when switching sessions.

```bash
flow state set --phase implement --goal "ship local assistant" --next "save context"
```

Updates `.agentflow/state.yaml` so future handoffs and `flow context save`
include the current goal and next action.

```bash
flow snapshot --phase verify --goal "prepare handoff" --next "open another tool"
```

Combines state update and context generation. Use it before switching from one
AI coding tool to another.

```bash
flow changes new "Improve local handoffs" --summary "Make context switching easier."
flow changes list
flow changes show improve-local-handoffs
```

Creates, lists, and shows `.agentflow/changes/<id>/README.md` records. New
records are marked active in `.agentflow/state.yaml`. Use them for lightweight,
local task notes before starting larger work or switching tools.

## Global Skills

Flow can act as a tiny offline skill package manager. Configure one global
skill root, install skills once, then sync each project so every coding tool can
find the same skill index through `.agentflow/skills/SKILL.md`.

Default home:

```text
C:\Users\<you>\.agentflow\
  config.yaml
  skills\
  cache\
  skills.lock.yaml
```

Daily interactive use:

```text
> /npm code-review
> /npx skills add https://github.com/vercel-labs/skills --skill find-skills
> /npx skills add https://github.com/cursor/plugins/tree/main/cursor-team-kit --all
> skill all
  source > npx skills add https://github.com/cursor/plugins/tree/main/cursor-team-kit --all
  source > local D:\Downloads\my-skill-pack
  source >
> /local D:\Downloads\my-skill
> /skills
> /sync
```

Skill packages use this layout:

```text
my-skill/
  SKILL.md
```

`SKILL.md` may include frontmatter:

```markdown
---
name: code-review
description: Review another agent's implementation before accepting it.
---
```

For npm sources, Flow runs `npm pack --ignore-scripts`, extracts the package,
finds `SKILL.md`, installs it into the global skill root, and refreshes the
current project's `.agentflow/skills/SKILL.md`.

## What It Creates

```text
.agentflow/
  README.md
  constitution.md
  config.yaml
  state.yaml
  skills/
    SKILL.md
    brainstorm.md, spec.md, plan.md, implement.md, verify.md, finish.md
  prompts/
    codex.md, cursor.md, claude.md, kiro.md, qoder.md
  interfaces/
    README.md, codex.md, claude.md, cursor.md, kiro.md, qoder.md, antigravity.md
  changes/
AGENTS.md
.codex/skills/agentflow/SKILL.md
.claude/skills/agentflow/SKILL.md
.cursor/skills/agentflow/SKILL.md
.kiro/steering/agentflow.md
.qoder/skills/agentflow/SKILL.md
.agent/skills/agentflow/SKILL.md
```

## Dependencies

- Python >= 3.11
- [Rich](https://github.com/Textualize/rich) >= 13.0.0 (terminal UI)
- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) >= 3.0.0
  (interactive slash-command prompt and history)

## Development

Create a local environment and install the project with test dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Run the verification checks:

```bash
python -m compileall -f agentflow tests
python -m pytest -q
```

If `pytest` is not available in the active environment, the test suite can also
run through the standard library:

```bash
python -m unittest discover -s tests -v
```

## API Key

The MVP is offline by default. `flow init` writes `.agentflow/config.yaml`
with an API key environment variable name for future AI-assisted analysis, but
the current commands do not require or read a secret.

## Workflow

1. Run `flow init` once per project.
2. Run `flow ask "<request>"` when you are unsure where a task belongs.
3. Run `flow handoff <platform> "<request>"`.
4. Paste the prompt into your chosen AI coding tool.
5. Require the agent to finish with files changed, commands run, evidence,
   unresolved risks, and next action.

The generated rules now include task gates, a verification ladder, CI/typecheck
failure routing, CLI/UI smoke expectations, and a final cleanup pass for unused
code, debug output, stale comments, and needless abstractions.
