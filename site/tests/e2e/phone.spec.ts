import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

const snapshot = JSON.parse(readFileSync(path.join(__dirname, "..", "fixtures", "snapshot.json"), "utf8")) as { roles: { slug: string; status: string; kind: string }[] };
const open = snapshot.roles.filter((r) => r.status === "open");

test("no page scrolls sideways on a phone", async ({ page }) => {
  for (const url of ["/", "/employers", "/market", "/method", `/role/${open[0].slug}`, "/nope"]) {
    await page.goto(url);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, url).toBeLessThanOrEqual(0);
  }
});

test("the first role is on the first screen", async ({ page }) => {
  await page.goto("/");
  const box = await page.locator(".row-head").first().boundingBox();
  expect(box!.y).toBeLessThan(page.viewportSize()!.height);
});

test("filters sit behind one control and still work", async ({ page }) => {
  await page.goto("/");
  const kind = page.getByRole("button", { name: /^Internships/ });
  await expect(kind).toBeHidden();
  await page.getByRole("button", { name: /^Filter/ }).click();
  await kind.click();
  await expect(page.locator(".row")).toHaveCount(open.filter((r) => r.kind === "internship").length);
  await expect(page.getByRole("button", { name: "Filter (1)" })).toBeVisible();
});

test("tap targets are big enough to hit", async ({ page }) => {
  await page.goto("/");
  await page.locator(".row-head").first().click();
  const small = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>("a, button, input, summary")]
      .filter((el) => el.offsetParent !== null && !el.closest(".foot") && !el.closest(".prose"))
      .map((el) => ({ el, r: el.getBoundingClientRect() }))
      .filter(({ r }) => r.width > 0 && (r.height < 32 || r.width < 32))
      .map(({ el, r }) => `${el.tagName} "${(el.textContent ?? "").trim().slice(0, 30)}" ${Math.round(r.width)}x${Math.round(r.height)}`),
  );
  expect(small).toEqual([]);
});
