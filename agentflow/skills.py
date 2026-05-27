"""Global skill registry and installer helpers for AgentFlow."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import templates


CONFIG_FILE = "config.yaml"
LOCK_FILE = "skills.lock.yaml"

GLOBAL_LINK_NAME = "_global"
GLOBAL_LINK_FALLBACK_FILE = ".global-link.txt"


@dataclass(frozen=True)
class SkillInfo:
    name: str
    description: str
    path: Path
    source: str = ""


def agentflow_home(home: str | Path | None = None) -> Path:
    """Return the global AgentFlow home directory."""

    if home is not None:
        return Path(home)
    configured = os.environ.get("AGENTFLOW_HOME")
    if configured:
        return Path(configured)
    return Path.home() / ".agentflow"


def default_skill_root(home: str | Path | None = None) -> Path:
    return agentflow_home(home) / "skills"


def bind_skill_root(skill_root: str | Path, home: str | Path | None = None) -> Path:
    """Bind the global skill root in the AgentFlow config."""

    root = Path(skill_root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    global_home = agentflow_home(home)
    global_home.mkdir(parents=True, exist_ok=True)
    _write_config(global_home / CONFIG_FILE, [root])
    return root


def get_skill_roots(home: str | Path | None = None) -> list[Path]:
    """Read configured skill roots, creating the default if needed."""

    global_home = agentflow_home(home)
    config_path = global_home / CONFIG_FILE
    if not config_path.exists():
        return [bind_skill_root(default_skill_root(global_home), home=global_home)]

    roots = _read_config(config_path)
    if not roots:
        return [bind_skill_root(default_skill_root(global_home), home=global_home)]

    for root in roots:
        root.mkdir(parents=True, exist_ok=True)
    return roots


def discover_global_skills(home: str | Path | None = None) -> list[SkillInfo]:
    """Discover all global skills under configured skill roots."""

    skills: list[SkillInfo] = []
    seen: set[str] = set()
    for root in get_skill_roots(home):
        if not root.exists():
            continue
        for candidate in sorted(root.iterdir(), key=lambda item: item.name.lower()):
            skill_file = candidate / "SKILL.md"
            if not candidate.is_dir() or not skill_file.is_file():
                continue
            info = read_skill_info(skill_file)
            if info.name in seen:
                continue
            seen.add(info.name)
            skills.append(info)
    return skills


def read_skill_info(skill_file: str | Path) -> SkillInfo:
    """Read name and description from a SKILL.md file."""

    path = Path(skill_file)
    text = path.read_text(encoding="utf-8-sig")
    metadata = _parse_frontmatter(text)
    name = metadata.get("name") or path.parent.name
    description = metadata.get("description") or _first_heading_or_sentence(text)
    return SkillInfo(name=_slug(name), description=description, path=path)


def import_local_skill(
    source: str | Path,
    home: str | Path | None = None,
    source_label: str | None = None,
) -> SkillInfo:
    """Import a local skill directory or SKILL.md into the global root."""

    source_path = Path(source).expanduser()
    skill_dir = _find_skill_directory(source_path)
    info = read_skill_info(skill_dir / "SKILL.md")
    target_root = get_skill_roots(home)[0]
    target_dir = (target_root / info.name).resolve()
    _ensure_child(target_dir, target_root.resolve())

    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(skill_dir, target_dir)

    installed = SkillInfo(
        name=info.name,
        description=info.description,
        path=target_dir / "SKILL.md",
        source=source_label or str(source_path),
    )
    _update_lock(installed, home=home)
    return installed


def import_zip_skill(zip_path: str | Path, home: str | Path | None = None) -> SkillInfo:
    """Import a skill from a zip archive."""

    archive = Path(zip_path).expanduser()
    with tempfile.TemporaryDirectory() as directory:
        extract_dir = Path(directory)
        _safe_extract_zip(archive, extract_dir)
        return import_local_skill(extract_dir, home=home, source_label=f"zip:{archive}")


def install_npm_skill(package: str, home: str | Path | None = None) -> SkillInfo:
    """Download an npm skill package with scripts disabled and import it."""

    package_name = _normalize_npm_package(package)
    global_home = agentflow_home(home)
    cache_dir = global_home / "cache" / "npm"
    cache_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "npm",
        "pack",
        package_name,
        "--ignore-scripts",
        "--pack-destination",
        str(cache_dir),
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "npm pack failed")

    filename = result.stdout.strip().splitlines()[-1].strip()
    tarball = cache_dir / filename
    if not tarball.exists():
        matches = sorted(cache_dir.glob("*.tgz"), key=lambda item: item.stat().st_mtime)
        if not matches:
            raise RuntimeError("npm pack did not produce a .tgz file")
        tarball = matches[-1]

    with tempfile.TemporaryDirectory() as directory:
        extract_dir = Path(directory)
        _safe_extract_tar(tarball, extract_dir)
        return import_local_skill(extract_dir, home=home, source_label=f"npm:{package_name}")


def install_github_skill(spec: str, home: str | Path | None = None) -> SkillInfo:
    """Clone a GitHub repo or repo subdirectory and import the skill."""

    owner, repo, subpath = _parse_github_source(spec)
    url = f"https://github.com/{owner}/{repo}.git"
    with tempfile.TemporaryDirectory() as directory:
        checkout = Path(directory) / "repo"
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(checkout)],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git clone failed")
        source = checkout / subpath if subpath else checkout
        return import_local_skill(source, home=home, source_label=f"github:{spec}")


def install_npx_skill_command(
    args: list[str],
    home: str | Path | None = None,
) -> SkillInfo | list[SkillInfo]:
    """Install from the common `npx skills add <source>` command shape.

    Flow does not execute arbitrary npx commands. It recognizes the skill-add
    command shape and performs the install itself, so no package scripts run.
    """

    if len(args) < 3 or args[0].lower() != "skills" or args[1].lower() != "add":
        raise ValueError("Supported format: npx skills add <source> (--skill <name> | --all)")

    source = args[2]
    all_requested = _has_all_flag(args[3:])
    skill_name = _extract_skill_name(args[3:])
    if all_requested and skill_name:
        raise ValueError("Use either --skill <name> or --all, not both")
    if all_requested:
        return install_all_skill_source(source, home=home)
    if not skill_name:
        raise ValueError("Missing --skill <name> or --all")

    return install_named_skill_source(source, skill_name, home=home)


def install_all_skill_source(
    source: str,
    home: str | Path | None = None,
) -> list[SkillInfo]:
    """Install every unique ``SKILL.md`` found in a source."""

    value = source.strip()
    if value.startswith("npm:"):
        return _install_all_npm_skills(value.removeprefix("npm:"), home=home)
    if value.startswith("github:"):
        return _install_all_github_skills(value.removeprefix("github:"), home=home)
    if value.startswith("gh:"):
        return _install_all_github_skills(value.removeprefix("gh:"), home=home)
    if value.startswith("zip:"):
        return _install_all_zip_skills(value.removeprefix("zip:"), home=home)
    if value.startswith("local:"):
        return _install_all_local_skills(value.removeprefix("local:"), home=home, source_label=value)

    github_source = _try_parse_github_source(value)
    if github_source:
        return _install_all_github_skills(value, home=home)

    return _install_all_local_skills(value, home=home, source_label=value)


def install_named_skill_source(
    source: str,
    skill_name: str,
    home: str | Path | None = None,
) -> SkillInfo:
    """Install one named skill from a GitHub repo URL, owner/repo, or local folder."""

    github_source = _try_parse_github_source(source)
    if github_source:
        owner, repo, subpath = github_source
        url = f"https://github.com/{owner}/{repo}.git"
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory) / "repo"
            result = subprocess.run(
                ["git", "clone", "--depth", "1", url, str(checkout)],
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git clone failed")
            root = checkout / subpath if subpath else checkout
            skill_dir = _find_named_skill_directory(root, skill_name)
            return import_local_skill(
                skill_dir,
                home=home,
                source_label=f"npx-skills:{source}#{skill_name}",
            )

    root = Path(source).expanduser()
    skill_dir = _find_named_skill_directory(root, skill_name)
    return import_local_skill(
        skill_dir,
        home=home,
        source_label=f"npx-skills:{source}#{skill_name}",
    )


def _install_all_local_skills(
    source: str | Path,
    home: str | Path | None = None,
    source_label: str | None = None,
) -> list[SkillInfo]:
    root = Path(source).expanduser()
    skill_dirs = _find_all_skill_directories(root)
    installed: list[SkillInfo] = []
    for skill_dir in skill_dirs:
        installed.append(
            import_local_skill(
                skill_dir,
                home=home,
                source_label=source_label or str(root),
            )
        )
    return installed


def _install_all_zip_skills(
    zip_path: str | Path,
    home: str | Path | None = None,
) -> list[SkillInfo]:
    archive = Path(zip_path).expanduser()
    with tempfile.TemporaryDirectory() as directory:
        extract_dir = Path(directory)
        _safe_extract_zip(archive, extract_dir)
        return _install_all_local_skills(
            extract_dir,
            home=home,
            source_label=f"zip:{archive}",
        )


def _install_all_npm_skills(
    package: str,
    home: str | Path | None = None,
) -> list[SkillInfo]:
    package_name = _normalize_npm_package(package)
    global_home = agentflow_home(home)
    cache_dir = global_home / "cache" / "npm"
    cache_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "npm",
        "pack",
        package_name,
        "--ignore-scripts",
        "--pack-destination",
        str(cache_dir),
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "npm pack failed")

    filename = result.stdout.strip().splitlines()[-1].strip()
    tarball = cache_dir / filename
    if not tarball.exists():
        matches = sorted(cache_dir.glob("*.tgz"), key=lambda item: item.stat().st_mtime)
        if not matches:
            raise RuntimeError("npm pack did not produce a .tgz file")
        tarball = matches[-1]

    with tempfile.TemporaryDirectory() as directory:
        extract_dir = Path(directory)
        _safe_extract_tar(tarball, extract_dir)
        return _install_all_local_skills(
            extract_dir,
            home=home,
            source_label=f"npm:{package_name}",
        )


def _install_all_github_skills(
    spec: str,
    home: str | Path | None = None,
) -> list[SkillInfo]:
    owner, repo, subpath = _parse_github_source(spec)
    url = f"https://github.com/{owner}/{repo}.git"
    with tempfile.TemporaryDirectory() as directory:
        checkout = Path(directory) / "repo"
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(checkout)],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git clone failed")
        root = checkout / subpath if subpath else checkout
        return _install_all_local_skills(root, home=home, source_label=f"github:{spec}#all")


def install_skill_source(source: str, home: str | Path | None = None) -> SkillInfo:
    """Install a skill from local:, zip:, npm:, github:/gh: or a plain path."""

    if source.startswith("npm:"):
        return install_npm_skill(source.removeprefix("npm:"), home=home)
    if source.startswith("github:"):
        return install_github_skill(source.removeprefix("github:"), home=home)
    if source.startswith("gh:"):
        return install_github_skill(source.removeprefix("gh:"), home=home)
    if source.startswith("zip:"):
        return import_zip_skill(source.removeprefix("zip:"), home=home)
    if source.startswith("local:"):
        return import_local_skill(source.removeprefix("local:"), home=home)
    return import_local_skill(source, home=home)


def sync_project_skill_index(
    project_dir: str | Path,
    home: str | Path | None = None,
) -> dict[str, object]:
    """Render global skills into the project's canonical skill index."""

    root = Path(project_dir)
    skills = discover_global_skills(home=home)
    skill_roots = get_skill_roots(home=home)
    index_path = root / ".agentflow" / "skills" / "SKILL.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    link_target = _read_global_link_target(root)
    rebased = _rebase_skills_via_link(skills, link_target) if link_target else skills

    index_path.write_text(
        templates.skill_index(global_skills=rebased, skill_roots=skill_roots),
        encoding="utf-8",
    )
    return {"path": str(index_path), "synced": len(skills)}


