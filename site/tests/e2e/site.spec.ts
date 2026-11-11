import { readFileSync } from "node:fs";
import path from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

type Role = { id: string; slug: string; title: string; employer: string; kind: string; status: string; url: string; facts: Record<string, { value: string; mark?: string | null }> };
const snapshot = JSON.parse(readFileSync(path.join(__dirname, "..", "fixtures", "snapshot.json"), "utf8")) as { roles: Role[]; boards: { name: string }[] };
const open = snapshot.roles.filter((r) => r.status === "open");
const withMark = open.find((r) => Object.values(r.facts).some((f) => f.mark));
const nationalsOnly = open.filter((r) => r.facts.eligibility?.value === "nationals_only");

function watch(page: Page): string[] {
  const problems: string[] = [];
  page.on("console", (m) => m.type() === "error" && problems.push(m.text()));
  page.on("pageerror", (e) => problems.push(e.message));
  return problems;
}

async function axe(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.length} (${v.nodes[0]?.target})`)).toEqual([]);
}

test.describe("the list", () => {
  test("shows every open role, newest group first, with no errors", async ({ page }) => {
    const problems = watch(page);
    await page.goto("/");
    await expect(page).toHaveTitle(/Intern Radar/);
    await expect(page.locator("h1")).toContainText(`${open.length} student roles open`);
    await expect(page.locator(".row")).toHaveCount(open.length);
    await expect(page.locator(".count")).toContainText(`${open.length} open roles`);
    const groups = await page.locator(".group-h").allTextContents();
    const order = ["Today", "Yesterday", "This week", "Earlier this month", "Older"];
    const seen = groups.map((g) => order.findIndex((o) => g.startsWith(o)));
    expect(seen).toEqual([...seen].sort((a, b) => a - b));
    expect(problems).toEqual([]);
  });

  test("a row opens to its facts, each beside its sentence, and closes with Escape", async ({ page }) => {
    test.skip(!withMark, "no role with a marked fact in the fixture");
    await page.goto("/");
    const row = page.locator(`.row[data-id="${withMark!.id}"]`);
    const head = row.locator(".row-head");
    await expect(head).toHaveAttribute("aria-expanded", "false");
    await head.click();
    await expect(head).toHaveAttribute("aria-expanded", "true");
    await expect(row.locator(".ledger")).toBeVisible();
    await expect(row.locator(".quote mark").first()).toBeVisible();
    const apply = row.getByRole("link", { name: /Open the posting at/ });
    await expect(apply).toHaveAttribute("href", withMark!.url);
    await expect(apply).toHaveAttribute("rel", /noopener/);
    await expect(apply).toHaveAttribute("target", "_blank");
    await page.keyboard.press("Escape");
    await expect(head).toHaveAttribute("aria-expanded", "false");
  });

  test("only one row is open at a time", async ({ page }) => {
    await page.goto("/");
    const heads = page.locator(".row-head");
    await heads.nth(0).click();
    await heads.nth(1).click();
    await expect(page.locator('.row-head[aria-expanded="true"]')).toHaveCount(1);
  });

  test("the kind filter narrows the list, lives in the address, and survives a reload", async ({ page }) => {
    const internships = open.filter((r) => r.kind === "internship").length;
    await page.goto("/");
    await page.getByRole("button", { name: /^Internships/ }).click();
    await expect(page.locator(".row")).toHaveCount(internships);
    await expect(page).toHaveURL(/kind=internship/);
    await page.reload();
    await expect(page.locator(".row")).toHaveCount(internships);
    await expect(page.getByRole("button", { name: /^Internships/ })).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("button", { name: "Clear" }).click();
    await expect(page.locator(".row")).toHaveCount(open.length);
    await expect(page).not.toHaveURL(/kind=/);
  });

  test("'Hide nationals-only' removes exactly the roles that say so", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Hide nationals-only" }).click();
    await expect(page.locator(".row")).toHaveCount(open.length - nationalsOnly.length);
    for (const r of nationalsOnly.slice(0, 3)) await expect(page.locator(`.row[data-id="${r.id}"]`)).toHaveCount(0);
  });

  test("field and place menus filter and show counts", async ({ page }) => {
    await page.goto("/");
    await page.locator("details.pick summary", { hasText: "Place" }).click();
    const option = page.locator(".menu .opt", { hasText: "Abu Dhabi" });
    const n = Number(await option.locator(".n").textContent());
    await option.locator("input").check();
    await expect(page.locator(".row")).toHaveCount(n);
    await expect(page).toHaveURL(/place=Abu(\+|%20)Dhabi/);
  });

  test("search finds by employer, and an empty result explains itself", async ({ page }) => {
    await page.goto("/");
    const employer = open[0].employer;
    await page.getByRole("searchbox").fill(employer);
    const expected = open.filter((r) => `${r.title} ${r.employer}`.toLowerCase().includes(employer.toLowerCase())).length;
    await expect(page.locator(".row")).toHaveCount(expected);
    await page.getByRole("searchbox").fill("zzzzqqq");
    await expect(page.locator(".row")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Nothing matches those filters." })).toBeVisible();
    await page.getByRole("button", { name: "Clear all filters" }).click();
    await expect(page.locator(".row")).toHaveCount(open.length);
  });

  test("a shared address opens already filtered", async ({ page }) => {
    await page.goto("/?kind=graduate&q=zzzzqqq");
    await expect(page.getByRole("searchbox")).toHaveValue("zzzzqqq");
    await expect(page.locator(".row")).toHaveCount(0);
  });

  test("saving a role is remembered in this browser", async ({ page }) => {
    await page.goto("/");
    await page.locator(".row-head").first().click();
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(page.getByRole("button", { name: /^Saved \(1\)/ })).toBeVisible();
    await page.reload();
    await page.getByRole("button", { name: /^Saved \(1\)/ }).click();
    await expect(page.locator(".row")).toHaveCount(1);
  });

  test("keyboard: slash searches, j moves, Enter opens", async ({ page }) => {
    await page.goto("/");
    await page.locator("body").click({ position: { x: 5, y: 5 } });
    await page.keyboard.press("/");
    await expect(page.getByRole("searchbox")).toBeFocused();
    await page.keyboard.press("Escape");
    await page.keyboard.press("j");
    const first = page.locator(".row-head").first();
    await expect(first).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(first).toHaveAttribute("aria-expanded", "true");
  });

  test("a newer check is offered, not forced", async ({ page }) => {
    await page.route("**/api/meta", (route) => route.fulfill({ json: { generated_at: "2099-01-01T00:00:00+00:00", open: open.length + 2 } }));
    await page.goto("/");
    const notice = page.getByRole("status").filter({ hasText: "A newer check landed" });
    // The page listens once it has hydrated; nudge it until it has.
    await expect(async () => {
      await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
      await expect(notice).toContainText("2 more than shown", { timeout: 1000 });
    }).toPass({ timeout: 15_000 });
    await expect(page.locator(".row")).toHaveCount(open.length);
    await notice.getByRole("button", { name: "Show the latest" }).click();
    await expect(notice).toHaveCount(0);
  });

  test("the theme choice is kept", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await page.getByRole("button", { name: "Switch to dark theme" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });
});

test.describe("the other pages", () => {
  test("a role page states every fact or says it is not stated", async ({ page }) => {
    const problems = watch(page);
    const r = withMark ?? open[0];
    await page.goto(`/role/${r.slug}`);
    await expect(page.locator("h1")).toHaveText(r.title);
    await expect(page.locator(".ledger > div")).toHaveCount(7);
    const stated = Object.keys(r.facts).length;
    await expect(page.locator(".ledger .none")).toHaveCount(7 - stated);
    await expect(page.getByRole("link", { name: /Open the posting at/ })).toHaveAttribute("href", r.url);
    await expect(page.locator(".timeline li").first()).toBeVisible();
    await expect(page).toHaveTitle(new RegExp(r.employer.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    expect(problems).toEqual([]);
  });

  test("an unknown role is a real 404 with a way back", async ({ page }) => {
    const res = await page.goto("/role/not-a-role");
    expect(res!.status()).toBe(404);
    await expect(page.getByRole("link", { name: "See open roles" })).toBeVisible();
  });

  test("employers lists every board and links to its roles", async ({ page }) => {
    await page.goto("/employers");
    await expect(page.locator("table.t tbody tr")).toHaveCount(new Set(snapshot.boards.map((b) => b.name)).size);
    await expect(page.getByRole("heading", { name: "Not covered" })).toBeVisible();
    const link = page.locator("table.t tbody tr td.name a").first();
    const name = (await link.textContent())!;
    await link.click();
    await expect(page.getByRole("searchbox")).toHaveValue(name);
  });

  test("market and method render their figures", async ({ page }) => {
    await page.goto("/market");
    await expect(page.locator(".big b").first()).toHaveText(String(open.length));
    await expect(page.locator(".bars").first()).toBeVisible();
    await page.goto("/method");
    await expect(page.getByRole("heading", { name: "How a posting is read" })).toBeVisible();
  });

  for (const [name, url, theme] of [
    ["home", "/", "light"],
    ["home dark", "/", "dark"],
    ["role", `/role/${(withMark ?? open[0]).slug}`, "light"],
    ["employers", "/employers", "light"],
    ["market", "/market", "light"],
    ["market dark", "/market", "dark"],
    ["method", "/method", "dark"],
  ] as const) {
    test(`accessibility: ${name}`, async ({ page }) => {
      await page.addInitScript((t) => localStorage.setItem("ir-theme", t), theme);
      await page.goto(url);
      if (url === "/") await page.locator(".row-head").first().click();
      await axe(page);
    });
  }
});

test.describe("feeds and headers", () => {
  test("the Atom feed is well formed and lists open roles", async ({ request }) => {
    const res = await request.get("/feed.xml");
    expect(res.headers()["content-type"]).toContain("application/atom+xml");
    const xml = await res.text();
    expect(xml.startsWith("<?xml")).toBe(true);
    expect((xml.match(/<entry>/g) ?? []).length).toBe(Math.min(60, open.length));
    expect(xml).not.toMatch(/<script/i);
  });

  test("the JSON feed and the meta endpoint agree with the list", async ({ request }) => {
    const feed = await (await request.get("/feed.json")).json();
    expect(feed.items.length).toBe(Math.min(60, open.length));
    expect(feed.items.every((i: { external_url: string }) => i.external_url.startsWith("https://"))).toBe(true);
    const meta = await (await request.get("/api/meta")).json();
    expect(meta.open).toBe(open.length);
  });

  test("every page is sent with its security headers", async ({ request }) => {
    for (const url of ["/", "/employers", "/feed.xml"]) {
      const h = (await request.get(url)).headers();
      expect(h["content-security-policy"]).toContain("default-src 'self'");
      expect(h["content-security-policy"]).toContain("object-src 'none'");
      expect(h["x-content-type-options"]).toBe("nosniff");
      expect(h["x-powered-by"]).toBeUndefined();
    }
  });
});

test.describe("matching a CV", () => {
  const withSkills = open.filter((r) => (r as unknown as { skills: string[] }).skills.includes("Python"));

  test("a pasted CV ranks the roles that name its skills first, and never leaves the browser", async ({ page }) => {
    test.skip(!withSkills.length, "no role names Python in the fixture");
    const sent: string[] = [];
    page.on("request", (req) => {
      const body = req.postData() ?? "";
      if (req.url().includes("zebra-cv-marker") || body.includes("zebra-cv-marker")) sent.push(req.url());
    });
    await page.goto("/");
    await page.getByRole("button", { name: "Match my CV" }).click();
    await page.getByLabel("Paste the text of your CV").fill("zebra-cv-marker. Projects in Python and SQL.");
    await page.getByRole("button", { name: "Match roles" }).click();
    await expect(page.locator("#fit-panel [role=status]")).toContainText("Python");
    await expect(page.locator(".group-h").first()).toContainText("Name a skill from your CV");
    await expect(page.locator(".row").first().locator(".fit")).toContainText("from your CV");
    await expect(page.locator(".row .fit", { hasText: "Python" })).toHaveCount(withSkills.length);
    await expect(page.locator(".row")).toHaveCount(open.length);

    // Sorting back by date keeps the match visible on each row.
    await page.getByRole("button", { name: "Sorted by match" }).click();
    await expect(page.locator(".group-h").first()).not.toContainText("your CV");

    // The skills found survive a reload in this tab; the CV text itself is kept nowhere.
    await page.reload();
    await expect(page.getByRole("button", { name: /^Your CV: \d+ skills?/ })).toBeVisible();
    const stored = await page.evaluate(() => JSON.stringify({ ...localStorage }) + JSON.stringify({ ...sessionStorage }));
    expect(stored).not.toContain("zebra-cv-marker");
    expect(sent).toEqual([]);

    await page.getByRole("button", { name: /^Your CV/ }).click();
    await page.getByLabel("Paste the text of your CV").fill("x");
    await page.getByRole("button", { name: "Forget my CV" }).click();
    await expect(page.locator(".row .fit")).toHaveCount(0);
  });
});
