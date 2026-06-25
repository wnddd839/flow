import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { tmpdir } from "node:os";
import { afterEach, describe, expect, it } from "vitest";
import { VERSION } from "../src/version.js";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const CLI = join(ROOT, "dist", "cli.js");

function runCli(cwd: string, args: string[]): { code: number; stdout: string; stderr: string } {
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
    expect(existsSync(join(dir, ".cursor", "rules", "agentflow.mdc"))).toBe(true);
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
});

describe("packaging", () => {
  it("version matches package.json", () => {
    const pkg = JSON.parse(
      readFileSync(join(ROOT, "package.json"), "utf8"),
    ) as { version: string };
    expect(VERSION).toBe(pkg.version);
  });
});
