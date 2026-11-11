import { FACT_NAME, FACT_ORDER } from "@/lib/labels";
import type { Fact, Role } from "@/lib/schema";

const SOURCE: Record<Fact["source"], string> = {
  text: "from the posting",
  title: "from the title",
  feed: "from the employer's filing",
};

/** The sentence a fact was read from, with the deciding words marked. Posting text is only ever rendered as text. */
export function Quote({ fact }: { fact: Fact }) {
  const { evidence, mark } = fact;
  const at = mark ? evidence.indexOf(mark) : -1;
  if (!mark || at < 0) return <p className="quote">{evidence}</p>;
  return (
    <p className="quote">
      {evidence.slice(0, at)}
      <mark>{mark}</mark>
      {evidence.slice(at + mark.length)}
    </p>
  );
}

/** Every fact beside its sentence. With `all`, facts the posting does not state are listed as "not stated". */
export function Ledger({ role, all = false }: { role: Role; all?: boolean }) {
  const keys = FACT_ORDER.filter((k) => all || role.facts[k]);
  if (!keys.length) {
    return <p className="why">The posting states none of the facts this site reads: who can apply, start, length, pay or stage of study.</p>;
  }
  return (
    <dl className="ledger">
      {keys.map((key) => {
        const fact = role.facts[key];
        return (
          <div key={key}>
            <dt>{FACT_NAME[key]}</dt>
            <dd>
              {fact ? (
                <>
                  <span className="value">{fact.label}</span>
                  {fact.source !== "text" ? <span className="from">{SOURCE[fact.source]}</span> : null}
                  {fact.source === "feed" ? null : <Quote fact={fact} />}
                </>
              ) : (
                <span className="value none">Not stated in the posting</span>
              )}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
