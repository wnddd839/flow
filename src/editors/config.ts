import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import {
  PLATFORM_DISPLAY,
  PLATFORM_ENTRYPOINTS,
  type PlatformName,
} from "../templates.js";

export const EDITOR_CONFIG_FILE = "editors.yaml";

export interface EditorConfig {
  enabled: string[];
  custom: Record<string, { display?: string; path?: string }>;
}

export interface EditorSpec {
  name: string;
  display: string;
  entrypoint: string;
  custom: boolean;
}

/**
 * Resolve the editor config for a given context.
 *
 * Resolution order on READ:
 *   1. project-level `.agentflow/editors.yaml` (if it exists)
 *   2. global `~/.agentflow/editors.yaml` (or AGENTFLOW_HOME)
 *
 * On WRITE, `target.projectDir` makes us write the project-level file so
 * `flow init` no longer mutates a shared global config that silently leaks
 * across projects (the v1-era "I lost my other project's editors" bug).
 */
export interface ConfigTarget {
  /** When set, project-level config is preferred (read) or written. */
  projectDir?: string;
  /** Global home override (mainly for tests). */
  home?: string;
}

export function agentflowHome(home?: string): string {
  if (home) return home;
  const configured = process.env.AGENTFLOW_HOME;
  return configured ? configured : join(homedir(), ".agentflow");
}

function globalConfigPath(home?: string): string {
  return join(agentflowHome(home), EDITOR_CONFIG_FILE);
}

/** Project-level config path, or null when no project context is given. */
function projectConfigPath(projectDir?: string): string | null {
  if (!projectDir) return null;
  return join(resolve(projectDir), ".agentflow", EDITOR_CONFIG_FILE);
}

/**
 * Load editor config with project-level priority.
 *
 * - If a project-level `.agentflow/editors.yaml` exists, it fully replaces
 *   the global config for this project.
 * - Otherwise the global `~/.agentflow/editors.yaml` is used.
 */
export function loadEditorConfig(target?: ConfigTarget): EditorConfig {
  const projectPath = projectConfigPath(target?.projectDir);
  const path =
    projectPath && existsSync(projectPath)
      ? projectPath
      : globalConfigPath(target?.home);
  return parseConfigFile(path);
}

/**
 * Save editor config. Writes project-level when `target.projectDir` is set,
 * otherwise the global home. This keeps per-project editor choices out of
 * the shared global config.
 */
export function saveEditorConfig(
  enabled: Iterable<string>,
  custom: EditorConfig["custom"] = {},
  target?: ConfigTarget,
): string {
  let path: string;
  if (target?.projectDir) {
    const projectPath = projectConfigPath(target.projectDir);
    path = projectPath ?? globalConfigPath(target.home);
  } else {
    path = globalConfigPath(target?.home);
  }
  writeConfigFile(path, enabled, custom);
  return path;
}

