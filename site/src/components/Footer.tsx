import Link from "next/link";

import { REPO_URL } from "@/lib/site";

export function Footer() {
  return (
    <footer className="foot">
      <div className="wrap foot-in">
        <p>
          Read from employers&rsquo; own career systems. Always check the posting itself before you apply: the employer&rsquo;s
          page is the source, this is a reading of it.
        </p>
        <Link href="/method">How it works</Link>
        <a href="/feed.xml">Feed</a>
        {REPO_URL ? <a href={REPO_URL}>Source</a> : null}
      </div>
    </footer>
  );
}
