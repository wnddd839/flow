"""读写 ``.agentflow/state.yaml``（当前阶段、目标、下一步）。

字段见 ``STATE_FIELDS``。被 ``changes``、``cli state``、``snapshot`` 等更新；
AI 工具交接时应先读此文件了解会话进度。
"""

from __future__ import annotations

from pathlib import Path


STATE_FIELDS = (
    "project",
    "phase",
    "current_goal",
    "active_change",
    "next_action",
    "blocked",
)


def load_state(project_dir: str | Path) -> dict[str, str]:
    """Load `.agentflow/state.yaml` as simple scalar key/value pairs."""

    path = _state_path(project_dir)
    if not path.exists():
        raise FileNotFoundError("No .agentflow/state.yaml found. Run `flow init` first.")

    state: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        state[key.strip()] = value.strip().strip('"')
    return state


def update_state(
    project_dir: str | Path,
    *,
    phase: str | None = None,
    current_goal: str | None = None,
    active_change: str | None = None,
    next_action: str | None = None,
    blocked: bool | None = None,
) -> dict[str, str]:
    """Update selected fields in `.agentflow/state.yaml`."""

    state = load_state(project_dir)
    updates = {
        "phase": phase,
        "current_goal": current_goal,
        "active_change": active_change,
        "next_action": next_action,
    }
    for key, value in updates.items():
        if value is not None:
            state[key] = value
    if blocked is not None:
        state["blocked"] = "true" if blocked else "false"

    _write_state(_state_path(project_dir), state)
    return state


def _state_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / ".agentflow" / "state.yaml"


def _write_state(path: Path, state: dict[str, str]) -> None:
    lines: list[str] = []
    for field in STATE_FIELDS:
        if field not in state:
            continue
        value = state[field]
        if field == "blocked":
            lines.append(f"{field}: {str(value).lower()}")
        else:
            lines.append(f'{field}: "{value}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
