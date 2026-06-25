import { existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { BASE_REQUIRED_FILES, doctorProject } from "../src/core/check.js";
import { initProject } from "../src/core/init.js";
import {
  getEnabledEditors,
  normalizeEditorNames,
} from "../src/editors/index.js";
import { pickEditors } from "../src/init-ui.js";
import { agentsMd } from "../src/templates.js";

describe("initProject", () => {
  const dirs: string[] = [];

  afterEach(() => {
    for (const dir of dirs) {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  function tempProject(): { root: string; home: string } {
    const root = mkdtempSync(join(tmpdir(), "flow-init-"));
    const home = join(root, "home");
    dirs.push(root);
    return { root, home };
  }

  it("creates skeleton files", () => {
    const { root, home } = tempProject();
    const result = initProject(root, { home });

    for (const relative of BASE_REQUIRED_FILES) {
      expect(existsSync(join(root, relative))).toBe(true);
    }
    expect(result.created).toContain(".agentflow/AGENTS.md");
    expect(result.created).not.toContain("AGENTS.md");
  });

  it("defaults to skeleton only", () => {
    const { root, home } = tempProject();
    initProject(root, { home });

    expect(existsSync(join(root, "AGENTS.md"))).toBe(false);
    expect(existsSync(join(root, "CLAUDE.md"))).toBe(false);
    expect(getEnabledEditors(home)).toEqual([]);
  });

  it("creates selected editor entrypoints", () => {
    const { root, home } = tempProject();
    initProject(root, { editors: ["qoder", "cursor"], home });

    const enabled = new Set(getEnabledEditors(home).map((s) => s.name));
    expect(enabled).toEqual(new Set(["qoder", "cursor"]));
    expect(existsSync(join(root, ".qoder/skills/agentflow/SKILL.md"))).toBe(
      true,
    );
    expect(existsSync(join(root, ".cursor/rules/agentflow.mdc"))).toBe(true);
    expect(existsSync(join(root, "AGENTS.md"))).toBe(false);
  });

  it("rejects unknown editors", () => {
    expect(() => normalizeEditorNames(["not-a-real-editor"])).toThrow(
      /Unknown editor/,
    );
  });

  it("pickEditors returns empty when not TTY", async () => {
    await expect(pickEditors({ isTty: false })).resolves.toEqual([]);
  });

  it("init is idempotent without force", () => {
    const { root, home } = tempProject();
    const first = initProject(root, { home });
    const second = initProject(root, { home });
    expect(first.created.length).toBeGreaterThan(0);
    expect(second.created.length).toBe(0);
  });
});

describe("doctorProject", () => {
  const dirs: string[] = [];

  afterEach(() => {
    for (const dir of dirs) {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("reports missing skeleton before init", () => {
    const root = mkdtempSync(join(tmpdir(), "flow-check-"));
    dirs.push(root);
    const report = doctorProject(root);
    expect(report.ok).toBe(false);
    expect(report.missing.length).toBeGreaterThan(0);
  });

  it("passes after init", () => {
    const root = mkdtempSync(join(tmpdir(), "flow-check-"));
    const home = join(root, "home");
    dirs.push(root);
    initProject(root, { home });
    const report = doctorProject(root, home);
    expect(report.ok).toBe(true);
  });

  it("reports drift when an entrypoint no longer points to agentflow", () => {
    const root = mkdtempSync(join(tmpdir(), "flow-check-"));
    const home = join(root, "home");
    dirs.push(root);
    initProject(root, { editors: ["cursor"], home });

    const entry = join(root, ".cursor", "rules", "agentflow.mdc");
    writeFileSync(entry, "no pointer here", "utf8");

    const report = doctorProject(root, home);
    expect(report.ok).toBe(false);
    expect(report.drift).toContain(".cursor/rules/agentflow.mdc");
    expect(report.missing).not.toContain(".cursor/rules/agentflow.mdc");
  });
});

describe("templates", () => {
  it("includes maintenance contract", () => {
    const content = agentsMd();
    expect(content).toContain("文档维护契约");
    expect(content).toContain("每条信息只出现在一个文档里");
    expect(content).toContain("完成定义");
  });
});
