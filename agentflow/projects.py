"""Registered project tracking for AgentFlow.

A registered project is one Flow knows about so it can run batch operations
(re-link the global skill folder, refresh the skill index) without you having
to walk into each project. The registry lives at user level::

    ~/.agentflow/projects.yaml
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .skills import agentflow_home


PROJECTS_FILE = "projects.yaml"


@dataclass(frozen=True)
class ProjectEntry:
    name: str
    path: Path
    key: str = ""


def _registry_path(home: str | Path | None = None) -> Path:
    return agentflow_home(home) / PROJECTS_FILE


def _key_for(name: str, path: Path) -> str:
    """Deterministic registry key derived from name + resolved path.

    The key is unique per path, so two projects sharing a directory name in
    different locations cannot collide on a single YAML key.
    """
    safe_name = "".join(
        ch if (ch.isalnum() or ch in "-_") else "_" for ch in (name or "")
    ).strip("_") or "project"
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:8]
    return f"{safe_name}-{digest}"


def list_projects(home: str | Path | None = None) -> list[ProjectEntry]:
    """Return every project currently registered.

    The on-disk format uses unique keys with a nested ``name`` field, but a
    legacy format that uses the display name directly as the key (and omits
    the ``name`` field) is also supported for backward compatibility.
    """
    path = _registry_path(home)
    if not path.exists():
        return []

    entries: list[ProjectEntry] = []
    current_key: str | None = None
    current_name: str = ""
    current_path: str = ""

    def _flush() -> None:
        nonlocal current_key, current_name, current_path
        if current_key and current_path:
            display = current_name or current_key
            entries.append(
                ProjectEntry(display, Path(current_path), current_key)
            )
        current_key = None
        current_name = ""
        current_path = ""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if not line.startswith(" ") and line.strip().lower() == "projects:":
            continue

        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if indent == 2 and stripped.endswith(":"):
            _flush()
            current_key = stripped.rstrip(":").strip()
        elif indent >= 4 and ":" in stripped and current_key is not None:
            key, value = stripped.split(":", 1)
            value_clean = value.strip().strip('"').strip("'")
            field_name = key.strip()
            if field_name == "path":
                current_path = value_clean
            elif field_name == "name":
                current_name = value_clean
    _flush()
    return entries


def _save_projects(entries: list[ProjectEntry], home: str | Path | None = None) -> Path:
    path = _registry_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["projects:"]
    seen_keys: set[str] = set()
    for entry in entries:
        key = entry.key or _key_for(entry.name, entry.path)
        # Guard against accidental key collisions when two entries share a
        # path-derived key (extremely unlikely, but keep YAML keys unique).
        unique_key = key
        suffix = 2
        while unique_key in seen_keys:
            unique_key = f"{key}-{suffix}"
            suffix += 1
        seen_keys.add(unique_key)
        lines.append(f"  {unique_key}:")
        lines.append(f'    name: "{entry.name}"')
        normalized = str(entry.path).replace("\\", "/")
        lines.append(f'    path: "{normalized}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def register_project(
    project_dir: str | Path,
    name: str | None = None,
    home: str | Path | None = None,
) -> ProjectEntry:
    """Add the given project to the registry.

    De-duplication is by resolved path (not name), so two projects with the
    same directory name in different locations can coexist under separate
    unique YAML keys.
    """
    root = Path(project_dir).resolve()
    project_name = (name or root.name or "project").strip() or root.name
    # Keep entries whose resolved path differs from the new one.
    entries = [
        item for item in list_projects(home)
        if item.path.resolve() != root
    ]
    new_entry = ProjectEntry(project_name, root, _key_for(project_name, root))
    entries.append(new_entry)
    entries.sort(key=lambda item: (item.name.lower(), item.key))
    _save_projects(entries, home=home)
    return new_entry


def unregister_project(name: str, home: str | Path | None = None) -> bool:
    """Remove a project from the registry.

    Resolution order:
    1. Exact unique-key match (preferred and unambiguous).
    2. Single display-name match (legacy convenience).
    3. If multiple entries share the display name, refuse and return False;
       the caller must disambiguate via the unique key.
    """
    entries = list_projects(home)
    by_key = [item for item in entries if item.key == name]
    if by_key:
        target_keys = {item.key for item in by_key}
        remaining = [item for item in entries if item.key not in target_keys]
        _save_projects(remaining, home=home)
        return True

    by_name = [item for item in entries if item.name == name]
    if not by_name:
        return False
    if len(by_name) > 1:
        # Ambiguous: refuse to delete to avoid wiping multiple projects.
        return False
    target_key = by_name[0].key
    remaining = [item for item in entries if item.key != target_key]
    _save_projects(remaining, home=home)
    return True


def sync_all_projects(home: str | Path | None = None) -> dict[str, object]:
    """Re-link the global skills folder and refresh the index for every project."""
    from .skills import sync_project_skill_index, link_global_skills_dir

    results: list[dict[str, object]] = []
    skipped: list[str] = []
    for entry in list_projects(home):
        if not entry.path.exists() or not (entry.path / ".agentflow").exists():
            skipped.append(entry.name)
            continue
        link_info = link_global_skills_dir(entry.path, home=home)
        sync_info = sync_project_skill_index(entry.path, home=home)
        results.append(
            {
                "name": entry.name,
                "path": str(entry.path),
                "link": link_info,
                "synced": sync_info["synced"],
            }
        )
    return {"results": results, "skipped": skipped}
