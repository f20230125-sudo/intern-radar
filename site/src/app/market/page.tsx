import type { Metadata } from "next";

import { FACT_NAME, KIND_PLURAL } from "@/lib/labels";
import type { FactKey, Kind } from "@/lib/schema";
import { loadSnapshot } from "@/lib/snapshot";
import { openRoles, pct, summary, tally } from "@/lib/stats";
import { longDate, postedMs } from "@/lib/time";

// Read at request time: the numbers on this page change with every hourly check.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "The market for student roles in the UAE",
  description: "How many student roles are open at UAE employers, in which fields and emirates, how many are limited to UAE nationals, and what postings leave unsaid.",
  alternates: { canonical: "/market" },
};

function Bars({ rows, total }: { rows: { name: string; n: number }[]; total: number }) {
  const max = Math.max(1, ...rows.map((r) => r.n));
  return (
    <div className="bars" role="list">
      {rows.map((r) => (
        <div key={r.name} role="listitem" aria-label={`${r.name}: ${r.n} of ${total}`}>
          <span>{r.name}</span>
          <span className="track" aria-hidden="true">
            <span className="fill" style={{ width: `${(r.n / max) * 100}%`, display: "block" }} />
          </span>
          <span className="v">{r.n}</span>
        </div>
      ))}
    </div>
  );
}

// Five greys and a hatch, darkest first, so the parts are told apart without hue and print as they look.
const SHADES = [
  "var(--ink)",
  "var(--ink-2)",
  "var(--ink-3)",
  "var(--rule-2)",
  "repeating-linear-gradient(135deg, var(--rule-2) 0 2px, var(--wash) 2px 6px)",
];

function Share({ parts, total }: { parts: { name: string; n: number }[]; total: number }) {
  const shown = parts.filter((p) => p.n > 0);
  return (
    <>
      <div className="share" role="img" aria-label={shown.map((p) => `${p.name}: ${p.n} of ${total}`).join(". ")}>
        {shown.map((p, i) => (
          <i key={p.name} style={{ flex: p.n, background: SHADES[i % SHADES.length] }} />
        ))}
      </div>
      <p className="keys">
        {shown.map((p, i) => (
          <span key={p.name}>
            <i style={{ background: SHADES[i % SHADES.length], border: "1px solid var(--rule-2)" }} />
            {p.name} {p.n} ({pct(p.n, total)})
          </span>
        ))}
      </p>
    </>
  );
}

export default async function Market() {
  const { snapshot, now } = await loadSnapshot();
  const open = openRoles(snapshot);
  const n = open.length;
  const s = summary(snapshot, now);

  const kinds = tally(open.map((r) => r.kind)).map((k) => ({ name: KIND_PLURAL[k.name as Kind], n: k.n }));
  const fields = tally(open.flatMap((r) => r.fields));
  const places = tally(open.flatMap((r) => r.places.map((p) => p.emirate)));
  const employers = tally(open.map((r) => r.employer)).slice(0, 12);

  const who = (v: string | undefined) =>
    v === "nationals_only" ? "UAE nationals only" : v === "nationals_preferred" ? "UAE nationals preferred" : v === "open" ? "Says open to all" : v === "own_visa" ? "Needs your own visa" : "Does not say";
  const order = ["UAE nationals only", "UAE nationals preferred", "Says open to all", "Needs your own visa", "Does not say"];
  const eligibility = tally(open.map((r) => who(r.facts.eligibility?.value))).sort((a, b) => order.indexOf(a.name) - order.indexOf(b.name));

  const stated: FactKey[] = ["stage", "start", "duration", "pay", "eligibility", "deadline"];
  const called: Partial<Record<FactKey, string>> = { stage: "Stage of study", start: "Start date", deadline: "Closing date" };
  const says = stated.map((k) => ({ name: called[k] ?? FACT_NAME[k], n: open.filter((r) => r.facts[k]).length })).sort((a, b) => b.n - a.n);
  const paid = open.filter((r) => r.facts.pay && r.facts.pay.value !== "unpaid").length;
  const amount = open.filter((r) => r.facts.pay?.value === "amount").length;
  const unpaid = open.filter((r) => r.facts.pay?.value === "unpaid").length;

  const ages = open.map((r) => Math.floor((now - postedMs(r)) / 86_400_000)).sort((a, b) => a - b);
  const median = ages.length ? ages[Math.floor(ages.length / 2)] : 0;

  return (
    <div className="wrap page">
      <h1>The market, counted from what is open today.</h1>
      <p className="sub">
        {n} student roles are open across the {s.employers} employers read, out of {s.uaePostings.toLocaleString("en")} UAE roles on their boards: about{" "}
        {pct(n, s.uaePostings)}. Every number on this page is counted from the roles listed on {longDate(Date.parse(snapshot.generated_at))}, so it describes
        these employers, not the whole country.
      </p>

      <div className="big">
        <div>
          <b>{n}</b>
          <span>student roles open</span>
        </div>
        <div>
          <b>{s.withRoles}</b>
          <span>employers with at least one</span>
        </div>
        <div>
          <b>{s.week}</b>
          <span>posted in the last 7 days</span>
        </div>
        <div>
          <b>{median}</b>
          <span>days: median age of an open role</span>
        </div>
      </div>

      <h2 className="h2">Who can apply</h2>
      <div className="fig">
        <p className="note">
          What each posting says about nationality or visa. &ldquo;Does not say&rdquo; is the honest reading of most postings: it is not a promise that anyone
          may apply.
        </p>
        <Share parts={eligibility} total={n} />
      </div>

      <div className="figs">
        <div className="fig">
          <h3>Kind of role</h3>
          <p className="note">Of {n} open roles.</p>
          <Bars rows={kinds} total={n} />
        </div>
        <div className="fig">
          <h3>Emirate</h3>
          <p className="note">A role in two emirates counts in both. &ldquo;UAE&rdquo; means the posting names only the country.</p>
          <Bars rows={places} total={n} />
        </div>
        <div className="fig">
          <h3>Field</h3>
          <p className="note">From the title, then the employer&rsquo;s department. A role can sit in two fields.</p>
          <Bars rows={fields} total={n} />
        </div>
        <div className="fig">
          <h3>Employers with the most student roles</h3>
          <p className="note">Open now.</p>
          <Bars rows={employers} total={n} />
        </div>
      </div>

      <h2 className="h2">What postings leave unsaid</h2>
      <div className="figs">
        <div className="fig">
          <h3>How many postings state each fact</h3>
          <p className="note">Of {n} open roles. The shorter the bar, the more often a student has to ask.</p>
          <Bars rows={says} total={n} />
        </div>
        <div className="fig">
          <h3>Pay</h3>
          <div className="prose">
            <p>
              <strong>
                {amount} of {n}
              </strong>{" "}
              postings name an amount. {paid - amount} more say the role is paid without a figure, {unpaid} say it is unpaid, and{" "}
              <strong>{n - paid - unpaid}</strong> ({pct(n - paid - unpaid, n)}) do not mention pay at all.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
