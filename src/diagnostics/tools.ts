import { execSync } from "node:child_process";

export interface ToolInfo {
  name: string;
  display: string;
  command: string;
  status: "ok" | "missing";
  path: string;
}

const KNOWN_TOOLS: [string, string][] = [
  ["codex", "Codex"],
  ["claude", "Claude Code"],
  ["cursor", "Cursor"],
  ["kiro", "Kiro"],
  ["qoder", "Qoder"],
  ["gemini", "Gemini CLI"],
];

export function which(command: string): string | null {
  try {
    const cmd = process.platform === "win32" ? "where" : "which";
    const result = execSync(`${cmd} ${command}`, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
    return result.split(/\r?\n/)[0] || null;
  } catch {
    return null;
  }
}

export function detectTools(
  resolver: (command: string) => string | null = which,
): ToolInfo[] {
  return KNOWN_TOOLS.map(([command, label]) => {
    const path = resolver(command) ?? "";
    return {
      name: command,
      display: label,
      command,
      status: path ? "ok" : "missing",
      path,
    };
  });
}
