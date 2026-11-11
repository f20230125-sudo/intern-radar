import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Out } from "@/components/icons";
import { Ledger } from "@/components/Ledger";
import { Restriction } from "@/components/RoleRow";
import { KIND_LABEL, KIND_NOTE, placeLine, SYSTEM_NAME } from "@/lib/labels";
import { loadSnapshot } from "@/lib/snapshot";
import type { Role } from "@/lib/schema";
import { ago, clock, groupOf, hasClockTime, longDate, postedMs } from "@/lib/time";

type Params = Promise<{ slug: string }>;

async function find(slug: string) {
  const { snapshot, now } = await loadSnapshot();
  return { snapshot, now, role: snapshot.roles.find((r) => r.slug === slug) };
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const { role } = await find(slug);
  if (!role) return { title: "Role not found" };
  const facts = Object.values(role.facts)
    .map((f) => f?.label)
    .filter(Boolean)
    .slice(0, 3)
    .join(", ");
  return {
    title: `${role.title} at ${role.employer}`,
    description: `${KIND_LABEL[role.kind]} at ${role.employer}, ${placeLine(role)}.${facts ? ` ${facts}.` : ""} Read from the employer's own posting.`,
    alternates: { canonical: `/role/${role.slug}` },
  };
}

function posted(role: Role, now: number) {
  const ms = postedMs(role);
  if (hasClockTime(role.posted_at) || !role.posted_at) return `Posted ${ago(ms, now)}`;
  const g = groupOf(ms, now);
  return g === "Today" ? "Posted today" : g === "Yesterday" ? "Posted yesterday" : `Posted ${longDate(ms)}`;
}

function stamp(iso: string) {
  const ms = Date.parse(iso);
  return hasClockTime(iso) ? `${longDate(ms)}, ${clock(ms)} UAE time` : longDate(ms);
}

export default async function RolePage({ params }: { params: Params }) {
  const { slug } = await params;
  const { snapshot, role, now } = await find(slug);
  if (!role) notFound();

  const closed = role.status === "closed";
  const others = snapshot.roles.filter((r) => r.board === role.board && r.id !== role.id && r.status === "open").slice(0, 6);
  const events: { at: string; text: string }[] = [];
  if (role.posted_at && Date.parse(role.posted_at) <= Date.parse(role.first_seen)) events.push({ at: role.posted_at, text: `Posted by ${role.employer}` });
  events.push({ at: role.first_seen, text: "First seen by Intern Radar" });
  if (role.changed_at) events.push({ at: role.changed_at, text: "The posting was edited" });
  if (closed && role.closed_at) events.push({ at: role.closed_at, text: "No longer listed by the employer" });
  else events.push({ at: role.last_seen, text: "Still listed at the last check" });

  return (
    <div className="wrap page">
      <p className="crumb">
        <Link href="/">Roles</Link> / {role.employer}
      </p>
      <h1 style={{ marginTop: 14, maxWidth: "26ch", ...(closed ? { color: "var(--ink-3)" } : {}) }}>{role.title}</h1>
      <p className="role-meta">
        <span>
          <strong style={{ color: "var(--ink)" }}>{role.employer}</strong>
        </span>
        <span>{placeLine(role)}</span>
        <span>{KIND_LABEL[role.kind]}</span>
        <span>{closed ? `Closed ${ago(Date.parse(role.closed_at ?? role.last_seen), now)}` : posted(role, now)}</span>
      </p>
      <Restriction role={role} />

      {closed ? (
        <p className="notice" style={{ borderColor: "var(--rule-2)", background: "var(--wash)" }}>
          This role is no longer on {role.employer}&rsquo;s board. It is kept here for a while so a saved link still explains what it was.
        </p>
      ) : (
        <div className="actions">
          <a className="btn" href={role.url} target="_blank" rel="noopener noreferrer">
            Open the posting at {role.employer}
            <Out />
          </a>
        </div>
      )}

      <h2 className="h2">What the posting says</h2>
      <Ledger role={role} all />
      <p className="why">
        Each line was read by a rule from the sentence beside it. A line marked &ldquo;not stated&rdquo; means the posting does not say; it does not mean no.
      </p>

      {role.excerpt ? (
        <>
          <h2 className="h2">About the role</h2>
          <div className="prose">
            <p>{role.excerpt}</p>
          </div>
        </>
      ) : null}

      <h2 className="h2">Why it is listed here</h2>
      <div className="prose">
        <p>
          Listed as <strong>{KIND_LABEL[role.kind].toLowerCase()}</strong>: {role.kind_reason}. {KIND_NOTE[role.kind]} Filed under{" "}
          {role.fields.join(" and ")}
          {role.department ? `; the employer's own department is ${role.department}` : ""}.
        </p>
        <p>
          Read from {role.employer}&rsquo;s board on {SYSTEM_NAME[role.system] ?? role.system}.
        </p>
      </div>

      <h2 className="h2">Timeline</h2>
      <ol className="timeline">
        {events.map((e) => (
          <li key={e.text}>
            <time dateTime={e.at}>{stamp(e.at)}</time>
            {e.text}
          </li>
        ))}
      </ol>

      {others.length ? (
        <>
          <h2 className="h2">Other student roles at {role.employer}</h2>
          <ul className="rows">
            {others.map((r) => (
              <li key={r.id} className="row" style={{ padding: "12px 0" }}>
                <Link href={`/role/${r.slug}`} style={{ fontWeight: 600 }}>
                  {r.title}
                </Link>
                <div className="row-facts" style={{ marginTop: 3 }}>
                  <span className="place">{placeLine(r)}</span>
                  <span>{KIND_LABEL[r.kind]}</span>
                </div>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}
