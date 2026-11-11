import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

// The colour roles in globals.css, checked against WCAG contrast. If a token is edited to something unreadable,
// this fails before anyone sees it.

const css = readFileSync(path.join(process.cwd(), "src", "app", "globals.css"), "utf8");

function tokens(block: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const m of block.matchAll(/--([a-z0-9-]+):\s*(#[0-9a-f]{6})\s*;/gi)) out[m[1]] = m[2];
  return out;
}

const light = tokens(css.slice(css.indexOf(":root {"), css.indexOf(':root[data-theme="dark"]')));
const dark = tokens(css.slice(css.indexOf(':root[data-theme="dark"]'), css.indexOf("@media (prefers-color-scheme: dark)")));
const system = tokens(css.slice(css.indexOf("@media (prefers-color-scheme: dark)"), css.indexOf("@media (min-width: 720px)")));

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

describe.each([
  ["light", light],
  ["dark", dark],
])("%s theme", (_name, t) => {
  it("defines every role", () => {
    for (const key of ["page", "surface", "wash", "rule", "rule-2", "ink", "ink-2", "ink-3", "signal", "signal-wash"]) expect(t[key], key).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it.each(["ink", "ink-2", "ink-3", "signal"])("%s is readable as text on every ground it sits on", (fg) => {
    for (const bg of ["page", "surface", "wash"]) expect(contrast(t[fg], t[bg]), `${fg} on ${bg}`).toBeGreaterThanOrEqual(4.5);
  });

  it("text on the notice ground is readable", () => {
    expect(contrast(t.ink, t["signal-wash"])).toBeGreaterThanOrEqual(7);
  });

  it("a filled button reads both ways round", () => {
    expect(contrast(t.page, t.ink)).toBeGreaterThanOrEqual(7);
  });

  it("borders that carry meaning can be seen", () => {
    expect(contrast(t["rule-2"], t.page)).toBeGreaterThanOrEqual(1.5);
    expect(contrast(t.signal, t.page)).toBeGreaterThanOrEqual(3);
  });
});

describe("dark by system setting", () => {
  it("uses exactly the same values as dark by choice", () => {
    expect(system).toEqual(dark);
  });
});
