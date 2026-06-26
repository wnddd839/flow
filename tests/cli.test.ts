import { execFileSync } from "node:child_process";
import {
  existsSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it } from "vitest";
import { VERSION } from "../src/version.js";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const CLI = join(ROOT, "dist", "cli.js");

function runCli(
  cwd: string,
  args: string[],
): { code: number; stdout: string; stderr: string } {
  try {
    const stdout = execFileSync(process.execPath, [CLI, ...args], {
      cwd,
      encoding: "utf8",
      env: { ...process.env, AGENTFLOW_HOME: join(cwd, ".af-home") },
    });
    return { code: 0, stdout, stderr: "" };
  } catch (err: unknown) {
    const e = err as { status?: number; stdout?: string; stderr?: string };
    return {
      code: e.status ?? 1,
      stdout: e.stdout ?? "",
      stderr: e.stderr ?? "",
    };
  }
}

describe("cli", () => {
  const dirs: string[] = [];

  afterEach(() => {
    for (const dir of dirs) {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  function tempDir(): string {
    const dir = mkdtempSync(join(tmpdir(), "flow-cli-"));
    dirs.push(dir);
    return dir;
  }

  it("prints version", () => {
    const dir = tempDir();
    const result = runCli(dir, ["--version"]);
    expect(result.code).toBe(0);
    expect(`${result.stdout}${result.stderr}`).toContain(VERSION);
  });

  it("bare flow prints help and exits 0", () => {
    const dir = tempDir();
    const result = runCli(dir, []);
    expect(result.code).toBe(0);
    expect(result.stdout).toContain("Usage:");
  });

  it("init --skeleton-only creates agentflow skeleton", () => {
    const dir = tempDir();
    const result = runCli(dir, ["init", "--skeleton-only"]);
    expect(result.code).toBe(0);
    expect(result.stdout).toContain("Initialized specification skeleton");
    expect(existsSync(join(dir, ".agentflow", "AGENTS.md"))).toBe(true);
    expect(existsSync(join(dir, "AGENTS.md"))).toBe(false);
  });

  it("check passes after init", () => {
    const dir = tempDir();
    runCli(dir, ["init", "--skeleton-only"]);
    const result = runCli(dir, ["check"]);
    expect(result.code).toBe(0);
    expect(result.stdout).toContain("AgentFlow check: OK");
  });

  it("check fails before init", () => {
    const dir = tempDir();
    const result = runCli(dir, ["check"]);
    expect(result.code).toBe(1);
    expect(result.stdout).toContain("missing files");
  });

  it("init cursor creates cursor entrypoint", () => {
    const dir = tempDir();
    const result = runCli(dir, ["init", "cursor"]);
    expect(result.code).toBe(0);
    expect(result.stdout).toContain("Editors: cursor");
    expect(existsSync(join(dir, ".cursor", "rules", "agentflow.mdc"))).toBe(
      true,
    );
  });

  it("init claude creates CLAUDE.md entrypoint", () => {
    const dir = tempDir();
    const result = runCli(dir, ["init", "claude"]);
    expect(result.code).toBe(0);
    expect(result.stdout).toContain("Editors: claude");
    expect(existsSync(join(dir, "CLAUDE.md"))).toBe(true);
  });

  it("init codex claude creates both entrypoints", () => {
    const dir = tempDir();
    const result = runCli(dir, ["init", "codex", "claude"]);
    expect(result.code).toBe(0);
    expect(result.stdout).toContain("Editors: codex, claude");
    expect(existsSync(join(dir, "AGENTS.md"))).toBe(true);
    expect(existsSync(join(dir, "CLAUDE.md"))).toBe(true);
  });

  it("init --skeleton-only lists all editor quick commands", () => {
    const dir = tempDir();
    const result = runCli(dir, ["init", "--skeleton-only"]);
    expect(result.code).toBe(0);
    expect(result.stdout).toContain("flow init codex");
    expect(result.stdout).toContain("flow init claude");
    expect(result.stdout).toContain("flow init cursor");
    expect(result.stdout).toContain("flow init antigravity");
  });

  it("init codex writes a root AGENTS.md pointer", () => {
    const dir = tempDir();
    const result = runCli(dir, ["init", "codex"]);
    expect(result.code).toBe(0);
    const agents = join(dir, "AGENTS.md");
    expect(existsSync(agents)).toBe(true);
    expect(readFileSync(agents, "utf8")).toContain(".agentflow/AGENTS.md");
  });

  it("init --force restores a tampered entrypoint", () => {
    const dir = tempDir();
    runCli(dir, ["init", "cursor"]);
    const entry = join(dir, ".cursor", "rules", "agentflow.mdc");
    writeFileSync(entry, "tampered", "utf8");
    runCli(dir, ["init", "cursor", "--force"]);
    expect(readFileSync(entry, "utf8")).toContain(".agentflow/AGENTS.md");
  });

  it("editors add/list/remove round-trip", () => {
    const dir = tempDir();
    runCli(dir, ["init", "--skeleton-only"]);

    const added = runCli(dir, ["editors", "add", "cursor"]);
    expect(added.code).toBe(0);
    expect(existsSync(join(dir, ".cursor", "rules", "agentflow.mdc"))).toBe(
      true,
    );

    const list = runCli(dir, ["editors", "list"]);
    expect(list.stdout).toContain("[x] cursor");

    const removed = runCli(dir, ["editors", "remove", "cursor"]);
    expect(removed.code).toBe(0);
    expect(existsSync(join(dir, ".cursor", "rules", "agentflow.mdc"))).toBe(
      false,
    );
  });

  it("check reports drift when an entrypoint stops pointing to agentflow", () => {
    const dir = tempDir();
    runCli(dir, ["init", "cursor"]);
    const entry = join(dir, ".cursor", "rules", "agentflow.mdc");
    writeFileSync(entry, "someone overwrote this pointer", "utf8");
    const result = runCli(dir, ["check"]);
    expect(result.code).toBe(1);
    expect(result.stdout).toContain("drift");
  });

  it("tools --json outputs tools array", () => {
    const dir = tempDir();
    const result = runCli(dir, ["tools", "--json"]);
    expect(result.code).toBe(0);
    const data = JSON.parse(result.stdout) as { tools: unknown[] };
    expect(data.tools).toBeInstanceOf(Array);
  });

  it("instructions requires init", () => {
    const dir = tempDir();
    const result = runCli(dir, ["instructions"]);
    expect(result.code).toBe(1);
    expect(result.stdout.toLowerCase()).toContain("not initialized");
  });

  it("instructions prints per-tool kickoff prompts after init", () => {
    const dir = tempDir();
    runCli(dir, ["init", "cursor"]);
    const result = runCli(dir, ["instructions"]);
    expect(result.code).toBe(0);
    expect(result.stdout).toContain("触发话术");
    expect(result.stdout).toContain("— Cursor —");
    expect(result.stdout).toContain(".agentflow/AGENTS.md");
  });

  it("init writes project-level editors.yaml, not global", () => {
    const dir = tempDir();
    runCli(dir, ["init", "cursor"]);
    // Project-level config lives inside the project...
    expect(existsSync(join(dir, ".agentflow", "editors.yaml"))).toBe(true);
    // ...and the global home (AGENTFLOW_HOME -> dir/.af-home) stays clean.
    const globalHome = join(dir, ".af-home");
    expect(existsSync(join(globalHome, "editors.yaml"))).toBe(false);
  });

  it("check reports unfilled sections right after init", () => {
    const dir = tempDir();
    runCli(dir, ["init", "--skeleton-only"]);
    const result = runCli(dir, ["check"]);
    // ok is true (files exist), but unfilled must be surfaced.
    expect(result.code).toBe(0);
    expect(result.stdout).toContain("skeleton not yet filled");
    expect(result.stdout).toContain("project.md");
  });
});

describe("packaging", () => {
  it("version matches package.json", () => {
    const pkg = JSON.parse(
      readFileSync(join(ROOT, "package.json"), "utf8"),
    ) as { version: string };
    expect(VERSION).toBe(pkg.version);
  });
});
