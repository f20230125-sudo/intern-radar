import { shortDate } from "@/lib/time";

const DAY = 86_400_000;

/** One bar a day: how many of the listed roles were posted on each of the last five weeks' days. */
export function Strip({ days, now }: { days: { day: number; n: number }[]; now: number }) {
  const max = Math.max(1, ...days.map((d) => d.n));
  const total = days.reduce((s, d) => s + d.n, 0);
  const last = days.length - 1;
  const busiest = days.reduce((a, b) => (b.n > a.n ? b : a), days[0]);
  const label =
    total === 0
      ? `No listed role was posted in the last ${days.length} days.`
      : `${total} of the listed roles were posted in the last ${days.length} days. The busiest day was ${shortDate(busiest.day * DAY, now)} with ${busiest.n}.`;
  return (
    <figure className="strip">
      <div className="strip-bars" role="img" aria-label={label}>
        {days.map((d, i) => (
          <i
            key={d.day}
            data-empty={d.n === 0 || undefined}
            data-today={i === last && d.n > 0 ? true : undefined}
            style={{ height: `${Math.round((d.n / max) * 100)}%` }}
            title={`${shortDate(d.day * DAY, now)}: ${d.n} posted`}
          />
        ))}
      </div>
      <figcaption className="strip-cap label">
        <span>{shortDate(days[0].day * DAY, now)}</span>
        <span>Roles posted per day</span>
        <span>Today</span>
      </figcaption>
    </figure>
  );
}
