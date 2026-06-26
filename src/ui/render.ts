/**
 * Tiny zero-dependency terminal UI helpers: ANSI colors, box panels, and the
 * Flow workbench banner. Kept ASCII-safe for legacy Windows code pages, with
 * Unicode box characters that also exist in GBK so they render in cmd.exe.
 */

const COLOR_ENABLED =
  process.env.NO_COLOR === undefined &&
  (Boolean(process.stdout.isTTY) || process.env.FORCE_COLOR !== undefined);

function sgr(code: string): (text: string) => string {
  if (!COLOR_ENABLED) return (text) => text;
  return (text) => `\x1b[${code}m${text}\x1b[0m`;
}

export const color = {
  cyan: sgr("36"),
  brightCyan: sgr("96"),
  blue: sgr("34"),
  brightBlue: sgr("94"),
  magenta: sgr("35"),
  brightMagenta: sgr("95"),
  green: sgr("32"),
  brightGreen: sgr("92"),
  yellow: sgr("33"),
  brightYellow: sgr("93"),
  red: sgr("31"),
  brightRed: sgr("91"),
  gray: sgr("90"),
  white: sgr("97"),
  bold: sgr("1"),
  dim: sgr("2"),
  pill: sgr("30;106"),
};

const ANSI_RE = new RegExp(`${String.fromCharCode(27)}\\[[0-9;]*m`, "g");

export function stripAnsi(text: string): string {
  return text.replace(ANSI_RE, "");
}

/** Visible width, counting common CJK ranges as width 2. */
export function visibleWidth(text: string): number {
  const plain = stripAnsi(text);
  let width = 0;
  for (const ch of plain) {
    const code = ch.codePointAt(0) ?? 0;
    width +=
      (code >= 0x1100 && code <= 0x115f) ||
      (code >= 0x2e80 && code <= 0xa4cf) ||
      (code >= 0xac00 && code <= 0xd7a3) ||
      (code >= 0xf900 && code <= 0xfaff) ||
      (code >= 0xff00 && code <= 0xff60) ||
      (code >= 0xffe0 && code <= 0xffe6)
        ? 2
        : 1;
  }
  return width;
}

function padTo(text: string, target: number): string {
  const pad = target - visibleWidth(text);
  return pad > 0 ? text + " ".repeat(pad) : text;
}

function truncateTo(text: string, max: number): string {
  if (visibleWidth(text) <= max) return text;
  let out = "";
  for (const ch of text) {
    if (visibleWidth(out + ch) > max - 1) break;
    out += ch;
  }
  return `${out}…`;
}

const BOX = { tl: "╭", tr: "╮", bl: "╰", br: "╯", h: "─", v: "│" };

/**
 * Render a titled panel to an array of equal-width lines (borders included).
 * `body` lines may contain ANSI; width is the total box width.
 */
export function panel(title: string, body: string[], width: number): string[] {
  const inner = width - 4; // content area between "│ " and " │"
  const titleText = ` ${title} `;
  const dashes = Math.max(0, width - 3 - visibleWidth(titleText));
  const top = color.gray(
    `${BOX.tl}${BOX.h}${color.bold(color.brightCyan(titleText))}${color.gray(
      BOX.h.repeat(dashes),
    )}${BOX.tr}`,
  );
  const bottom = color.gray(`${BOX.bl}${BOX.h.repeat(width - 2)}${BOX.br}`);
  const lines = body.map((line) => {
    const content = padTo(truncateTo(line, inner), inner);
    return `${color.gray(BOX.v)} ${content} ${color.gray(BOX.v)}`;
  });
  return [top, ...lines, bottom];
}

/** Lay two panels side by side; pad the shorter one with blank rows. */
export function sideBySide(left: string[], right: string[], gap = 2): string[] {
  const rows = Math.max(left.length, right.length);
  const leftWidth = left.length ? visibleWidth(left[0]) : 0;
  const out: string[] = [];
  for (let i = 0; i < rows; i++) {
    const l = left[i] ?? " ".repeat(leftWidth);
    const r = right[i] ?? "";
    out.push(`${l}${" ".repeat(gap)}${r}`);
  }
  return out;
}

export function terminalWidth(): number {
  return process.stdout.columns ?? 80;
}

const LOGO = [
  " _____ _               ",
  "|  ___| | _____      __",
  "| |_  | |/ _ \\ \\ /\\ / /",
  "|  _| | | (_) \\ V  V / ",
  "|_|   |_|\\___/ \\_/\\_/  ",
];

/** Two-tone gradient logo (cyan → blue). */
export function logo(): string {
  const tints = [
    color.brightCyan,
    color.brightCyan,
    color.cyan,
    color.brightBlue,
    color.blue,
  ];
  return LOGO.map((line, i) => `  ${tints[i](line)}`).join("\n");
}

/** A row of highlighted command "pills". */
export function pills(items: string[]): string {
  return items.map((item) => color.pill(` ${item} `)).join(" ");
}
