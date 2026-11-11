import type { Role } from "./schema";
import PATTERNS from "./skills.json";

// Matching a pasted CV to roles. The CV is read with exactly the patterns the collector uses on postings
// (skills.json is written from the collector's own list), so "Python" means the same thing on both sides.
// Everything here runs in the reader's browser: the CV text is never sent anywhere and never stored.

const COMPILED = (PATTERNS as { name: string; pattern: string; flags: string }[]).map((p) => ({ name: p.name, re: new RegExp(p.pattern, p.flags) }));

export const MAX_CV_CHARS = 60_000;

/** The skills, from the fixed list, that the CV text names. */
export function cvSkills(text: string): string[] {
  const hay = text.slice(0, MAX_CV_CHARS);
  return COMPILED.filter((p) => p.re.test(hay)).map((p) => p.name);
}

/** The skills a role names that the CV also names, in the role's order. */
export function matched(role: Pick<Role, "skills">, mine: string[]): string[] {
  const have = new Set(mine);
  return role.skills.filter((s) => have.has(s));
}
