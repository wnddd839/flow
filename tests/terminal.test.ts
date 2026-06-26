import { afterEach, describe, expect, it } from "vitest";
import { canRunInteractivePicker } from "../src/terminal.js";

describe("terminal", () => {
  const envBackup = { ...process.env };

  afterEach(() => {
    process.env = { ...envBackup };
  });

  it("canRunInteractivePicker respects explicit isTty=false", () => {
    expect(canRunInteractivePicker(false)).toBe(false);
  });

  it("canRunInteractivePicker is false when FLOW_NON_INTERACTIVE=1", () => {
    process.env.FLOW_NON_INTERACTIVE = "1";
    expect(canRunInteractivePicker()).toBe(false);
  });

  it("canRunInteractivePicker is false when CI=true", () => {
    process.env.CI = "true";
    expect(canRunInteractivePicker()).toBe(false);
  });
});
