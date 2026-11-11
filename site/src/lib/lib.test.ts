import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { atom, jsonFeed, newest } from "./feed";
import { activeCount, apply, counts, EMPTY, matchesQuery, parse, serialize, toggle, type Filters } from "./filters";
import { placeLine, rowFacts } from "./labels";
import { SnapshotSchema, type Role } from "./schema";
import { employers, postedPerDay, summary, tally } from "./stats";
import { ago, clock, groupOf, hasClockTime, longDate, postedMs, shortAge, shortDate, uaeDay } from "./time";

const NOW = Date.parse("2026-11-10T10:30:00Z"); // 14:30 in the UAE
const H = 3_600_000;
const D = 24 * H;

function role(over: Partial<Role> = {}): Role {
  return {
    id: "greenhouse:acme:1",
    slug: "acme-data-intern-abc123",
    employer: "Acme",
    board: "greenhouse:acme",
    system: "greenhouse",
    title: "Data Intern",
    url: "https://example.test/job/1",
    places: [{ emirate: "Dubai", raw: "Dubai" }],
    elsewhere: 0,
    kind: "internship",
    kind_reason: 'title says "Intern"',
    fields: ["Data and analytics"],
    skills: [],
    facts: {},
    excerpt: "",
    posted_at: new Date(NOW - 2 * H).toISOString(),
    first_seen: new Date(NOW - H).toISOString(),
    last_seen: new Date(NOW).toISOString(),
    status: "open",
    ...over,
  };
}

describe("time", () => {
  it("counts days in UAE time, not the reader's", () => {
    // 21:00 UTC on the 9th is already the 10th in the UAE.
    expect(uaeDay(Date.parse("2026-11-09T21:00:00Z"))).toBe(uaeDay(NOW));
    expect(groupOf(Date.parse("2026-11-09T21:00:00Z"), NOW)).toBe("Today");
    expect(groupOf(Date.parse("2026-11-09T19:00:00Z"), NOW)).toBe("Yesterday");
    expect(groupOf(NOW - 4 * D, NOW)).toBe("This week");
    expect(groupOf(NOW - 20 * D, NOW)).toBe("Earlier this month");
    expect(groupOf(NOW - 60 * D, NOW)).toBe("Older");
  });

  it("writes short ages the way a timetable does", () => {
    expect(shortAge(NOW - 20_000, NOW)).toBe("1 min");
    expect(shortAge(NOW - 25 * 60_000, NOW)).toBe("25 min");
    expect(shortAge(NOW - 3 * H, NOW)).toBe("3 h");
    expect(shortAge(NOW - 30 * H, NOW)).toBe("Yesterday");
    expect(shortAge(NOW - 3 * D, NOW)).toBe("3 d");
    expect(shortAge(NOW - 12 * D, NOW)).toBe("29 Oct");
    expect(shortAge(NOW + H, NOW)).toBe("1 min"); // a clock slightly ahead never shows a negative age
    expect(shortDate(Date.parse("2025-12-31T12:00:00Z"), NOW)).toBe("31 Dec 2025");
    expect(longDate(NOW)).toBe("10 Nov 2026");
    expect(clock(NOW)).toBe("14:30");
  });

  it("writes ages in sentences", () => {
    expect(ago(NOW - 10_000, NOW)).toBe("just now");
    expect(ago(NOW - 60_000, NOW)).toBe("1 minute ago");
    expect(ago(NOW - 12 * 60_000, NOW)).toBe("12 minutes ago");
    expect(ago(NOW - H, NOW)).toBe("1 hour ago");
    expect(ago(NOW - 3 * D, NOW)).toBe("3 days ago");
  });

  it("trusts the employer's date unless it is later than when the role was seen", () => {
    expect(postedMs(role())).toBe(NOW - 2 * H);
    expect(postedMs(role({ posted_at: new Date(NOW + D).toISOString() }))).toBe(NOW - H);
    expect(postedMs(role({ posted_at: null }))).toBe(NOW - H);
    expect(postedMs(role({ posted_at: "not a date" }))).toBe(NOW - H);
  });

  it("knows a date without a time from a real time", () => {
    expect(hasClockTime("2026-11-10T00:00:00+00:00")).toBe(false);
    expect(hasClockTime("2026-11-10T00:00:00.000Z")).toBe(false);
    expect(hasClockTime("2026-10-04T23:20:00-04:00")).toBe(true);
    expect(hasClockTime(null)).toBe(false);
  });
});

