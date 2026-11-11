import { defineConfig, devices } from "@playwright/test";

// End-to-end tests drive the real pages in a real browser. Locally and in CI they run against a server on port
// 3151 that reads a pinned snapshot, so they do not depend on what employers posted today. Against the published
// site:  BASE_URL=https://... npx playwright test
const remote = process.env.BASE_URL;
const local = "http://127.0.0.1:3151";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  workers: process.env.CI ? 2 : 4,
  expect: { timeout: 10_000 },
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: { baseURL: remote ?? local, trace: "retain-on-failure", reducedMotion: "reduce" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } }, testIgnore: /phone\.spec\.ts/ },
    { name: "phone", use: { ...devices["Pixel 7"] }, testMatch: /phone\.spec\.ts/ },
  ],
  webServer: remote
    ? undefined
    : {
        command: process.env.CI ? "npx next start -p 3151 -H 127.0.0.1" : "npx next dev -p 3151 -H 127.0.0.1",
        url: local,
        reuseExistingServer: !process.env.CI,
        timeout: 180_000,
        env: { RADAR_SNAPSHOT_FILE: "snapshot.json", NEXT_PUBLIC_SITE_URL: local },
      },
});
