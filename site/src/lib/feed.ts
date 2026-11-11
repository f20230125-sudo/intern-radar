import { KIND_LABEL, placeLine } from "./labels";
import type { Role, Snapshot } from "./schema";
import { postedMs } from "./time";

// Feeds for people who would rather be told than come and look. Built from the same snapshot as the pages.

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, "");

export function newest(snapshot: Snapshot, limit = 60): Role[] {
  return snapshot.roles
    .filter((r) => r.status === "open")
    .sort((a, b) => Date.parse(b.first_seen) - Date.parse(a.first_seen) || postedMs(b) - postedMs(a))
    .slice(0, limit);
}

export function summaryLine(role: Role): string {
  const facts = Object.values(role.facts)
    .map((f) => f?.label)
    .filter(Boolean);
  return [KIND_LABEL[role.kind], placeLine(role), ...facts].join(" · ");
}

export function atom(snapshot: Snapshot, site: string): string {
  const entries = newest(snapshot)
    .map(
      (r) => `  <entry>
    <id>${esc(`${site}/role/${r.slug}`)}</id>
    <title>${esc(`${r.title} at ${r.employer}`)}</title>
    <link href="${esc(`${site}/role/${r.slug}`)}"/>
    <link rel="related" href="${esc(r.url)}"/>
    <updated>${esc(new Date(Date.parse(r.changed_at ?? r.first_seen)).toISOString())}</updated>
    <published>${esc(new Date(Date.parse(r.first_seen)).toISOString())}</published>
    <author><name>${esc(r.employer)}</name></author>
    <summary>${esc(summaryLine(r))}</summary>
  </entry>`,
    )
    .join("\n");
  return `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>${esc(site)}/</id>
  <title>Intern Radar: student roles at UAE employers</title>
  <subtitle>Internships, graduate programmes and first jobs, newest first.</subtitle>
  <link href="${esc(site)}/"/>
  <link rel="self" href="${esc(site)}/feed.xml"/>
  <updated>${esc(new Date(Date.parse(snapshot.generated_at)).toISOString())}</updated>
${entries}
</feed>
`;
}

export function jsonFeed(snapshot: Snapshot, site: string) {
  return {
    version: "https://jsonfeed.org/version/1.1",
    title: "Intern Radar: student roles at UAE employers",
    home_page_url: `${site}/`,
    feed_url: `${site}/feed.json`,
    items: newest(snapshot).map((r) => ({
      id: `${site}/role/${r.slug}`,
      url: `${site}/role/${r.slug}`,
      external_url: r.url,
      title: `${r.title} at ${r.employer}`,
      content_text: summaryLine(r),
      date_published: new Date(Date.parse(r.first_seen)).toISOString(),
      authors: [{ name: r.employer }],
      tags: [KIND_LABEL[r.kind], ...r.fields],
    })),
  };
}
