import { RoleBoard } from "@/components/RoleBoard";
import { Strip } from "@/components/Strip";
import { parse } from "@/lib/filters";
import { loadSnapshot } from "@/lib/snapshot";
import { postedPerDay, summary } from "@/lib/stats";
import { ago, clock } from "@/lib/time";

type Search = Promise<Record<string, string | string[] | undefined>>;

export default async function Home({ searchParams }: { searchParams: Search }) {
  const raw = await searchParams;
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(raw)) if (typeof v === "string") params.set(k, v);

  const { snapshot, source, now } = await loadSnapshot();
  const checked = Date.parse(snapshot.generated_at);
  const s = summary(snapshot, now);
  const stale = now - checked > 3 * 3_600_000;

  return (
    <>
      <div className="wrap lede">
        <div>
          <h1>
            <b>{s.open}</b> student {s.open === 1 ? "role" : "roles"} open at UAE employers right now.
          </h1>
          <p className="lede-sub">
            Internships, graduate programmes and first jobs, read every hour from {s.employers} employers&rsquo; own career systems. Open a role to see each
            fact beside the sentence it was read from.
          </p>
          <p className="status">
            <span className={`dot${stale ? " stale" : ""}`} />
            <span>
              Checked {ago(checked, now)}, at {clock(checked)} UAE time
              {s.today ? ` · ${s.today} posted today` : ""}
              {source === "bundled" ? " · showing a saved copy" : ""}
              {stale ? " · the hourly check is late" : ""}
            </span>
          </p>
        </div>
        <Strip days={postedPerDay(snapshot.roles, now)} now={now} />
      </div>
      <RoleBoard roles={snapshot.roles} generatedAt={snapshot.generated_at} serverNow={now} initial={parse(params)} />
    </>
  );
}
