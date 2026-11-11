import { readFile } from "node:fs/promises";
import path from "node:path";

import type { Metadata } from "next";
import Link from "next/link";

import { SYSTEM_NAME } from "@/lib/labels";
import { loadSnapshot } from "@/lib/snapshot";
import { summary, tally } from "@/lib/stats";

// Read at request time: the numbers on this page change with every hourly check.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "How Intern Radar works",
  description: "Where the roles come from, how a posting is read, how accurate the reading is, and what the site does not cover.",
  alternates: { canonical: "/method" },
};

type Score = { name: string; n: number; precision: number | null; recall: number | null; correct?: number };
type Report = { labelled: number; with_facts: number; date: string; scores: Score[]; first_pass: Score[] };

async function report(): Promise<Report | null> {
  try {
    return JSON.parse(await readFile(path.join(process.cwd(), "public", "eval.json"), "utf8")) as Report;
  } catch {
    return null;
  }
}

const show = (v: number | null) => (v === null ? "n/a" : `${Math.round(v * 100)}%`);

export default async function Method() {
  const { snapshot, now } = await loadSnapshot();
  const s = summary(snapshot, now);
  const systems = tally(snapshot.boards.map((b) => SYSTEM_NAME[b.system] ?? b.system));
  const scores = await report();

  return (
    <div className="wrap page">
      <h1>How a posting becomes a line on this site.</h1>
      <p className="sub">
        No person types these roles in and no language model writes them. A program reads {s.employers} employers&rsquo; job boards once an hour, keeps the
        student roles in the UAE, and reads a few facts out of each one with rules you can check.
      </p>

      <h2 className="h2">Where the roles come from</h2>
      <div className="prose">
        <p>
          Employers publish their openings through a career system, and most of those systems offer a public feed meant for exactly this. Intern Radar reads{" "}
          {systems.map((x, i) => `${x.n} on ${x.name}${i < systems.length - 2 ? ", " : i === systems.length - 2 ? " and " : ""}`).join("")}. The full list is on
          the <Link href="/employers">Employers</Link> page.
        </p>
        <p>
          It reads politely: one request a second to any one system, once an hour, and it identifies itself. It does not read LinkedIn, Indeed, Bayt, GulfTalent
          or Naukrigulf, whose terms forbid it, and it skips any career system whose own rules ask automated readers to stay away.
        </p>
      </div>

      <h2 className="h2">How a posting is read</h2>
      <div className="prose">
        <ol style={{ listStyle: "decimal", paddingLeft: 20 }}>
          <li>
            <strong>Place.</strong> A posting counts if its location names the UAE or one of its cities. &ldquo;Remote, EMEA&rdquo; does not.
          </li>
          <li style={{ marginTop: 8 }}>
            <strong>Kind.</strong> An internship says so in its title (intern, trainee, working student, placement). A graduate programme says so too (graduate
            programme, new grad, launch programme). A first job is an ordinary role whose text says it is open to someone with little or no experience: it asks for a year or less in a junior role, says no experience is needed, or says it is for recent graduates. Everything else is left
            out. Roles for people who run student programmes, such as an early-careers recruiter, are left out as well.
          </li>
          <li style={{ marginTop: 8 }}>
            <strong>Facts.</strong> Seven are looked for: who can apply, start, length, pay, stage of study, where you work and the closing date. Each is a
            pattern matched against one sentence, and the sentence is kept with the deciding words marked.
          </li>
          <li style={{ marginTop: 8 }}>
            <strong>Nothing is guessed.</strong> If a posting does not state a fact, the site says &ldquo;not stated&rdquo;. A missing nationality rule is not
            shown as &ldquo;open to all&rdquo;.
          </li>
        </ol>
      </div>

      <h2 className="h2">How accurate the reading is</h2>
      <div className="prose">
        {scores ? (
          <>
            <p>
              On {scores.date} every one of the {scores.labelled} UAE postings on the watched boards was checked: is it a student role, and which kind. The{" "}
              {scores.with_facts} that the rules listed were then read in full and each fact written out. Precision is how often a stated reading was right;
              recall is how often something the posting says was read.
            </p>
            <p>
              <strong>Read the two columns differently.</strong> &ldquo;First meeting&rdquo; is how the rules did the first time they met these postings. The misses
              were then fixed, so &ldquo;after fixes&rdquo; is scored on the same postings the fixes were made for: it shows the fixes work, not how the rules will do
              on postings they have never seen. The first column is the honest guide to that.
            </p>
            <p>
              The answers were written by Claude, the AI assistant that built this site, by reading each posting. No person has checked them yet. Facts were
              labelled only on roles the rules had already listed, so a fact in a role the rules missed altogether is not counted.
            </p>
          </>
        ) : (
          <p>The rules are being scored against a hand-labelled set of real postings. The table will appear here when that is done.</p>
        )}
      </div>
      {scores ? (
        <div className="table-wrap" tabIndex={0} role="region" aria-label="Accuracy of the reading">
          <table className="t" style={{ maxWidth: 860 }}>
            <thead>
              <tr>
                <th scope="col">What is read</th>
                <th scope="col" className="num">
                  Postings where it applies
                </th>
                <th scope="col" className="num">
                  First meeting: precision
                </th>
                <th scope="col" className="num">
                  recall
                </th>
                <th scope="col" className="num">
                  After fixes: precision
                </th>
                <th scope="col" className="num">
                  recall
                </th>
              </tr>
            </thead>
            <tbody>
              {scores.scores.map((row) => {
                const first = scores.first_pass.find((f) => f.name === row.name);
                return (
                  <tr key={row.name}>
                    <td className="name">{row.name}</td>
                    <td className="num">{row.n}</td>
                    <td className="num">{show(first?.precision ?? null)}</td>
                    <td className="num">{show(first?.recall ?? null)}</td>
                    <td className="num">{show(row.precision)}</td>
                    <td className="num">{show(row.recall)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      <h2 className="h2">How it stays current</h2>
      <div className="prose">
        <p>
          A scheduled job runs the reader every hour and publishes the result. The site picks up a new result within five minutes, and an open page offers the
          newer list instead of swapping it under you. The first time a role is seen is remembered, so &ldquo;posted 2 hours ago&rdquo; keeps meaning the same thing
          tomorrow. A role that leaves an employer&rsquo;s board is marked closed and kept for 45 days.
        </p>
        <p>
          If an employer&rsquo;s board cannot be read, its roles stay as they were and the Employers page says so. A board that suddenly lists nothing is doubted
          for three checks before its roles are closed, because that is more often a fault than a mass closing.
        </p>
      </div>

      <h2 className="h2">What it does not do</h2>
      <div className="prose">
        <ul>
          <li>It does not cover every employer. Many large UAE employers use systems with no public feed.</li>
          <li>It does not know what a posting leaves out. Most do not state pay or who may apply.</li>
          <li>It does not apply for you, store your CV, or use an account. Saved roles and your last visit stay in your own browser.</li>
          <li>It is not the employer. The posting on the employer&rsquo;s site is the source; always read it before applying.</li>
        </ul>
      </div>
    </div>
  );
}
