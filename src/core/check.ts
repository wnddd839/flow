import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { getEnabledEditors } from "../editors/index.js";
import {
  BASE_REQUIRED_FILES,
  resolveRequiredPath,
  SPEC_DOC_FILES,
} from "./paths.js";

export { BASE_REQUIRED_FILES, SPEC_DOC_FILES } from "./paths.js";

const AGENTFLOW_POINTER = ".agentflow/AGENTS.md";

export interface DoctorReport {
  ok: boolean;
  missing: string[];
  drift: string[];
  unfilled: string[];
  /** Spec docs still at pre-v0.6.5 flat paths under .agentflow/ */
  legacyDocs: string[];
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

/**
 * A skeleton section is "unfilled" when, beneath its `## heading`, there is
 * nothing but blank lines and HTML comment placeholders (<!-- ... -->).
 *
 * We only inspect the skeleton docs that init generates with per-section
 * placeholders; AGENTS.md / skills/README.md have no such sections, so they
 * are skipped.
 */
const UNFILLABLE_FILES = new Set<string>(SPEC_DOC_FILES);

function findUnfilledSections(path: string): string[] {
  let content: string;
  try {
    content = readFileSync(path, "utf8");
  } catch {
    return [];
  }

  const sections: string[] = [];
  // Split into [heading, body] pairs at each "## " at the start of a line.
  const parts = content.split(/(?=^## )/m);
  for (const part of parts) {
    const match = part.match(/^## (.+)$/m);
    if (!match) continue;
    const heading = match[1].trim();
    const body = part.slice(match[0].length);
    // Strip blank lines and HTML comments; if nothing remains, it's unfilled.
    const stripped = body
      .split("\n")
      .map((l) => l.trim())
      .filter(
        (l) => l.length > 0 && !l.startsWith("<!--") && !l.endsWith("-->"),
      );
    if (stripped.length === 0) {
      sections.push(heading);
    }
  }
  return sections;
}

export function doctorProject(projectDir: string, home?: string): DoctorReport {
  const root = resolve(projectDir);
  const enabled = getEnabledEditors({ projectDir: root, home });
  const editorEntrypoints = enabled.map((spec) => spec.entrypoint);
  const missing: string[] = [];
  const drift: string[] = [];
  const unfilled: string[] = [];
  const legacyDocs: string[] = [];

  for (const relative of BASE_REQUIRED_FILES) {
    const resolved = resolveRequiredPath(root, relative, existsSync);
    if (!resolved) {
      missing.push(relative);
      continue;
    }
    if (resolved.legacy && UNFILLABLE_FILES.has(relative)) {
      legacyDocs.push(resolved.relative);
    }
    if (UNFILLABLE_FILES.has(relative)) {
      const empty = findUnfilledSections(resolved.path);
      if (empty.length > 0) {
        unfilled.push(`${resolved.relative} (${empty.join(", ")})`);
      }
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
    // unfilled does NOT fail `ok`: an unfilled skeleton is the expected
    // intermediate state right after init, not an error condition. It is
    // surfaced separately so users see "skeleton ready, content pending".
    ok: missing.length === 0 && drift.length === 0,
    missing,
    drift,
    unfilled,
    legacyDocs,
    checked: [...BASE_REQUIRED_FILES, ...editorEntrypoints],
    editors: enabled.map((spec) => spec.name),
  };
}
