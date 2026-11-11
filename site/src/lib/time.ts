// Time as a student reads it: "12 min", "3 h", "Yesterday", "4 Nov". All functions take `now` so they can be
// tested and so the server and the browser agree on first paint.

const DAY = 86_400_000;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// The UAE has one time zone and no daylight saving, so "today" is computed there, not in the reader's zone.
const UAE_OFFSET = 4 * 3_600_000;

export function uaeDay(ms: number): number {
  return Math.floor((ms + UAE_OFFSET) / DAY);
}

/** The moment a role became visible: the employer's own date when the feed gives one, else when we first saw it. */
export function postedMs(role: { posted_at?: string | null; first_seen: string }): number {
  const posted = role.posted_at ? Date.parse(role.posted_at) : NaN;
  const seen = Date.parse(role.first_seen);
  // A feed date in the future, or after we saw it, is a feed error; trust what we saw.
  return Number.isFinite(posted) && posted <= seen ? posted : seen;
}

/** Feeds that give a date without a time put it at midnight; showing "9 h ago" for that would be invented precision. */
export function hasClockTime(iso: string | null | undefined): boolean {
  if (!iso) return false;
  return !/T00:00:00(?:\.0+)?(?:Z|[+-]\d\d:\d\d)$/.test(iso) && iso.includes("T");
}

export function shortAge(ms: number, now: number, precise = true): string {
  const diff = Math.max(0, now - ms);
  const days = uaeDay(now) - uaeDay(ms);
  if (precise && diff < 3_600_000) return `${Math.max(1, Math.round(diff / 60_000))} min`;
  if (precise && diff < DAY && days <= 1) return `${Math.round(diff / 3_600_000)} h`;
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} d`;
  return shortDate(ms, now);
}

export function shortDate(ms: number, now: number): string {
  const d = new Date(ms + UAE_OFFSET);
  const sameYear = d.getUTCFullYear() === new Date(now + UAE_OFFSET).getUTCFullYear();
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}${sameYear ? "" : ` ${d.getUTCFullYear()}`}`;
}

export function longDate(ms: number): string {
  const d = new Date(ms + UAE_OFFSET);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

export function clock(ms: number): string {
  const d = new Date(ms + UAE_OFFSET);
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

/** "checked 12 minutes ago", for sentences. */
export function ago(ms: number, now: number): string {
  const diff = Math.max(0, now - ms);
  const mins = Math.round(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hours = Math.round(diff / 3_600_000);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.round(diff / DAY);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export const GROUPS = ["Today", "Yesterday", "This week", "Earlier this month", "Older"] as const;
export type Group = (typeof GROUPS)[number];

export function groupOf(ms: number, now: number): Group {
  const days = uaeDay(now) - uaeDay(ms);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return "This week";
  if (days < 31) return "Earlier this month";
  return "Older";
}