def link_global_skills_dir(
    project_dir: str | Path,
    home: str | Path | None = None,
) -> dict[str, object]:
    """Make the global skill folder reachable from inside the project tree.

    The preferred mechanism is a symbolic link at
    ``<project>/.agentflow/skills/_global`` pointing at the first configured
    skill root. On Windows without symlink permission a directory junction is
    used instead. If neither succeeds, a small marker file records the absolute
    target so the index falls back to absolute paths gracefully.
    """
    root = Path(project_dir)
    skills_dir = root / ".agentflow" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    link_path = skills_dir / GLOBAL_LINK_NAME
    fallback_path = skills_dir / GLOBAL_LINK_FALLBACK_FILE

    target_roots = get_skill_roots(home=home)
    target = target_roots[0] if target_roots else default_skill_root(home)
    target = Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    _remove_path(link_path)

    method = "absolute"
    error: str | None = None
    try:
        os.symlink(str(target), str(link_path), target_is_directory=True)
        method = "symlink"
    except (OSError, NotImplementedError) as exc:
        error = str(exc)
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link_path), str(target)],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                if result.returncode == 0:
                    method = "junction"
                    error = None
                else:
                    error = result.stderr.strip() or result.stdout.strip() or "mklink failed"
            except OSError as junction_exc:
                error = str(junction_exc)

    if method == "absolute":
        # Persist a marker so the index can still annotate the resolved target.
        fallback_path.write_text(str(target), encoding="utf-8")
    elif fallback_path.exists():
        try:
            fallback_path.unlink()
        except OSError:
            pass

    _ensure_gitignore_entry(root, ".agentflow/skills/_global")

    return {
        "method": method,
        "target": str(target),
        "link": str(link_path),
        "error": error,
    }


