import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { getEnabledEditors } from "../editors/index.js";

export const BASE_REQUIRED_FILES = [
  ".agentflow/AGENTS.md",
  ".agentflow/project.md",
  ".agentflow/conventions.md",
  ".agentflow/business.md",
  ".agentflow/pitfalls.md",
  ".agentflow/skills/README.md",
] as const;

const AGENTFLOW_POINTER = ".agentflow/AGENTS.md";

export interface DoctorReport {
  ok: boolean;
  missing: string[];
  drift: string[];
  checked: string[];
  editors: string[];
}

/** An enabled entrypoint has drifted if it exists but no longer points back to .agentflow. */
function pointsToAgentflow(path: string): boolean {
  try {
    return readFileSync(path, "utf8").includes(AGENTFLOW_POINTER);
  } catch {
    return false;
  }
}

export function doctorProject(projectDir: string, home?: string): DoctorReport {
  const root = resolve(projectDir);
  const enabled = getEnabledEditors(home);
  const editorEntrypoints = enabled.map((spec) => spec.entrypoint);
  const missing: string[] = [];
  const drift: string[] = [];

  for (const relative of BASE_REQUIRED_FILES) {
    if (!existsSync(join(root, relative))) {
      missing.push(relative);
    }
  }

  for (const relative of editorEntrypoints) {
    const full = join(root, relative);
    if (!existsSync(full)) {
      missing.push(relative);
    } else if (!pointsToAgentflow(full)) {
      drift.push(relative);
    }
  }

  return {
    ok: missing.length === 0 && drift.length === 0,
    missing,
    drift,
    checked: [...BASE_REQUIRED_FILES, ...editorEntrypoints],
    editors: enabled.map((spec) => spec.name),
  };
}
