import type { Metadata } from "next";
import Link from "next/link";

import { SYSTEM_NAME } from "@/lib/labels";
import { loadSnapshot } from "@/lib/snapshot";
import { employers } from "@/lib/stats";
import { ago } from "@/lib/time";

// Read at request time: the numbers on this page change with every hourly check.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Employers watched",
  description: "Every employer Intern Radar reads, the career system it uses, how many UAE roles it lists and when it was last checked.",
  alternates: { canonical: "/employers" },
};

export default async function Employers() {
  const { snapshot, now } = await loadSnapshot();
  const boards = employers(snapshot);
  const failed = boards.filter((b) => !b.ok);
  const withRoles = boards.filter((b) => b.student > 0).length;
  const uae = boards.reduce((s, b) => s + b.uae, 0);

  return (
    <div className="wrap page">
      <h1>{boards.length} employers, read every hour.</h1>
      <p className="sub">
        Between them they list {uae.toLocaleString("en")} roles in the UAE today. {withRoles} of them have at least one student role open.{" "}
        {failed.length ? `${failed.length} could not be read at the last check; their roles are kept as they were.` : "All of them answered at the last check."}
      </p>

      <div className="table-wrap" tabIndex={0} role="region" aria-label="Employers watched">
        <table className="t">
          <thead>
            <tr>
              <th scope="col">Employer</th>
              <th scope="col" className="num">
                Student roles
              </th>
              <th scope="col" className="num">
                UAE roles
              </th>
              <th scope="col">Read from</th>
              <th scope="col">Last check</th>
            </tr>
          </thead>
          <tbody>
            {boards.map((b) => (
              <tr key={b.name} data-zero={b.student === 0 || undefined}>
                <td className="name">
                  {b.student > 0 ? <Link href={`/?q=${encodeURIComponent(b.name)}`}>{b.name}</Link> : b.name}
                </td>
                <td className="num">{b.student}</td>
                <td className="num">{b.uae}</td>
                <td>{b.systems.map((x) => SYSTEM_NAME[x] ?? x).join(", ")}</td>
                <td>
                  {b.ok ? (
                    <span className="state">{ago(Date.parse(b.checkedAt), now)}</span>
                  ) : (
                    <span className="state bad">
                      Not read: {b.error}
                      {b.lastOk ? `, last read ${ago(Date.parse(b.lastOk), now)}` : ""}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {snapshot.not_covered.length ? (
        <>
          <h2 className="h2">Not covered</h2>
          <div className="prose">
            <p>These employers hire students in the UAE and are not read. Check their careers pages yourself.</p>
            <ul>
              {snapshot.not_covered.map((n) => (
                <li key={n.name}>
                  <strong>{n.name}.</strong> {n.reason}
                </li>
              ))}
            </ul>
            <p>
              Job sites such as LinkedIn, Indeed, Bayt and GulfTalent are not read either: their terms do not allow it, and a role there is a copy of the
              employer&rsquo;s own posting.
            </p>
          </div>
        </>
      ) : null}
    </div>
  );
}
