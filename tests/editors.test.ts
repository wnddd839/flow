import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  applyEditors,
  getEnabledEditors,
  loadEditorConfig,
  saveEditorConfig,
  validateRelativeEntrypoint,
} from "../src/editors/index.js";
import { thinEntrypoint } from "../src/templates.js";

describe("editors", () => {
  const dirs: string[] = [];

  afterEach(() => {
    for (const dir of dirs) {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  function tempProject(): { root: string; home: string } {
    const root = mkdtempSync(join(tmpdir(), "flow-editors-"));
    const home = join(root, "home");
    dirs.push(root);
    return { root, home };
  }

  it("applyEditors does not delete user files", () => {
    const { root, home } = tempProject();
    const cursorDir = join(root, ".cursor", "rules");
    mkdirSync(cursorDir, { recursive: true });
    const userFile = join(cursorDir, "my-rules.mdc");
    writeFileSync(userFile, "custom", "utf8");

    const entrypoint = join(cursorDir, "agentflow.mdc");
    writeFileSync(entrypoint, thinEntrypoint("cursor"), "utf8");

    const target = { projectDir: root, home };
    const config = loadEditorConfig(target);
    saveEditorConfig([], config.custom, target);
    const result = applyEditors(root, target);

    expect(result.removed).toContain(".cursor/rules/agentflow.mdc");
    expect(existsSync(userFile)).toBe(true);
  });

  it("rejects absolute custom entrypoint paths", () => {
    expect(() => validateRelativeEntrypoint("/etc/passwd")).toThrow(
      /project-relative/,
    );
    expect(() => validateRelativeEntrypoint("..\\secret.txt")).toThrow(/\.\./);
  });

  it("round-trips editor config yaml subset", () => {
    const { root } = tempProject();
    const target = { projectDir: root };
    saveEditorConfig(["cursor", "claude"], {}, target);
    const loaded = loadEditorConfig(target);
    expect(loaded.enabled).toEqual(["cursor", "claude"]);
  });

  it("project-level config does not leak across projects", () => {
    // Project A enables cursor; project B enables codex. Neither should see
    // the other's editors — the v1 global-config cross-contamination bug.
    const a = mkdtempSync(join(tmpdir(), "flow-projA-"));
    const b = mkdtempSync(join(tmpdir(), "flow-projB-"));
    dirs.push(a, b);

    saveEditorConfig(["cursor"], {}, { projectDir: a });
    saveEditorConfig(["codex"], {}, { projectDir: b });

    expect(getEnabledEditors({ projectDir: a }).map((s) => s.name)).toEqual([
      "cursor",
    ]);
    expect(getEnabledEditors({ projectDir: b }).map((s) => s.name)).toEqual([
      "codex",
    ]);

    // And the project-level file lives inside the project, not the home dir.
    expect(existsSync(join(a, ".agentflow", "editors.yaml"))).toBe(true);
    expect(existsSync(join(b, ".agentflow", "editors.yaml"))).toBe(true);
  });
});
