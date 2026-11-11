import type { Kind, Role } from "./schema";
import { postedMs } from "./time";

// The filter a visitor has set. It lives in the address bar, so a filtered list can be bookmarked and shared.

export type Eligibility = "any" | "open" | "unrestricted";
export type Age = "any" | "1" | "7" | "30";

export type Filters = {
  q: string;
  kinds: Kind[];
  fields: string[];
  places: string[];
  eligibility: Eligibility;
  age: Age;
  closed: boolean;
};

export const EMPTY: Filters = { q: "", kinds: [], fields: [], places: [], eligibility: "any", age: "any", closed: false };

const KIND_SET = new Set<string>(["internship", "graduate", "first_job"]);
const split = (v: string | null) => (v ? v.split(",").map((s) => s.trim()).filter(Boolean) : []);

export function parse(params: URLSearchParams): Filters {
  const eligibility = params.get("who");
  const age = params.get("age");
  return {
    q: (params.get("q") ?? "").slice(0, 80),
    kinds: split(params.get("kind")).filter((k): k is Kind => KIND_SET.has(k)),
    fields: split(params.get("field")).slice(0, 12),
    places: split(params.get("place")).slice(0, 8),
    eligibility: eligibility === "open" || eligibility === "unrestricted" ? eligibility : "any",
    age: age === "1" || age === "7" || age === "30" ? age : "any",
    closed: params.get("closed") === "1",
  };
}

export function serialize(f: Filters): string {
  const p = new URLSearchParams();
  if (f.q.trim()) p.set("q", f.q.trim());
  if (f.kinds.length) p.set("kind", f.kinds.join(","));
  if (f.fields.length) p.set("field", f.fields.join(","));
  if (f.places.length) p.set("place", f.places.join(","));
  if (f.eligibility !== "any") p.set("who", f.eligibility);
  if (f.age !== "any") p.set("age", f.age);
  if (f.closed) p.set("closed", "1");
  return p.toString();
}

export function activeCount(f: Filters): number {
  return (
    f.kinds.length + f.fields.length + f.places.length + (f.eligibility !== "any" ? 1 : 0) + (f.age !== "any" ? 1 : 0) + (f.closed ? 1 : 0)
  );
}

const norm = (s: string) => s.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");

/** Every word typed must appear somewhere in the role: title, employer, field, place or a fact. */
export function matchesQuery(role: Role, q: string): boolean {
  const words = norm(q).split(/\s+/).filter(Boolean);
  if (!words.length) return true;
  const hay = norm(
    [role.title, role.employer, role.fields.join(" "), role.places.map((p) => p.emirate).join(" "), role.department ?? "", ...Object.values(role.facts).map((f) => f?.label ?? "")].join(" "),
  );
  return words.every((w) => hay.includes(w));
}

export function restricted(role: Role): boolean {
  return role.facts.eligibility?.value === "nationals_only";
}

export function matches(role: Role, f: Filters, now: number): boolean {
  if (!f.closed && role.status !== "open") return false;
  if (f.kinds.length && !f.kinds.includes(role.kind)) return false;
  if (f.fields.length && !role.fields.some((x) => f.fields.includes(x))) return false;
  if (f.places.length && !role.places.some((p) => f.places.includes(p.emirate))) return false;
  // "unrestricted" hides roles that say UAE nationals only. "open" keeps only roles that say anyone may apply.
  if (f.eligibility === "unrestricted" && restricted(role)) return false;
  if (f.eligibility === "open" && role.facts.eligibility?.value !== "open") return false;
  if (f.age !== "any" && now - postedMs(role) > Number(f.age) * 86_400_000) return false;
  return matchesQuery(role, f.q);
}

export function apply(roles: Role[], f: Filters, now: number): Role[] {
  return roles.filter((r) => matches(r, f, now));
}

/** How many open roles each choice would show, given the other filters. Used for the numbers beside options. */
export function counts(roles: Role[], f: Filters, now: number) {
  const tally = (key: "kinds" | "fields" | "places", values: (r: Role) => string[]) => {
    const without = { ...f, [key]: [] } as Filters;
    const out = new Map<string, number>();
    for (const r of roles) {
      if (!matches(r, without, now)) continue;
      for (const v of new Set(values(r))) out.set(v, (out.get(v) ?? 0) + 1);
    }
    return out;
  };
  return {
    kinds: tally("kinds", (r) => [r.kind]),
    fields: tally("fields", (r) => r.fields),
    places: tally("places", (r) => r.places.map((p) => p.emirate)),
  };
}

export function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}
