// One picture of the CV match in use: node scripts/shot-fit.mjs <outDir> [baseUrl]
import { mkdirSync } from "node:fs";
import path from "node:path";

import { chromium } from "@playwright/test";

const out = process.argv[2] ?? "shots";
const base = process.argv[3] ?? "http://127.0.0.1:3150";
mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
for (const [name, width, height] of [
  ["fit-desktop", 1440, 1300],
  ["fit-phone", 390, 1500],
]) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 2, reducedMotion: "reduce" });
  const page = await ctx.newPage();
  await page.goto(base, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Match my CV" }).click();
  await page.getByLabel("Paste the text of your CV").fill("LLM agents and RAG pipelines in Python; SQL and DuckDB; Next.js and TypeScript; machine learning with PyTorch; Excel; data analysis.");
  await page.getByRole("button", { name: "Match roles" }).click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(out, `${name}.png`) });
  await ctx.close();
}
await browser.close();