describe("filters", () => {
  const roles: Role[] = [
    role(),
    role({ id: "b", title: "Graduate Engineer", kind: "graduate", fields: ["Engineering"], places: [{ emirate: "Abu Dhabi", raw: "Abu Dhabi" }], posted_at: new Date(NOW - 10 * D).toISOString(), first_seen: new Date(NOW - 10 * D).toISOString() }),
    role({ id: "c", title: "Sales Trainee", employer: "Zed", fields: ["Sales and business development"], facts: { eligibility: { value: "nationals_only", label: "UAE nationals only", evidence: "UAE nationals only.", source: "text" } } }),
    role({ id: "d", title: "Old Intern", status: "closed" }),
    role({ id: "e", title: "Open Intern", facts: { eligibility: { value: "open", label: "Open to all nationalities", evidence: "All nationalities.", source: "text" } } }),
  ];

  it("round-trips through the address bar", () => {
    const f: Filters = { q: "data intern", kinds: ["internship", "graduate"], fields: ["Data and analytics"], places: ["Dubai"], eligibility: "unrestricted", age: "7", closed: true };
    expect(parse(new URLSearchParams(serialize(f)))).toEqual(f);
    expect(serialize(EMPTY)).toBe("");
    expect(parse(new URLSearchParams(""))).toEqual(EMPTY);
  });

  it("ignores values it does not know", () => {
    const f = parse(new URLSearchParams("kind=internship,boss&who=everyone&age=99&q=" + "x".repeat(200)));
    expect(f.kinds).toEqual(["internship"]);
    expect(f.eligibility).toBe("any");
    expect(f.age).toBe("any");
    expect(f.q).toHaveLength(80);
  });

  it("hides closed roles unless asked", () => {
    expect(apply(roles, EMPTY, NOW).map((r) => r.id)).not.toContain("d");
    expect(apply(roles, { ...EMPTY, closed: true }, NOW).map((r) => r.id)).toContain("d");
  });

  it("filters by kind, field, place and age", () => {
    expect(apply(roles, { ...EMPTY, kinds: ["graduate"] }, NOW).map((r) => r.id)).toEqual(["b"]);
    expect(apply(roles, { ...EMPTY, fields: ["Engineering"] }, NOW).map((r) => r.id)).toEqual(["b"]);
    expect(apply(roles, { ...EMPTY, places: ["Abu Dhabi"] }, NOW).map((r) => r.id)).toEqual(["b"]);
    expect(apply(roles, { ...EMPTY, age: "7" }, NOW).map((r) => r.id)).not.toContain("b");
  });

  it("'hide nationals-only' removes only roles that say so; silence is kept", () => {
    const shown = apply(roles, { ...EMPTY, eligibility: "unrestricted" }, NOW).map((r) => r.id);
    expect(shown).not.toContain("c");
    expect(shown).toContain("greenhouse:acme:1");
    expect(apply(roles, { ...EMPTY, eligibility: "open" }, NOW).map((r) => r.id)).toEqual(["e"]);
  });

  it("searches every word across title, employer, field, place and facts", () => {
    expect(matchesQuery(roles[0], "data dubai")).toBe(true);
    expect(matchesQuery(roles[0], "DATA  acme")).toBe(true);
    expect(matchesQuery(roles[0], "data london")).toBe(false);
    expect(matchesQuery(roles[2], "nationals")).toBe(true);
    expect(matchesQuery(roles[0], "   ")).toBe(true);
  });

  it("counts what each choice would show, ignoring its own group", () => {
    const c = counts(roles, { ...EMPTY, kinds: ["graduate"] }, NOW);
    expect(c.kinds.get("internship")).toBe(3);
    expect(c.kinds.get("graduate")).toBe(1);
    expect(c.places.get("Abu Dhabi")).toBe(1);
    expect(c.places.get("Dubai")).toBeUndefined();
  });

  it("counts active filters and toggles", () => {
    expect(activeCount(EMPTY)).toBe(0);
    expect(activeCount({ ...EMPTY, kinds: ["internship"], age: "7", closed: true })).toBe(3);
    expect(toggle(["a"], "b")).toEqual(["a", "b"]);
    expect(toggle(["a", "b"], "a")).toEqual(["b"]);
  });
});

