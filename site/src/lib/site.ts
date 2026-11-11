// Addresses that differ between a laptop and the published site. Nothing secret lives here.
//
// On Vercel, a project connected to its GitHub repository is given VERCEL_GIT_REPO_OWNER and VERCEL_GIT_REPO_SLUG
// and its own production address, so the published site needs no settings typed in by hand. Each value below can
// still be overridden with an environment variable.

const owner = process.env.VERCEL_GIT_REPO_OWNER;
const slug = process.env.VERCEL_GIT_REPO_SLUG;
const fromGit = owner && slug ? `https://github.com/${owner}/${slug}` : "";

export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ?? (process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : "http://127.0.0.1:3150")
).replace(/\/$/, "");

// Links that need the repository are not shown until one is known.
export const REPO_URL = (process.env.NEXT_PUBLIC_REPO_URL ?? fromGit).replace(/\/$/, "");

// The hourly job publishes the snapshot on the repository's `data` branch.
export const SNAPSHOT_URL = process.env.SNAPSHOT_URL ?? (owner && slug ? `https://raw.githubusercontent.com/${owner}/${slug}/data/snapshot.json` : "");
