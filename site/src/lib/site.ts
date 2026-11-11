// Addresses that differ between a laptop and the published site. Nothing secret lives here.

export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ?? (process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : "http://127.0.0.1:3150")
).replace(/\/$/, "");

// Set once the repository exists. Until then the links that need it are simply not shown.
export const REPO_URL = (process.env.NEXT_PUBLIC_REPO_URL ?? "").replace(/\/$/, "");
