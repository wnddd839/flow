import { createReadStream, createWriteStream } from "node:fs";
import type { Readable, Writable } from "node:stream";

export function isCiEnvironment(): boolean {
  const ci = process.env.CI;
  return ci === "true" || ci === "1";
}

/**
 * Whether we should attempt an interactive picker.
 * Windows cmd.exe often reports stdin/stdout.isTTY=false while still interactive.
 */
export function canRunInteractivePicker(isTty?: boolean): boolean {
  if (isTty !== undefined) return isTty;
  if (isCiEnvironment() || process.env.FLOW_NON_INTERACTIVE === "1") {
    return false;
  }
  if (process.env.TERM === "dumb") {
    return false;
  }
  if (process.stdout.isTTY || process.stderr.isTTY || process.stdin.isTTY) {
    return true;
  }
  // Last resort: on Windows, isTTY is unreliable — still try (uses CONIN$ fallback).
  if (process.platform === "win32") {
    return true;
  }
  return false;
}

/** Best-effort streams for keyboard input on Windows when stdin.isTTY is false. */
export function interactiveStreams(): { input: Readable; output: Writable } {
  if (process.stdin.isTTY && process.stdout.isTTY) {
    return { input: process.stdin, output: process.stdout };
  }
  if (process.platform === "win32") {
    try {
      return {
        input: createReadStream("CONIN$"),
        output: createWriteStream("CONOUT$"),
      };
    } catch {
      // fall through
    }
  }
  return { input: process.stdin, output: process.stdout };
}

export function describeTtyState(): string {
  return `stdin.isTTY=${Boolean(process.stdin.isTTY)}, stdout.isTTY=${Boolean(process.stdout.isTTY)}, platform=${process.platform}`;
}
