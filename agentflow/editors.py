"""AI 编辑器（Agent）目录与用户级启用配置。

## 职责

为 Codex / Cursor / Qoder 等工具在项目里生成**薄入口文件**（指向 ``.agentflow/``），
避免在每个工具里各写一套规则。

## 配置位置（重要：全局）

``~/.agentflow/editors.yaml``::

    enabled: [qoder, cursor]   # 全局启用列表，影响所有项目的 doctor 与 apply
    custom:                    # 自定义编辑器入口路径

## 关键函数

- ``get_enabled_editors`` — 当前启用的编辑器列表
- ``apply_editors``       — 按配置创建/清理项目内的薄入口（禁用时不删用户自有文件）
- ``save_editor_config``  — 写回全局 yaml

## 常见误区

在 A 项目 setup 里取消勾选 Cursor，会改掉**全局**配置，B 项目的 Cursor 入口也可能被移除。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable

from .skills import agentflow_home


EDITOR_CONFIG_FILE = "editors.yaml"


@dataclass(frozen=True)
class EditorSpec:
    """Describes one editor's thin entrypoint."""

    name: str
    display: str
    entrypoint: str
    custom: bool = False


# Built-in editors. Custom ones are merged from the user config.
KNOWN_EDITORS: dict[str, EditorSpec] = {
    "codex": EditorSpec("codex", "Codex", ".codex/skills/agentflow/SKILL.md"),
    "claude": EditorSpec("claude", "Claude Code", ".claude/skills/agentflow/SKILL.md"),
    "cursor": EditorSpec("cursor", "Cursor", ".cursor/skills/agentflow/SKILL.md"),
    "kiro": EditorSpec("kiro", "Kiro", ".kiro/steering/agentflow.md"),
    "qoder": EditorSpec("qoder", "Qoder", ".qoder/skills/agentflow/SKILL.md"),
    "antigravity": EditorSpec("antigravity", "Antigravity", ".agent/skills/agentflow/SKILL.md"),
}


# -- Persistence --------------------------------------------------------------


def _config_path(home: str | Path | None = None) -> Path:
    return agentflow_home(home) / EDITOR_CONFIG_FILE


def load_editor_config(home: str | Path | None = None) -> dict:
    """Read the editors config from disk, returning a normalized dict.

    The shape is::

        {"enabled": [<name>...], "custom": {<name>: {"display":..., "path":...}}}

    Missing or malformed files yield empty enabled list and empty custom map.
    """
    path = _config_path(home)
    enabled: list[str] = []
    custom: dict[str, dict[str, str]] = {}

    if not path.exists():
        return {"enabled": enabled, "custom": custom}

    section: str | None = None
    current_custom: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if not line.startswith(" "):
            head = line.rstrip(":")
            section = head.strip().lower()
            current_custom = None
            continue

        stripped = line.strip()
        if section == "enabled" and stripped.startswith("-"):
            value = stripped[1:].strip().strip('"').strip("'")
            if value:
                enabled.append(value)
        elif section == "custom":
            indent = len(line) - len(line.lstrip())
            if indent == 2 and stripped.endswith(":"):
                current_custom = stripped.rstrip(":").strip()
                custom[current_custom] = {}
            elif current_custom and ":" in stripped:
                key, value = stripped.split(":", 1)
                custom[current_custom][key.strip()] = (
                    value.strip().strip('"').strip("'")
                )

    return {"enabled": enabled, "custom": custom}


