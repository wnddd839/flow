import { existsSync } from "node:fs";
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

export interface DoctorReport {
  ok: boolean;
  missing: string[];
  checked: string[];
  editors: string[];
}

export function doctorProject(projectDir: string, home?: string): DoctorReport {
  const root = resolve(projectDir);
  const enabled = getEnabledEditors(home);
  const required = [
    ...BASE_REQUIRED_FILES,
    ...enabled.map((spec) => spec.entrypoint),
  ];
  const missing = required.filter(
    (relative) => !existsSync(join(root, relative)),
  );
  return {
    ok: missing.length === 0,
    missing,
    checked: required,
    editors: enabled.map((spec) => spec.name),
  };
}
