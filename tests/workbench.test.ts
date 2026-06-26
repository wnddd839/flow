import { describe, expect, it } from "vitest";
import { panel, stripAnsi, visibleWidth } from "../src/ui/render.js";
import { normalize, renderDashboard } from "../src/workbench.js";

describe("workbench", () => {
  it("normalize maps numbers and slash commands", () => {
    expect(normalize("1")).toBe("init");
    expect(normalize("/init")).toBe("init");
    expect(normalize("2")).toBe("check");
    expect(normalize("/doctor")).toBe("check");
    expect(normalize("3")).toBe("prompts");
    expect(normalize("/prompts")).toBe("prompts");
    expect(normalize("0")).toBe("exit");
    expect(normalize("/quit")).toBe("exit");
    expect(normalize("tools")).toBe("tools");
    expect(normalize("nonsense")).toBeNull();
  });

  it("renderDashboard shows status for a fresh project", () => {
    const out = renderDashboard("/tmp/demo", {
      initialized: false,
      ok: false,
      missing: 6,
      unfilled: 0,
      editors: [],
    });
    expect(out).toContain("System Status");
    expect(out).toContain("Quick Wizard");
    expect(out).toContain("not initialized");
    expect(out).toContain("Quick Commands");
  });

  it("renderDashboard reflects an initialized project with editors", () => {
    const out = renderDashboard("/tmp/demo", {
      initialized: true,
      ok: true,
      missing: 0,
      unfilled: 0,
      editors: ["cursor", "claude"],
    });
    expect(out).toContain("ready");
    expect(out).toContain("cursor, claude");
  });
});

describe("ui/render", () => {
  it("panel lines are all the same visible width", () => {
    const lines = panel("Title", ["short", "a longer line here"], 40);
    for (const line of lines) {
      expect(visibleWidth(line)).toBe(40);
    }
  });

  it("stripAnsi removes escape codes", () => {
    expect(stripAnsi("\x1b[36mhi\x1b[0m")).toBe("hi");
  });
});