def save_editor_config(
    enabled: Iterable[str],
    custom: dict[str, dict[str, str]] | None = None,
    home: str | Path | None = None,
) -> Path:
    """Persist the editor configuration to ``~/.agentflow/editors.yaml``."""
    home_dir = agentflow_home(home)
    home_dir.mkdir(parents=True, exist_ok=True)
    path = _config_path(home)
    custom = custom or {}

    lines = ["enabled:"]
    for name in enabled:
        lines.append(f'  - "{name}"')
    lines.append("custom:")
    for name in sorted(custom):
        spec = custom[name]
        lines.append(f"  {name}:")
        for key in ("display", "path"):
            value = spec.get(key, "")
            lines.append(f'    {key}: "{value}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# -- Catalog queries ----------------------------------------------------------


def all_editors(home: str | Path | None = None) -> dict[str, EditorSpec]:
    """Return the union of built-in and user-defined editors."""
    config = load_editor_config(home)
    catalog = dict(KNOWN_EDITORS)
    for name, spec in config["custom"].items():
        catalog[name] = EditorSpec(
            name=name,
            display=spec.get("display") or name.title(),
            entrypoint=spec.get("path") or f".{name}/skills/agentflow/SKILL.md",
            custom=True,
        )
    return catalog


def get_enabled_editors(home: str | Path | None = None) -> list[EditorSpec]:
    """Return EditorSpec instances for the names persisted as enabled."""
    config = load_editor_config(home)
    catalog = all_editors(home)
    enabled: list[EditorSpec] = []
    seen: set[str] = set()
    for name in config["enabled"]:
        if name in catalog and name not in seen:
            enabled.append(catalog[name])
            seen.add(name)
    return enabled


def enable_editor(name: str, home: str | Path | None = None) -> EditorSpec:
    """Add an editor to the persisted enabled list."""
    catalog = all_editors(home)
    if name not in catalog:
        raise KeyError(f"Unknown editor: {name}. Use 'flow editors add-custom' first.")
    config = load_editor_config(home)
    if name not in config["enabled"]:
        config["enabled"].append(name)
        save_editor_config(config["enabled"], config["custom"], home=home)
    return catalog[name]


def disable_editor(name: str, home: str | Path | None = None) -> None:
    """Remove an editor from the persisted enabled list."""
    config = load_editor_config(home)
    if name in config["enabled"]:
        config["enabled"] = [item for item in config["enabled"] if item != name]
        save_editor_config(config["enabled"], config["custom"], home=home)


def add_custom_editor(
    name: str,
    entrypoint: str,
    display: str | None = None,
    home: str | Path | None = None,
) -> EditorSpec:
    """Register a custom editor and enable it.

    The entrypoint must be a project-relative file path. Absolute paths,
    parent-directory traversal, and bare directories are rejected so a custom
    editor cannot trick Flow into writing files outside the project root.
    """
    if not name.strip():
        raise ValueError("Editor name is required")
    cleaned_entrypoint = _validate_relative_entrypoint(entrypoint)

    config = load_editor_config(home)
    config["custom"][name] = {
        "display": display or name.title(),
        "path": cleaned_entrypoint,
    }
    if name not in config["enabled"]:
        config["enabled"].append(name)
    save_editor_config(config["enabled"], config["custom"], home=home)
    return EditorSpec(
        name=name,
        display=display or name.title(),
        entrypoint=cleaned_entrypoint,
        custom=True,
    )


def remove_custom_editor(name: str, home: str | Path | None = None) -> None:
    """Unregister a custom editor and remove it from enabled list."""
    config = load_editor_config(home)
    config["custom"].pop(name, None)
    if name in config["enabled"]:
        config["enabled"] = [item for item in config["enabled"] if item != name]
    save_editor_config(config["enabled"], config["custom"], home=home)


# -- Project actions ----------------------------------------------------------


def apply_editors(
    project_dir: str | Path,
    home: str | Path | None = None,
    force: bool = False,
) -> dict[str, list[str]]:
    """Reconcile the project's editor entrypoints with the enabled config.

    Returns a dict with ``created``, ``kept``, ``removed``, and ``skipped``
    lists relative to the project root.

    Safety rules for disabled editors:
    - NEVER delete the editor's top-level directory (e.g. ``.cursor/``).
    - Only delete the specific entrypoint file if it contains the AgentFlow
      generated marker or is recognisable as a thin entrypoint.
    - After removing the file, prune empty parent directories up to (but NOT
      including) the top-level editor folder.
    """
    from . import templates  # local import avoids cycle at module load time

    root = Path(project_dir)
    resolved_root = root.resolve()
    enabled = get_enabled_editors(home)
    enabled_names = {spec.name for spec in enabled}
    created: list[str] = []
    kept: list[str] = []
    removed: list[str] = []
    skipped: list[str] = []

    for spec in enabled:
        target = _safe_project_path(resolved_root, spec.entrypoint)
        if target is None:
            # Refuse to write anywhere outside the project root.
            skipped.append(spec.entrypoint)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not force:
            kept.append(spec.entrypoint)
            continue
        target.write_text(
            templates.thin_entrypoint(spec.name, display=spec.display),
            encoding="utf-8",
        )
        created.append(spec.entrypoint)

    catalog = all_editors(home)
    for name, spec in catalog.items():
        if name in enabled_names:
            continue
        entrypoint_path = _safe_project_path(resolved_root, spec.entrypoint)
        if entrypoint_path is None:
            # Never delete files outside the project root.
            skipped.append(spec.entrypoint)
            continue
        if not entrypoint_path.is_file():
            continue
        if _is_agentflow_entrypoint(entrypoint_path):
            entrypoint_path.unlink()
            removed.append(spec.entrypoint)
            _prune_empty_parents(entrypoint_path.parent, resolved_root)
        else:
            skipped.append(spec.entrypoint)

    return {"created": created, "kept": kept, "removed": removed, "skipped": skipped}


def _validate_relative_entrypoint(entrypoint: str) -> str:
    """Validate that ``entrypoint`` is a project-relative file path.

    Returns the cleaned path string. Raises ``ValueError`` when the input is
    empty, absolute (POSIX or Windows), contains ``..`` segments, or does not
    point at a file (e.g. trailing separator only).
    """
    if entrypoint is None or not str(entrypoint).strip():
        raise ValueError("Editor entrypoint path is required")
    cleaned = str(entrypoint).strip()
    if PurePosixPath(cleaned).is_absolute() or PureWindowsPath(cleaned).is_absolute():
        raise ValueError(
            f"Editor entrypoint must be a project-relative path: {entrypoint!r}"
        )
    posix = cleaned.replace("\\", "/")
    parts = [part for part in PurePosixPath(posix).parts if part not in ("",)]
    if any(part == ".." for part in parts):
        raise ValueError(
            f"Editor entrypoint must not contain '..': {entrypoint!r}"
        )
    if not parts or posix.endswith("/") or parts[-1] in (".", ".."):
        raise ValueError(
            f"Editor entrypoint must include a file name: {entrypoint!r}"
        )
    return cleaned


def _safe_project_path(root: Path, relative: str) -> Path | None:
    """Return an absolute path inside ``root`` for ``relative`` or ``None``.

    The function rejects absolute paths and any candidate that resolves
    outside of ``root``. ``root`` is resolved internally so callers can pass
    either a resolved or an unresolved path.
    """
    if relative is None:
        return None
    candidate = str(relative).strip()
    if not candidate:
        return None
    if PurePosixPath(candidate).is_absolute() or PureWindowsPath(candidate).is_absolute():
        return None
    posix = candidate.replace("\\", "/")
    if any(part == ".." for part in PurePosixPath(posix).parts):
        return None
    try:
        resolved_root = root.resolve()
        resolved_target = (resolved_root / candidate).resolve()
        resolved_target.relative_to(resolved_root)
    except (OSError, ValueError):
        return None
    return resolved_target


def _is_agentflow_entrypoint(path: Path) -> bool:
    """Return True if the file was generated by AgentFlow (safe to delete)."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    # New marker present?
    from .templates import AGENTFLOW_GENERATED_MARKER
    if AGENTFLOW_GENERATED_MARKER in content:
        return True
    # Legacy detection: files generated before the marker was added.
    if "# AgentFlow for" in content and "thin platform entrypoint" in content:
        return True
    return False


def _prune_empty_parents(directory: Path, stop_at: Path) -> None:
    """Remove empty parent directories up to (but NOT including) the top-level
    editor folder directly under ``stop_at``.

    Example: for ``.cursor/skills/agentflow/``, this may remove
    ``agentflow/`` and ``skills/`` if empty, but never ``.cursor/``.
    """
    current = directory
    # The top-level folder (first component under project root) must be kept.
    try:
        relative = current.relative_to(stop_at)
    except ValueError:
        return
    top_level = stop_at / relative.parts[0] if relative.parts else stop_at

    while current != top_level and current != stop_at:
        try:
            if any(current.iterdir()):
                break
            current.rmdir()
        except OSError:
            break
        current = current.parent
