import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { afterEach, describe, expect, it } from "vitest";
import {
  applyEditors,
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

    const config = loadEditorConfig(home);
    saveEditorConfig([], config.custom, home);
    const result = applyEditors(root, home);

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
    const { home } = tempProject();
    saveEditorConfig(["cursor", "claude"], {}, home);
    const loaded = loadEditorConfig(home);
    expect(loaded.enabled).toEqual(["cursor", "claude"]);
  });
});
