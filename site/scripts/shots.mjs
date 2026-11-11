// Take pictures of the running site for review: node scripts/shots.mjs <outDir> [baseUrl]
import { mkdirSync } from "node:fs";
import path from "node:path";

import { chromium } from "@playwright/test";

const out = process.argv[2] ?? "shots";
const base = process.argv[3] ?? "http://127.0.0.1:3150";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
const errors = [];

async function shot(name, url, { width, height, theme = "light", full = false, act }) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 2, reducedMotion: "reduce" });
  const page = await ctx.newPage();
  page.on("console", (m) => m.type() === "error" && errors.push(`${name}: ${m.text()}`));
  page.on("pageerror", (e) => errors.push(`${name}: ${e.message}`));
  await page.addInitScript((t) => localStorage.setItem("ir-theme", t), theme);
  await page.goto(base + url, { waitUntil: "networkidle" });
  if (act) await act(page);
  await page.screenshot({ path: path.join(out, `${name}.png`), fullPage: full });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (overflow > 0) errors.push(`${name}: page scrolls sideways by ${overflow}px`);
  await ctx.close();
}

const openFirst = async (page) => {
  await page.locator(".row-head").first().click();
  await page.waitForTimeout(200);
};

await shot("home-desktop", "/", { width: 1440, height: 900 });
await shot("home-desktop-open", "/", { width: 1440, height: 1100, act: openFirst });
await shot("home-desktop-dark", "/", { width: 1440, height: 900, theme: "dark", act: openFirst });
await shot("home-phone", "/", { width: 390, height: 844 });
await shot("home-phone-open", "/", { width: 390, height: 844, act: openFirst, full: true });
await shot("home-phone-dark", "/", { width: 390, height: 844, theme: "dark" });
await shot("home-tablet", "/", { width: 820, height: 1100 });
await shot("home-filter-menu", "/", {
  width: 1440,
  height: 900,
  act: async (page) => {
    await page.locator("details.pick summary").first().click();
    await page.waitForTimeout(150);
  },
});
await shot("home-empty", "/?q=zzzzqq", { width: 1440, height: 900 });
const slug = await (async () => {
  const res = await fetch(base + "/feed.json");
  const feed = await res.json();
  return new URL(feed.items[0].url).pathname;
})();
await shot("role-desktop", slug, { width: 1440, height: 900, full: true });
await shot("role-phone", slug, { width: 390, height: 844, full: true });
await shot("employers-desktop", "/employers", { width: 1440, height: 900 });
await shot("employers-phone", "/employers", { width: 390, height: 844 });
await shot("market-desktop", "/market", { width: 1440, height: 900, full: true });
await shot("market-phone", "/market", { width: 390, height: 844, full: true });
await shot("market-dark", "/market", { width: 1440, height: 900, theme: "dark", full: true });
await shot("method-desktop", "/method", { width: 1440, height: 900, full: true });
await shot("notfound", "/nope", { width: 1440, height: 900 });

await browser.close();
console.log(errors.length ? errors.join("\n") : "no console errors, no sideways scroll");
