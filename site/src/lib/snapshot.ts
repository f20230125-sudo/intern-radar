import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";

import { SnapshotSchema, type Snapshot } from "./schema";
import { SNAPSHOT_URL } from "./site";

// Where the snapshot comes from, in order:
//   1. The published copy on the repository's data branch (SNAPSHOT_URL in site.ts). A bot commit there reaches
//      the site within five minutes without a new deployment.
//   2. ../data/snapshot.json: a local run of the collector, for development.
//   3. The copy bundled with the build, so the site always has something true to show.
const REVALIDATE_SECONDS = 300;

// `now` is read once here, with the data, so every number on a page is counted against the same moment.
export type Loaded = { snapshot: Snapshot; source: "live" | "local" | "bundled"; now: number; problem?: string };

async function fromFile(file: string): Promise<Snapshot> {
  return SnapshotSchema.parse(JSON.parse(await readFile(file, "utf8")));
}

export async function loadSnapshot(): Promise<Loaded> {
  const url = SNAPSHOT_URL;
  let problem: string | undefined;
  // Tests pin the snapshot to a file so they do not depend on what employers posted today.
  const pinned = process.env.RADAR_SNAPSHOT_FILE;
  const now = Date.now();
  if (pinned) return { snapshot: await fromFile(path.join(process.cwd(), "tests", "fixtures", path.basename(pinned))), source: "local", now };
  if (url) {
    try {
      const res = await fetch(url, { next: { revalidate: REVALIDATE_SECONDS } });
      if (!res.ok) throw new Error(`the data branch answered ${res.status}`);
      return { snapshot: SnapshotSchema.parse(await res.json()), source: "live", now };
    } catch (err) {
      problem = err instanceof Error ? err.message.slice(0, 200) : "the live snapshot could not be read";
    }
  }
  try {
    return { snapshot: await fromFile(path.join(process.cwd(), "..", "data", "snapshot.json")), source: "local", now, problem };
  } catch {
    // fall through to the bundled copy
  }
  return { snapshot: await fromFile(path.join(process.cwd(), "public", "snapshot.sample.json")), source: "bundled", now, problem };
}
