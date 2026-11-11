"use client";

import Link from "next/link";
import { memo } from "react";

import { KIND_LABEL, placeLine, rowFacts } from "@/lib/labels";
import type { Role } from "@/lib/schema";
import { hasClockTime, longDate, postedMs, shortAge, shortDate } from "@/lib/time";

import { Chevron, Link2, Lock, Out, Star } from "./icons";
import { Ledger } from "./Ledger";

type Props = {
  role: Role;
  now: number;
  open: boolean;
  isNew: boolean;
  arrived: boolean;
  saved: boolean;
  matched?: string[];
  onToggle: (id: string) => void;
  onSave: (id: string) => void;
};

export function Restriction({ role }: { role: Role }) {
  const e = role.facts.eligibility;
  if (!e) return null;
  if (e.value === "nationals_only")
    return (
      <span className="lock">
        <Lock />
        {e.label}
      </span>
    );
  return <span className="lock soft">{e.label}</span>;
}

function RoleRowInner({ role, now, open, isNew, arrived, saved, matched, onToggle, onSave }: Props) {
  const posted = postedMs(role);
  const precise = hasClockTime(role.posted_at) || !role.posted_at;
  const facts = rowFacts(role);
  const closed = role.status === "closed";
  const panel = `d-${role.slug}`;
  return (
    <li className="row" data-open={open || undefined} data-closed={closed || undefined} data-arrived={arrived || undefined} data-id={role.id}>
      <h3 style={{ font: "inherit" }}>
        <button type="button" className="row-head" aria-expanded={open} aria-controls={panel} onClick={() => onToggle(role.id)}>
          <span className="row-time">
            <time dateTime={new Date(posted).toISOString()} title={`Posted ${longDate(posted)}`}>
              {precise ? shortAge(posted, now) : shortDate(posted, now)}
            </time>
            {closed ? <span>Closed</span> : isNew ? <span className="new">New</span> : null}
          </span>
          <span>
            <span className="row-employer">
              {role.employer}
              <span className="kind-inline"> · {KIND_LABEL[role.kind]}</span>
            </span>
            <span className="row-title">{role.title}</span>
            <span className="row-facts">
              <span className="place">{placeLine(role)}</span>
              {facts.map((f) => (
                <span key={f.key}>{f.text}</span>
              ))}
            </span>
            <Restriction role={role} />
            {matched?.length ? (
              <span className="fit">
                <span className="fit-n">{matched.length}</span> from your CV: {matched.join(", ")}
              </span>
            ) : null}
          </span>
          <span className="row-side">
            <span className="kind">{KIND_LABEL[role.kind]}</span>
            <Chevron className="chev" />
          </span>
        </button>
      </h3>
      {open ? (
        <div className="detail" id={panel}>
          <div>
            {role.excerpt ? <p className="excerpt">{role.excerpt}</p> : null}
            <Ledger role={role} />
            {role.skills.length ? (
              <p className="why" style={{ marginTop: 14 }}>
                Skills the posting names: {role.skills.join(", ")}.
              </p>
            ) : null}
            <p className="why" style={{ marginTop: role.skills.length ? 4 : 14 }}>
              Listed as {KIND_LABEL[role.kind].toLowerCase()}: {role.kind_reason}. Filed under {role.fields.join(" and ")}.
            </p>
            <div className="actions">
              {closed ? null : (
                <a className="btn" href={role.url} target="_blank" rel="noopener noreferrer">
                  Open the posting at {role.employer}
                  <Out />
                </a>
              )}
              <Link className="btn quiet" href={`/role/${role.slug}`}>
                <Link2 />
                Role page
              </Link>
              <button type="button" className="btn quiet" aria-pressed={saved} onClick={() => onSave(role.id)}>
                <Star on={saved} />
                {saved ? "Saved" : "Save"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </li>
  );
}

export const RoleRow = memo(RoleRowInner);