def get_global_link_status(
    project_dir: str | Path,
    home: str | Path | None = None,
) -> dict[str, object]:
    """Return whether the project has a working global skills link."""
    root = Path(project_dir)
    link_path = root / ".agentflow" / "skills" / GLOBAL_LINK_NAME
    target = _read_global_link_target(root)
    method = "missing"
    if link_path.is_symlink():
        method = "symlink"
    elif link_path.exists() and target is not None:
        method = "junction"
    elif (root / ".agentflow" / "skills" / GLOBAL_LINK_FALLBACK_FILE).exists():
        method = "absolute"
    return {
        "method": method,
        "link": str(link_path),
        "target": str(target) if target else "",
        "exists": link_path.exists(),
    }


def _read_global_link_target(project_dir: Path) -> Path | None:
    """Return the absolute target of the project's _global link, if any."""
    link_path = project_dir / ".agentflow" / "skills" / GLOBAL_LINK_NAME
    if link_path.is_symlink():
        try:
            resolved = link_path.resolve(strict=False)
            return resolved
        except OSError:
            return None
    if link_path.exists() and link_path.is_dir():
        return link_path.resolve()
    return None


def _rebase_skills_via_link(
    skills: list[SkillInfo], link_target: Path
) -> list[SkillInfo]:
    """Rewrite skill paths to go through the in-project ``_global`` link."""
    rebased: list[SkillInfo] = []
    target_resolved = link_target.resolve()
    for skill in skills:
        try:
            relative = skill.path.resolve().relative_to(target_resolved)
        except ValueError:
            rebased.append(skill)
            continue
        new_path = Path(".agentflow") / "skills" / GLOBAL_LINK_NAME / relative
        rebased.append(
            SkillInfo(
                name=skill.name,
                description=skill.description,
                path=Path(str(new_path).replace("\\", "/")),
                source=skill.source,
            )
        )
    return rebased


