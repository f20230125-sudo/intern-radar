"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { activeCount, apply, counts, EMPTY, serialize, toggle, type Age, type Filters } from "@/lib/filters";
import { cvSkills, matched as matchedSkills } from "@/lib/fit";
import { KIND_SHORT } from "@/lib/labels";
import { KINDS, type Kind, type Role } from "@/lib/schema";
import { ago, groupOf, GROUPS, postedMs, type Group } from "@/lib/time";

import { FitPanel } from "./FitPanel";
import { Chevron, Search, Sliders, Star } from "./icons";
import { RoleRow } from "./RoleRow";

type Props = {
  roles: Role[];
  generatedAt: string;
  serverNow: number;
  initial: Filters;
};

const DAY = 86_400_000;
const AGES: { value: Age; label: string }[] = [
  { value: "any", label: "Any time" },
  { value: "1", label: "Last 24 hours" },
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
];

function readSet(key: string): Set<string> {
  try {
    const raw = JSON.parse(localStorage.getItem(key) ?? "[]");
    return new Set(Array.isArray(raw) ? raw.filter((x) => typeof x === "string").slice(0, 500) : []);
  } catch {
    return new Set();
  }
}

export function RoleBoard({ roles, generatedAt, serverNow, initial }: Props) {
  const router = useRouter();
  const [filters, setFilters] = useState<Filters>(initial);
  const [now, setNow] = useState(serverNow);
  const [open, setOpen] = useState<string | null>(null);
  const [saved, setSaved] = useState<Set<string>>(new Set());
  const [onlySaved, setOnlySaved] = useState(false);
  const [since, setSince] = useState<number | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);
  const [fresh, setFresh] = useState<{ at: string; open: number } | null>(null);
  const [arrived, setArrived] = useState<Set<string>>(new Set());
  const [pinged, setPinged] = useState(false);
  const [fitOpen, setFitOpen] = useState(false);
  const [mine, setMine] = useState<string[] | null>(null);
  const [byFit, setByFit] = useState(true);
  const searchRef = useRef<HTMLInputElement>(null);
  const known = useRef<Set<string> | null>(null);

  // Things only the browser knows: the clock, what was saved, when this reader last looked.
  useEffect(() => {
    const start = window.setTimeout(() => {
      setNow(Date.now());
      setSaved(readSet("ir-saved"));
      let last: number | null = null;
      try {
        const raw = Number(localStorage.getItem("ir-seen"));
        last = Number.isFinite(raw) && raw > 0 ? raw : null;
      } catch {
        last = null;
      }
      try {
        const kept = JSON.parse(sessionStorage.getItem("ir-fit") ?? "null");
        if (Array.isArray(kept) && kept.every((x) => typeof x === "string")) setMine(kept.slice(0, 80));
      } catch {
        // nothing kept
      }
      // A first-time reader has no "last visit"; the last day stands in for it.
      setSince(last ?? Date.now() - DAY);
    }, 0);
    const remember = () => {
      try {
        localStorage.setItem("ir-seen", String(Date.now()));
      } catch {
        // storage refused: the marker just will not persist
      }
    };
    const onHide = () => document.visibilityState === "hidden" && remember();
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("pagehide", remember);
    const tick = window.setInterval(() => setNow(Date.now()), 60_000);
    return () => {
      window.clearTimeout(start);
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("pagehide", remember);
      window.clearInterval(tick);
    };
  }, []);

  // Rows that were not in the list before a refresh arrive with a signal edge.
  useEffect(() => {
    const ids = new Set(roles.map((r) => r.id));
    if (known.current) {
      const added = [...ids].filter((id) => !known.current!.has(id));
      if (added.length) {
        const on = window.setTimeout(() => {
          setArrived(new Set(added));
          setPinged(true);
        }, 0);
        const off = window.setTimeout(() => {
          setArrived(new Set());
          setPinged(false);
        }, 7000);
        known.current = ids;
        return () => {
          window.clearTimeout(on);
          window.clearTimeout(off);
        };
      }
    }
    known.current = ids;
  }, [roles]);

  // Ask now and then whether a newer snapshot exists. The list is never swapped under the reader: they choose.
  useEffect(() => {
    let stop = false;
    const check = async () => {
      if (document.visibilityState !== "visible") return;
      try {
        const res = await fetch("/api/meta", { cache: "no-store" });
        if (!res.ok) return;
        const meta = (await res.json()) as { generated_at: string; open: number };
        if (!stop && Date.parse(meta.generated_at) > Date.parse(generatedAt)) setFresh({ at: meta.generated_at, open: meta.open });
      } catch {
        // offline or blocked: the page keeps what it has
      }
    };
    const id = window.setInterval(check, 150_000);
    document.addEventListener("visibilitychange", check);
    return () => {
      stop = true;
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", check);
    };
  }, [generatedAt]);

  const update = useCallback((next: Filters) => {
    setFilters(next);
    const qs = serialize(next);
    window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
  }, []);

  const toggleOpen = useCallback((id: string) => setOpen((cur) => (cur === id ? null : id)), []);
  const toggleSave = useCallback((id: string) => {
    setSaved((cur) => {
      const next = new Set(cur);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      try {
        localStorage.setItem("ir-saved", JSON.stringify([...next]));
      } catch {
        // storage refused
      }
      return next;
    });
  }, []);

  const fit = useMemo(() => {
    const map = new Map<string, string[]>();
    if (mine) for (const r of roles) map.set(r.id, matchedSkills(r, mine));
    return map;
  }, [roles, mine]);
  const ranked = mine !== null && byFit;
  const visible = useMemo(() => {
    const list = apply(roles, filters, now).filter((r) => !onlySaved || saved.has(r.id));
    const newest = (a: Role, b: Role) => postedMs(b) - postedMs(a);
    return list.sort(ranked ? (a, b) => (fit.get(b.id)?.length ?? 0) - (fit.get(a.id)?.length ?? 0) || newest(a, b) : newest);
  }, [roles, filters, now, onlySaved, saved, ranked, fit]);
  const setCv = useCallback((text: string | null) => {
    const found = text === null ? null : cvSkills(text);
    setMine(found);
    setByFit(true);
    try {
      if (found) sessionStorage.setItem("ir-fit", JSON.stringify(found));
      else sessionStorage.removeItem("ir-fit");
    } catch {
      // storage refused: the match lasts until the page is closed
    }
  }, []);
  const tallies = useMemo(() => counts(roles, filters, now), [roles, filters, now]);
  const fields = useMemo(() => [...new Set(roles.flatMap((r) => r.fields))].sort((a, b) => (a === "Other" ? 1 : b === "Other" ? -1 : a.localeCompare(b))), [roles]);
  const places = useMemo(() => [...new Set(roles.flatMap((r) => r.places.map((p) => p.emirate)))].sort(), [roles]);
  const groups = useMemo(() => {
    if (ranked) {
      // Ranked by fit, the list is two groups: roles that name a skill from the CV, and the rest.
      const hit = visible.filter((r) => (fit.get(r.id)?.length ?? 0) > 0);
      const rest = visible.filter((r) => (fit.get(r.id)?.length ?? 0) === 0);
      return [
        { name: "Name a skill from your CV", roles: hit },
        { name: "Name none of them", roles: rest },
      ].filter((g) => g.roles.length);
    }
    const map = new Map<Group, Role[]>();
    for (const r of visible) {
      const g = groupOf(postedMs(r), now);
      map.set(g, [...(map.get(g) ?? []), r]);
    }
    return GROUPS.filter((g) => map.has(g)).map((g) => ({ name: g, roles: map.get(g)! }));
  }, [visible, now, ranked, fit]);

  // Keyboard: "/" to search, j and k between rows, Escape to close.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const typing = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
      if (e.key === "Escape") {
        document.querySelectorAll<HTMLDetailsElement>("details.pick[open]").forEach((d) => (d.open = false));
        if (typing) (target as HTMLInputElement).blur();
        else setOpen(null);
        return;
      }
      if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "/") {
        e.preventDefault();
        searchRef.current?.focus();
      } else if (e.key === "j" || e.key === "k") {
        const heads = [...document.querySelectorAll<HTMLButtonElement>(".row-head")];
        if (!heads.length) return;
        const at = heads.indexOf(document.activeElement as HTMLButtonElement);
        const next = e.key === "j" ? Math.min(heads.length - 1, at + 1) : Math.max(0, at === -1 ? 0 : at - 1);
        heads[next].focus();
        heads[next].scrollIntoView({ block: "nearest" });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // A menu closes when the reader clicks anywhere else.
  useEffect(() => {
    const onDown = (e: PointerEvent) => {
      document.querySelectorAll<HTMLDetailsElement>("details.pick[open]").forEach((d) => {
        if (!d.contains(e.target as Node)) d.open = false;
      });
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, []);

  const active = activeCount(filters) + (onlySaved ? 1 : 0);
  const openCount = roles.filter((r) => r.status === "open").length;
  const hideNationals = filters.eligibility === "unrestricted";

  return (
    <>
      <div className="bar">
        <div className="wrap bar-in" role="search" aria-label="Filter roles">
          <div className="search">
            <Search />
            <input
              ref={searchRef}
              type="search"
              inputMode="search"
              autoComplete="off"
              spellCheck={false}
              aria-label="Search roles, employers and fields"
              placeholder="Search roles"
              value={filters.q}
              onChange={(e) => update({ ...filters, q: e.target.value.slice(0, 80) })}
            />
            <kbd aria-hidden="true">/</kbd>
          </div>
          <button type="button" className="ctl bar-toggle" aria-expanded={moreOpen} aria-controls="more-filters" onClick={() => setMoreOpen((v) => !v)}>
            <Sliders />
            Filter{active ? ` (${active})` : ""}
          </button>
          <div className="bar-more" id="more-filters" data-open={moreOpen || undefined}>
            <div className="seg" role="group" aria-label="Kind of role">
              {KINDS.map((k: Kind) => (
                <button key={k} type="button" aria-pressed={filters.kinds.includes(k)} onClick={() => update({ ...filters, kinds: toggle(filters.kinds, k) })}>
                  {KIND_SHORT[k]}
                  <span className="n">{tallies.kinds.get(k) ?? 0}</span>
                </button>
              ))}
            </div>
            <Pick label="Field" chosen={filters.fields} options={fields} tally={tallies.fields} onChange={(v) => update({ ...filters, fields: v })} />
            <Pick label="Place" chosen={filters.places} options={places} tally={tallies.places} onChange={(v) => update({ ...filters, places: v })} />
            <button
              type="button"
              className="ctl"
              aria-pressed={hideNationals}
              title="Hide roles that say they are for UAE nationals only"
              onClick={() => update({ ...filters, eligibility: hideNationals ? "any" : "unrestricted" })}
            >
              Hide nationals-only
            </button>
            <details className="pick" data-on={filters.age !== "any" || undefined}>
              <summary>
                {AGES.find((a) => a.value === filters.age)!.label}
                <Chevron />
              </summary>
              <div className="menu right" role="group" aria-label="Posted within">
                {AGES.map((a) => (
                  <label key={a.value} className="opt">
                    <input type="radio" name="age" checked={filters.age === a.value} onChange={() => update({ ...filters, age: a.value })} />
                    {a.label}
                  </label>
                ))}
                <label className="opt" style={{ borderTop: "1px solid var(--rule)", marginTop: 6, paddingTop: 6 }}>
                  <input type="checkbox" checked={filters.closed} onChange={(e) => update({ ...filters, closed: e.target.checked })} />
                  Include closed roles
                </label>
              </div>
            </details>
            {active || filters.q ? (
              <button
                type="button"
                className="clear"
                onClick={() => {
                  setOnlySaved(false);
                  update(EMPTY);
                }}
              >
                Clear
              </button>
            ) : null}
          </div>
        </div>
      </div>

      <div className="wrap">
        {fresh ? (
          <div className="notice" role="status">
            <span className={`dot${pinged ? " pinged" : ""}`} />
            <span>
              A newer check landed {ago(Date.parse(fresh.at), now)}: {fresh.open} roles open, {fresh.open - openCount === 0 ? "same count, details may have changed" : `${Math.abs(fresh.open - openCount)} ${fresh.open > openCount ? "more" : "fewer"} than shown`}.
            </span>
            <button
              type="button"
              className="btn"
              onClick={() => {
                setFresh(null);
                router.refresh();
              }}
            >
              Show the latest
            </button>
          </div>
        ) : null}

        <div className="count">
          <span aria-live="polite">
            {visible.length === openCount && !active && !filters.q
              ? `${openCount} open role${openCount === 1 ? "" : "s"}, ${ranked ? "best match first" : "newest first"}`
              : `${visible.length} of ${filters.closed ? roles.length : openCount} role${visible.length === 1 ? "" : "s"}`}
          </span>
          <span className="count-tools">
            {mine ? (
              <button type="button" className="saved" aria-pressed={byFit} onClick={() => setByFit((v) => !v)}>
                {byFit ? "Sorted by match" : "Sort by match"}
              </button>
            ) : null}
            <button type="button" className="saved" aria-expanded={fitOpen} aria-controls="fit-panel" onClick={() => setFitOpen((v) => !v)}>
              {mine ? `Your CV: ${mine.length} skill${mine.length === 1 ? "" : "s"}` : "Match my CV"}
            </button>
            {saved.size || onlySaved ? (
              <button type="button" className="saved" aria-pressed={onlySaved} onClick={() => setOnlySaved((v) => !v)}>
                <Star on={onlySaved} />
                {onlySaved ? "Showing saved" : "Saved"} ({saved.size})
              </button>
            ) : null}
          </span>
        </div>
        {fitOpen ? <FitPanel skills={mine} onMatch={setCv} onClose={() => setFitOpen(false)} /> : null}

        {groups.length ? (
          groups.map((g) => (
            <section key={g.name} aria-label={g.name}>
              <h2 className="group-h">
                {g.name}
                <span className="n">{g.roles.length}</span>
              </h2>
              <ul className="rows">
                {g.roles.map((r) => (
                  <RoleRow
                    key={r.id}
                    role={r}
                    now={now}
                    open={open === r.id}
                    isNew={since !== null && Date.parse(r.first_seen) > since && r.status === "open"}
                    arrived={arrived.has(r.id)}
                    saved={saved.has(r.id)}
                    matched={mine ? fit.get(r.id) : undefined}
                    onToggle={toggleOpen}
                    onSave={toggleSave}
                  />
                ))}
              </ul>
            </section>
          ))
        ) : (
          <div className="empty">
            <h2>{roles.length ? "Nothing matches those filters." : "No roles are listed yet."}</h2>
            <p>
              {roles.length
                ? "Student roles in the UAE are few at any one time, so a narrow filter often comes back empty. Clear a filter, or save this address and look again later: the list is read every hour."
                : "The first check has not finished. Come back in a few minutes."}
            </p>
            {roles.length ? (
              <div className="actions">
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    setOnlySaved(false);
                    update(EMPTY);
                  }}
                >
                  Clear all filters
                </button>
              </div>
            ) : null}
          </div>
        )}
        {groups.length ? (
          <p className="keys-hint label">
            Keyboard: <kbd>/</kbd> search, <kbd>j</kbd> <kbd>k</kbd> move between roles, <kbd>Enter</kbd> open, <kbd>Esc</kbd> close.
          </p>
        ) : null}
      </div>
    </>
  );
}

function Pick({ label, chosen, options, tally, onChange }: { label: string; chosen: string[]; options: string[]; tally: Map<string, number>; onChange: (v: string[]) => void }) {
  return (
    <details className="pick" data-on={chosen.length ? true : undefined}>
      <summary>
        {label}
        {chosen.length ? ` (${chosen.length})` : ""}
        <Chevron />
      </summary>
      <div className="menu" role="group" aria-label={label}>
        {options.map((o) => {
          const n = tally.get(o) ?? 0;
          return (
            <label key={o} className="opt" data-zero={n === 0 && !chosen.includes(o) ? true : undefined}>
              <input type="checkbox" checked={chosen.includes(o)} onChange={() => onChange(toggle(chosen, o))} />
              {o}
              <span className="n">{n}</span>
            </label>
          );
        })}
      </div>
    </details>
  );
}
