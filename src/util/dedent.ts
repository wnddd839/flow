/** Strip common leading indentation from template literals. */
export function dedent(text: string): string {
  const lines = text.replace(/^\n/, "").split("\n");
  const indents = lines
    .filter((line) => line.trim().length > 0)
    .map((line) => line.match(/^(\s*)/)?.[1].length ?? 0);
  const min = indents.length ? Math.min(...indents) : 0;
  return lines.map((line) => line.slice(min)).join("\n");
}