describe("labels", () => {
  it("writes the place line and the row facts in a fixed order", () => {
    const r = role({
      elsewhere: 2,
      facts: {
        pay: { value: "paid", label: "Paid, amount not stated", evidence: "x", source: "text" },
        start: { value: "when", label: "June 2027", evidence: "x", source: "text" },
        eligibility: { value: "open", label: "Open to all nationalities", evidence: "x", source: "text" },
        deadline: { value: "date", label: "30 November 2026", evidence: "x", source: "text" },
      },
    });
    expect(placeLine(r)).toBe("Dubai + 2 elsewhere");
    expect(rowFacts(r).map((f) => f.text)).toEqual(["Starts June 2027", "Paid, amount not stated", "Apply by 30 November 2026"]);
    expect(rowFacts(role({ facts: { start: { value: "immediate", label: "Immediate start", evidence: "x", source: "text" } } }))[0].text).toBe("Starts now");
  });
});

describe("stats and feeds", () => {
  const snapshot = SnapshotSchema.parse({
    schema_version: 1,
    rules_version: 2,
    generated_at: new Date(NOW).toISOString(),
    started_at: new Date(NOW).toISOString(),
    roles: [role(), role({ id: "x", slug: "x", title: 'Risky <script>alert("1")</script> & Co', first_seen: new Date(NOW - 2 * D).toISOString(), posted_at: new Date(NOW - 2 * D).toISOString() }), role({ id: "y", slug: "y", status: "closed" })],
    boards: [
      { key: "greenhouse:acme", name: "Acme", system: "greenhouse", ok: true, checked_at: new Date(NOW).toISOString(), last_ok: new Date(NOW).toISOString(), postings: 40, uae: 9, student: 2 },
      { key: "lever:zed", name: "Zed", system: "lever", ok: false, error: "HTTP 500", checked_at: new Date(NOW).toISOString(), last_ok: null, postings: 0, uae: 0, student: 0 },
    ],
    not_covered: [],
  });

  it("counts from the snapshot", () => {
    const s = summary(snapshot, NOW);
    expect(s).toMatchObject({ open: 2, employers: 1, withRoles: 1, today: 1, week: 2, failed: 1, uaePostings: 9 });
    expect(employers(snapshot).map((e) => [e.name, e.student, e.ok])).toEqual([
      ["Acme", 2, true],
      ["Zed", 0, false],
    ]);
    const days = postedPerDay(snapshot.roles, NOW, 7);
    expect(days).toHaveLength(7);
    expect(days[6].n).toBe(2); // the open one and the closed one, both posted today
    expect(days[4].n).toBe(1);
    expect(tally(["a", "b", "a"])).toEqual([
      { name: "a", n: 2 },
      { name: "b", n: 1 },
    ]);
  });

  it("feeds list open roles newest first and escape employer text", () => {
    expect(newest(snapshot).map((r) => r.id)).toEqual(["greenhouse:acme:1", "x"]);
    const xml = atom(snapshot, "https://radar.test");
    expect(xml).toContain("<title>Data Intern at Acme</title>");
    expect(xml).not.toContain("<script>");
    expect(xml).toContain("&lt;script&gt;");
    expect(xml).toContain('<link href="https://radar.test/role/x"/>');
    const feed = jsonFeed(snapshot, "https://radar.test");
    expect(feed.items).toHaveLength(2);
    expect(feed.items[0].external_url).toBe("https://example.test/job/1");
  });

  it("refuses a snapshot whose links are not https", () => {
    const bad = { ...JSON.parse(JSON.stringify(snapshot)) };
    bad.roles[0].url = "javascript:alert(1)";
    expect(SnapshotSchema.safeParse(bad).success).toBe(false);
    bad.roles[0].url = "http://example.test/";
    expect(SnapshotSchema.safeParse(bad).success).toBe(false);
  });

  it("accepts the snapshot bundled with the site", () => {
    const raw = JSON.parse(readFileSync(path.join(process.cwd(), "public", "snapshot.sample.json"), "utf8"));
    const parsed = SnapshotSchema.safeParse(raw);
    expect(parsed.success).toBe(true);
    expect(parsed.data!.roles.length).toBeGreaterThan(0);
  });
});

describe("matching a CV", () => {
  it("reads a CV with the collector's own skill list", async () => {
    const { cvSkills, matched } = await import("./fit");
    const mine = cvSkills("Built a RAG pipeline in Python with FastAPI; SQL warehouse in DuckDB; React and TypeScript front ends; fluent in Hindi.");
    expect(mine).toEqual(["Python", "SQL", "TypeScript", "React", "Hindi or Urdu"]); // "SQL warehouse" is not logistics
    expect(cvSkills("We react quickly and support our R&D team.")).toEqual([]);
    expect(matched({ skills: ["SQL", "Excel", "Python"] }, mine)).toEqual(["SQL", "Python"]);
    expect(matched({ skills: [] }, mine)).toEqual([]);
  });
});
