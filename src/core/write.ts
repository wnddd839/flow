import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

export function writeText(
  path: string,
  content: string,
  force: boolean,
): "created" | "skipped" {
  mkdirSync(dirname(path), { recursive: true });
  if (existsSync(path) && !force) {
    return "skipped";
  }
  writeFileSync(path, content, "utf8");
  return "created";
}