def _remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    try:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    except OSError:
        # Last-ditch attempt: rename out of the way.
        try:
            path.replace(path.with_suffix(path.suffix + ".old"))
        except OSError:
            pass


def _ensure_gitignore_entry(project_dir: Path, entry: str) -> None:
    gitignore = project_dir / ".gitignore"
    line = entry.replace("\\", "/")
    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8").splitlines()
        if any(item.strip() == line for item in existing):
            return
        if existing and existing[-1] != "":
            existing.append("")
        existing.append(line)
        gitignore.write_text("\n".join(existing) + "\n", encoding="utf-8")
    else:
        gitignore.write_text(line + "\n", encoding="utf-8")


def describe_skill_home(home: str | Path | None = None) -> dict[str, object]:
    """Return a small status object for the global skill home."""

    global_home = agentflow_home(home)
    roots = get_skill_roots(home=global_home)
    skills = discover_global_skills(home=global_home)
    return {
        "home": str(global_home),
        "skill_roots": [str(root) for root in roots],
        "skills": [skill.name for skill in skills],
    }


def _write_config(path: Path, roots: list[Path]) -> None:
    lines = ["skill_roots:"]
    for root in roots:
        normalized = str(root).replace("\\", "/")
        lines.append(f'  - "{normalized}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_config(path: Path) -> list[Path]:
    roots: list[Path] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        value = stripped[1:].strip().strip('"').strip("'")
        if value:
            roots.append(Path(value))
    return roots


def _parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    metadata: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def _first_heading_or_sentence(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if stripped and not stripped.startswith("---"):
            return stripped[:120]
    return "No description provided."


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip().lower()).strip("-")
    return slug or "skill"


def _find_skill_directory(source: Path) -> Path:
    if source.is_file() and source.name.lower() == "skill.md":
        return source.parent
    if (source / "SKILL.md").is_file():
        return source
    matches = sorted(source.rglob("SKILL.md"))
    if matches:
        return matches[0].parent
    raise FileNotFoundError(f"No SKILL.md found in {source}")


def _ensure_child(path: Path, parent: Path) -> None:
    path.relative_to(parent)


def _update_lock(skill: SkillInfo, home: str | Path | None = None) -> None:
    global_home = agentflow_home(home)
    global_home.mkdir(parents=True, exist_ok=True)
    lock_path = global_home / LOCK_FILE
    existing = _read_lock(lock_path)
    existing[skill.name] = skill
    lines = ["skills:"]
    for name in sorted(existing):
        item = existing[name]
        item_path = str(item.path).replace("\\", "/")
        lines.extend(
            [
                f"  {name}:",
                f'    path: "{item_path}"',
                f'    source: "{item.source}"',
            ]
        )
    lock_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_lock(path: Path) -> dict[str, SkillInfo]:
    if not path.exists():
        return {}
    entries: dict[str, SkillInfo] = {}
    current: str | None = None
    current_path = ""
    current_source = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            if current:
                entries[current] = SkillInfo(current, "", Path(current_path), current_source)
            current = line.strip().rstrip(":")
            current_path = ""
            current_source = ""
        elif current and line.strip().startswith("path:"):
            current_path = line.split(":", 1)[1].strip().strip('"')
        elif current and line.strip().startswith("source:"):
            current_source = line.split(":", 1)[1].strip().strip('"')
    if current:
        entries[current] = SkillInfo(current, "", Path(current_path), current_source)
    return entries


def _normalize_npm_package(package: str) -> str:
    package = package.strip()
    if package.startswith("@") or "/" in package:
        return package
    return f"@agentflow-skill/{package}"


def _parse_github_spec(spec: str) -> tuple[str, str, Path | None]:
    parts = [part for part in spec.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub source must look like owner/repo or owner/repo/path")
    owner, repo = parts[0], parts[1]
    subpath = Path(*parts[2:]) if len(parts) > 2 else None
    return owner, repo, subpath


def _try_parse_github_source(source: str) -> tuple[str, str, Path | None] | None:
    value = source.strip().strip('"').strip("'")
    for prefix in ("https://github.com/", "http://github.com/"):
        if value.startswith(prefix):
            value = value.removeprefix(prefix)
            value = value.split("?", 1)[0].split("#", 1)[0].strip("/")
            parts = [part for part in value.split("/") if part]
            if len(parts) < 2:
                return None
            owner, repo = parts[0], parts[1]
            if repo.endswith(".git"):
                repo = repo[:-4]
            rest = parts[2:]
            if rest[:1] in (["tree"], ["blob"]):
                rest = rest[2:] if len(rest) >= 2 else []
            subpath = Path(*rest) if rest else None
            return owner, repo, subpath

    if value.startswith("git@github.com:"):
        value = value.removeprefix("git@github.com:").removesuffix(".git")
        try:
            return _parse_github_spec(value)
        except ValueError:
            return None

    if (
        "\\" in value
        or re.match(r"^[a-zA-Z]:", value)
        or value.startswith((".", "~", "/"))
        or Path(value).expanduser().exists()
    ):
        return None

    try:
        return _parse_github_spec(value)
    except ValueError:
        return None


def _parse_github_source(spec: str) -> tuple[str, str, Path | None]:
    parsed = _try_parse_github_source(spec)
    if parsed is None:
        raise ValueError("GitHub source must look like owner/repo or a GitHub URL")
    return parsed


def _extract_skill_name(args: list[str]) -> str | None:
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--skill":
            if index + 1 >= len(args):
                return None
            return args[index + 1]
        if token.startswith("--skill="):
            return token.split("=", 1)[1]
        index += 1
    return None


def _has_all_flag(args: list[str]) -> bool:
    return any(token == "--all" for token in args)


def _find_named_skill_directory(source: Path, skill_name: str) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"Skill source does not exist: {source}")

    expected = _slug(skill_name)
    matches = []
    for skill_file in sorted(source.rglob("SKILL.md")):
        info = read_skill_info(skill_file)
        parent_name = _slug(skill_file.parent.name)
        if info.name == expected or parent_name == expected:
            matches.append(skill_file.parent)

    if matches:
        return matches[0]

    raise FileNotFoundError(f"No skill named {skill_name!r} found in {source}")


def _find_all_skill_directories(source: Path) -> list[Path]:
    if source.is_file() and source.name.lower() == "skill.md":
        return [source.parent]
    if not source.exists():
        raise FileNotFoundError(f"Skill source does not exist: {source}")

    skill_files = sorted(source.rglob("SKILL.md"))
    if not skill_files:
        raise FileNotFoundError(f"No SKILL.md found in {source}")

    directories: list[Path] = []
    seen_names: set[str] = set()
    seen_dirs: set[Path] = set()
    for skill_file in skill_files:
        skill_dir = skill_file.parent
        resolved = skill_dir.resolve()
        if resolved in seen_dirs:
            continue
        info = read_skill_info(skill_file)
        if info.name in seen_names:
            continue
        seen_dirs.add(resolved)
        seen_names.add(info.name)
        directories.append(skill_dir)
    return directories


def _safe_extract_zip(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            target = (destination / member.filename).resolve()
            _ensure_child(target, destination.resolve())
        zf.extractall(destination)


def _safe_extract_tar(archive: Path, destination: Path) -> None:
    with tarfile.open(archive) as tf:
        for member in tf.getmembers():
            target = (destination / member.name).resolve()
            _ensure_child(target, destination.resolve())
        try:
            tf.extractall(destination, filter="data")
        except TypeError:
            tf.extractall(destination)