function parseConfigFile(path: string): EditorConfig {
  const enabled: string[] = [];
  const custom: EditorConfig["custom"] = {};

  if (!existsSync(path)) {
    return { enabled, custom };
  }

  let section: string | null = null;
  let currentCustom: string | null = null;

  for (const rawLine of readFileSync(path, "utf8").split("\n")) {
    const line = rawLine.replace(/\r$/, "");
    if (!line.trim()) continue;

    if (!line.startsWith(" ")) {
      section = line.replace(/:$/, "").trim().toLowerCase();
      currentCustom = null;
      continue;
    }

    const stripped = line.trim();
    if (section === "enabled" && stripped.startsWith("-")) {
      const value = stripped
        .slice(1)
        .trim()
        .replace(/^["']|["']$/g, "");
      if (value) enabled.push(value);
    } else if (section === "custom") {
      const indent = line.length - line.trimStart().length;
      if (indent === 2 && stripped.endsWith(":")) {
        currentCustom = stripped.slice(0, -1).trim();
        custom[currentCustom] = {};
      } else if (currentCustom && stripped.includes(":")) {
        const colon = stripped.indexOf(":");
        const key = stripped.slice(0, colon).trim();
        const value = stripped
          .slice(colon + 1)
          .trim()
          .replace(/^["']|["']$/g, "");
        if (key === "display" || key === "path") {
          custom[currentCustom][key] = value;
        }
      }
    }
  }

  return { enabled, custom };
}

function writeConfigFile(
  path: string,
  enabled: Iterable<string>,
  custom: EditorConfig["custom"],
): void {
  mkdirSync(dirname(path), { recursive: true });

  const lines = ["enabled:"];
  for (const name of enabled) {
    lines.push(`  - "${name}"`);
  }
  lines.push("custom:");
  for (const name of Object.keys(custom).sort()) {
    const spec = custom[name] ?? {};
    lines.push(`  ${name}:`);
    for (const key of ["display", "path"] as const) {
      lines.push(`    ${key}: "${spec[key] ?? ""}"`);
    }
  }

  writeFileSync(path, `${lines.join("\n")}\n`, "utf8");
}

function builtinEditors(): Record<string, EditorSpec> {
  const catalog: Record<string, EditorSpec> = {};
  for (const name of Object.keys(PLATFORM_DISPLAY) as PlatformName[]) {
    catalog[name] = {
      name,
      display: PLATFORM_DISPLAY[name],
      entrypoint: PLATFORM_ENTRYPOINTS[name],
      custom: false,
    };
  }
  return catalog;
}

export function normalizeEditorNames(names: Iterable<string>): string[] {
  const catalog = builtinEditors();
  const normalized: string[] = [];
  for (const raw of names) {
    const name = String(raw).trim().toLowerCase();
    if (!name) continue;
    if (!(name in catalog)) {
      const known = Object.keys(catalog).sort().join(", ");
      throw new Error(
        `Unknown editor: ${JSON.stringify(raw)}. Known editors: ${known}`,
      );
    }
    if (!normalized.includes(name)) normalized.push(name);
  }
  return normalized;
}

export function allEditors(target?: ConfigTarget): Record<string, EditorSpec> {
  const config = loadEditorConfig(target);
  const catalog = builtinEditors();
  for (const [name, spec] of Object.entries(config.custom)) {
    catalog[name] = {
      name,
      display: spec.display || name[0]?.toUpperCase() + name.slice(1),
      entrypoint: spec.path || `.${name}/skills/agentflow/SKILL.md`,
      custom: true,
    };
  }
  return catalog;
}

export function getEnabledEditors(target?: ConfigTarget): EditorSpec[] {
  const config = loadEditorConfig(target);
  const catalog = allEditors(target);
  const enabled: EditorSpec[] = [];
  const seen = new Set<string>();
  for (const name of config.enabled) {
    if (name in catalog && !seen.has(name)) {
      enabled.push(catalog[name]);
      seen.add(name);
    }
  }
  return enabled;
}

export function enableEditor(name: string, target?: ConfigTarget): EditorSpec {
  const catalog = allEditors(target);
  if (!(name in catalog)) {
    throw new Error(
      `Unknown editor: ${name}. Use 'flow editors add-custom' first.`,
    );
  }
  const config = loadEditorConfig(target);
  if (!config.enabled.includes(name)) {
    config.enabled.push(name);
    saveEditorConfig(config.enabled, config.custom, target);
  }
  return catalog[name];
}

export function disableEditor(name: string, target?: ConfigTarget): void {
  const config = loadEditorConfig(target);
  if (config.enabled.includes(name)) {
    config.enabled = config.enabled.filter((item) => item !== name);
    saveEditorConfig(config.enabled, config.custom, target);
  }
}

export function validateRelativeEntrypoint(entrypoint: string): string {
  const cleaned = String(entrypoint).trim();
  if (!cleaned) throw new Error("Editor entrypoint path is required");
  if (cleaned.startsWith("/") || /^[A-Za-z]:[\\/]/.test(cleaned)) {
    throw new Error(
      `Editor entrypoint must be a project-relative path: ${JSON.stringify(entrypoint)}`,
    );
  }
  const posix = cleaned.replace(/\\/g, "/");
  const parts = posix.split("/").filter((part) => part.length > 0);
  if (parts.some((part) => part === "..")) {
    throw new Error(
      `Editor entrypoint must not contain '..': ${JSON.stringify(entrypoint)}`,
    );
  }
  if (
    !parts.length ||
    posix.endsWith("/") ||
    parts.at(-1) === "." ||
    parts.at(-1) === ".."
  ) {
    throw new Error(
      `Editor entrypoint must include a file name: ${JSON.stringify(entrypoint)}`,
    );
  }
  return cleaned;
}

export function addCustomEditor(
  name: string,
  entrypoint: string,
  display?: string,
  target?: ConfigTarget,
): EditorSpec {
  if (!name.trim()) throw new Error("Editor name is required");
  const cleanedEntrypoint = validateRelativeEntrypoint(entrypoint);
  const config = loadEditorConfig(target);
  config.custom[name] = {
    display: display || name[0]?.toUpperCase() + name.slice(1),
    path: cleanedEntrypoint,
  };
  if (!config.enabled.includes(name)) {
    config.enabled.push(name);
  }
  saveEditorConfig(config.enabled, config.custom, target);
  return {
    name,
    display: display || name[0]?.toUpperCase() + name.slice(1),
    entrypoint: cleanedEntrypoint,
    custom: true,
  };
}

export function removeCustomEditor(name: string, target?: ConfigTarget): void {
  const config = loadEditorConfig(target);
  delete config.custom[name];
  config.enabled = config.enabled.filter((item) => item !== name);
  saveEditorConfig(config.enabled, config.custom, target);
}
