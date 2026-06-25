import {
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { dirname, relative, resolve } from "node:path";
import {
  AGENTFLOW_GENERATED_MARKER,
  rootAgentsPointer,
  thinEntrypoint,
} from "../templates.js";
import { allEditors, getEnabledEditors } from "./config.js";

export interface ApplyEditorsResult {
  created: string[];
  kept: string[];
  removed: string[];
  skipped: string[];
}

export function safeProjectPath(
  root: string,
  candidate: string,
): string | null {
  const cleaned = String(candidate).trim();
  if (!cleaned) return null;
  if (cleaned.startsWith("/") || /^[A-Za-z]:[\\/]/.test(cleaned)) {
    return null;
  }
  const posix = cleaned.replace(/\\/g, "/");
  if (posix.split("/").some((part) => part === "..")) {
    return null;
  }
  try {
    const resolvedRoot = resolve(root);
    const resolvedTarget = resolve(resolvedRoot, cleaned);
    const rel = relative(resolvedRoot, resolvedTarget);
    if (rel.startsWith("..")) {
      return null;
    }
    return resolvedTarget;
  } catch {
    return null;
  }
}

function isAgentflowEntrypoint(path: string): boolean {
  try {
    const content = readFileSync(path, "utf8");
    if (content.includes(AGENTFLOW_GENERATED_MARKER)) return true;
    if (content.includes("本项目规范见 `.agentflow/AGENTS.md`")) return true;
    if (
      content.includes("# AgentFlow for") &&
      content.includes("thin platform entrypoint")
    ) {
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

function pruneEmptyParents(directory: string, stopAt: string): void {
  let current = directory;
  const resolvedStop = resolve(stopAt);
  const rel = relative(resolvedStop, current);
  if (rel.startsWith("..")) return;

  const topLevelName = rel.split(/[/\\]/)[0];
  if (!topLevelName) return;
  const topLevel = resolve(resolvedStop, topLevelName);

  while (current !== topLevel && current !== resolvedStop) {
    try {
      if (readdirSync(current).length > 0) break;
      rmSync(current, { recursive: false, force: true });
    } catch {
      break;
    }
    current = dirname(current);
  }
}

export function applyEditors(
  projectDir: string,
  home?: string,
  force = false,
): ApplyEditorsResult {
  const resolvedRoot = resolve(projectDir);
  const enabled = getEnabledEditors(home);
  const enabledNames = new Set(enabled.map((spec) => spec.name));
  const created: string[] = [];
  const kept: string[] = [];
  const removed: string[] = [];
  const skipped: string[] = [];

  for (const spec of enabled) {
    const target = safeProjectPath(resolvedRoot, spec.entrypoint);
    if (!target) {
      skipped.push(spec.entrypoint);
      continue;
    }
    mkdirSync(dirname(target), { recursive: true });
    if (existsSync(target) && !force) {
      kept.push(spec.entrypoint);
      continue;
    }
    const content =
      spec.name === "codex" ? rootAgentsPointer() : thinEntrypoint(spec.name);
    writeFileSync(target, content, "utf8");
    created.push(spec.entrypoint);
  }

  const catalog = allEditors(home);
  for (const [name, spec] of Object.entries(catalog)) {
    if (enabledNames.has(name)) continue;
    const entrypointPath = safeProjectPath(resolvedRoot, spec.entrypoint);
    if (!entrypointPath) {
      skipped.push(spec.entrypoint);
      continue;
    }
    if (!existsSync(entrypointPath) || !statSync(entrypointPath).isFile()) {
      continue;
    }
    if (!isAgentflowEntrypoint(entrypointPath)) {
      skipped.push(spec.entrypoint);
      continue;
    }
    unlinkSync(entrypointPath);
    removed.push(spec.entrypoint);
    pruneEmptyParents(dirname(entrypointPath), resolvedRoot);
  }

  return { created, kept, removed, skipped };
}
