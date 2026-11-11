import type { Role, Snapshot } from "./schema";
import { postedMs, uaeDay } from "./time";

// Numbers the pages state. Each is counted here, from the snapshot, so no page carries a hand-typed figure.

export function openRoles(snapshot: Snapshot): Role[] {
  return snapshot.roles.filter((r) => r.status === "open");
}

/** Roles posted per UAE day for the last `days` days, oldest first. */
export function postedPerDay(roles: Role[], now: number, days = 35): { day: number; n: number }[] {
  const today = uaeDay(now);
  const out = Array.from({ length: days }, (_, i) => ({ day: today - (days - 1 - i), n: 0 }));
  for (const r of roles) {
    const at = uaeDay(postedMs(r)) - (today - (days - 1));
    if (at >= 0 && at < days) out[at].n += 1;
  }
  return out;
}

export function tally<T extends string>(items: T[]): { name: T; n: number }[] {
  const map = new Map<T, number>();
  for (const i of items) map.set(i, (map.get(i) ?? 0) + 1);
  return [...map.entries()].map(([name, n]) => ({ name, n })).sort((a, b) => b.n - a.n || a.name.localeCompare(b.name));
}

export function summary(snapshot: Snapshot, now: number) {
  const open = openRoles(snapshot);
  const read = employers(snapshot).filter((e) => e.lastOk);
  const today = uaeDay(now);
  return {
    open: open.length,
    employers: read.length,
    withRoles: new Set(open.map((r) => r.employer)).size,
    today: open.filter((r) => uaeDay(postedMs(r)) === today).length,
    week: open.filter((r) => today - uaeDay(postedMs(r)) < 7).length,
    failed: employers(snapshot).filter((e) => !e.ok).length,
    uaePostings: snapshot.boards.reduce((s, b) => s + b.uae, 0),
  };
}

export type Employer = {
  name: string;
  systems: string[];
  student: number;
  uae: number;
  ok: boolean;
  checkedAt: string;
  lastOk: string | null;
  error: string | null;
};

/** One line per employer. An employer with two career sites is one employer; its open roles are counted once. */
export function employers(snapshot: Snapshot): Employer[] {
  const open = new Map<string, number>();
  for (const r of openRoles(snapshot)) open.set(r.employer, (open.get(r.employer) ?? 0) + 1);
  const map = new Map<string, Employer>();
  for (const b of snapshot.boards) {
    const e = map.get(b.name);
    if (!e) {
      map.set(b.name, { name: b.name, systems: [b.system], student: open.get(b.name) ?? 0, uae: b.uae, ok: b.ok, checkedAt: b.checked_at, lastOk: b.last_ok ?? null, error: b.ok ? null : (b.error ?? "unknown reason") });
      continue;
    }
    if (!e.systems.includes(b.system)) e.systems.push(b.system);
    e.uae += b.uae;
    if (!b.ok) {
      e.ok = false;
      e.error = e.error ?? b.error ?? "unknown reason";
    }
    if (b.last_ok && (!e.lastOk || b.last_ok > e.lastOk)) e.lastOk = b.last_ok;
    if (b.checked_at < e.checkedAt) e.checkedAt = b.checked_at;
  }
  return [...map.values()].sort((a, b) => b.student - a.student || b.uae - a.uae || a.name.localeCompare(b.name));
}

export function pct(n: number, of: number): string {
  return of ? `${Math.round((100 * n) / of)}%` : "0%";
}
