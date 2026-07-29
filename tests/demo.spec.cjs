const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const payload = JSON.parse(fs.readFileSync(path.join(root, "demo/data/changes.json"), "utf8"));
const corePages = [
  "/", "/demo/professor_presentation.html", "/demo/ranked_change_feed.html",
  "/demo/case_studies.html", "/demo/case_study_walkthrough.html",
  "/demo/company_comparison.html", "/demo/company_timeline.html",
  "/demo/research_results.html", "/demo/methodology.html",
  "/demo/innovation_framework.html", "/demo/pilot_plan.html",
  "/demo/professor_materials.html", "/demo/private_workspace.html"
];
const packets = ["01_TFC", "02_KHC", "03_DLTR", "04_DVN", "05_RH", "06_FCX", "07_EFX", "08_CHE"]
  .map((name) => `/demo/evidence_packets/${name}.html`);

test("all frozen metrics and evidence fields reconcile", async () => {
  expect(payload.records).toHaveLength(995);
  const novelty = { previous: 0, new: 0, partial: 0, unclear: 0 };
  let high = 0;
  for (const record of payload.records) {
    for (const field of ["id", "date", "ticker", "issuer", "title", "summary", "why", "category", "materiality", "url"]) expect(record[field], `${record.id}:${field}`).toBeTruthy();
    expect(record.url).toMatch(/^https:\/\/www\.sec\.gov\//);
    expect(record.confidence).toBeGreaterThan(0);
    if (record.confidence >= .8) high += 1;
    const title = record.title.toLowerCase();
    if (title.includes("previously disclosed") || title.includes("previously covered in news")) novelty.previous += 1;
    else if (title.includes("genuinely new")) novelty.new += 1;
    else if (title.includes("partially anticipated")) novelty.partial += 1;
    else novelty.unclear += 1;
  }
  expect(high).toBe(629);
  expect(novelty).toEqual({ previous: 394, new: 342, partial: 243, unclear: 16 });
  expect(Object.values(novelty).reduce((a, b) => a + b, 0)).toBe(995);
});

test("public pages have metadata, semantic headings, and zero console errors", async ({ page }) => {
  const errors = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));
  for (const route of [...corePages, ...packets]) {
    await page.goto(route);
    await expect(page).toHaveTitle(/\S+/);
    await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /\S+/);
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.locator(".skip-link")).toHaveCount(1);
  }
  expect(errors).toEqual([]);
});

test("all static internal links and public downloads resolve", async ({ request }) => {
  const htmlFiles = [];
  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const target = path.join(directory, entry.name);
      if (entry.isDirectory() && !["node_modules", "test-results", "playwright-report", ".git", ".tmp"].includes(entry.name)) walk(target);
      else if (entry.name.endsWith(".html")) htmlFiles.push(target);
    }
  }
  walk(root);
  for (const filePath of htmlFiles) {
    const relative = path.relative(root, filePath).replaceAll("\\", "/");
    const html = fs.readFileSync(filePath, "utf8");
    const hrefs = [...html.matchAll(/href="([^"]+)"/g)].map((match) => match[1])
      .filter((href) => !href.startsWith("#") && !href.startsWith("http") && !href.startsWith("data:") && !href.startsWith("mailto:"));
    for (const href of hrefs) {
      const url = new URL(href, `http://127.0.0.1:4173/${relative}`).pathname;
      expect((await request.get(url)).status(), `${relative} -> ${href}`).toBe(200);
    }
  }
});

test("presentation supports duration modes, notes, navigation, demo jump, and clean exit", async ({ page }) => {
  await page.goto("/demo/professor_presentation.html");
  await expect(page.locator(".story-section")).toHaveCount(12);
  await page.getByRole("button", { name: "5 min" }).click();
  await expect(page.getByRole("button", { name: "5 min" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Present" }).click();
  await expect(page.locator("body")).toHaveClass(/presentation-active/);
  await expect(page.locator("[data-presentation-position]")).toHaveText("1 / 8");
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("[data-presentation-position]")).toHaveText("2 / 8");
  await page.keyboard.press("Space");
  await page.keyboard.press("PageDown");
  await page.keyboard.press("PageUp");
  await page.keyboard.press("Home");
  await expect(page.locator("[data-presentation-position]")).toHaveText("1 / 8");
  await page.keyboard.press("n");
  await expect(page.locator("body")).toHaveClass(/notes-visible/);
  await expect(page.locator(".story-section.is-current .speaker-notes")).toBeVisible();
  await page.getByRole("button", { name: "Jump to demo" }).click();
  await expect(page.locator(".story-section.is-current")).toHaveAttribute("id", "slide-workflow");
  await page.keyboard.press("End");
  await expect(page.locator("[data-presentation-position]")).toHaveText("8 / 8");
  await page.keyboard.press("Escape");
  await expect(page.locator("body")).not.toHaveClass(/presentation-active/);
  await page.getByRole("button", { name: "10 min" }).click();
  await page.keyboard.press("f");
  await expect(page.locator("[data-presentation-position]")).toHaveText("1 / 12");
  await page.keyboard.press("Escape");
});

test("ranked feed onboarding, guided example, filters, sorting, pagination, and shortlist work", async ({ page }) => {
  await page.goto("/demo/ranked_change_feed.html");
  await expect(page.getByText("995 of 995 changes")).toBeVisible();
  await expect(page.locator("#feed-onboarding")).toBeVisible();
  await page.getByRole("button", { name: "Dismiss" }).click();
  await page.reload();
  await expect(page.locator("#feed-onboarding")).toBeHidden();
  await page.getByRole("button", { name: "Start guided example" }).click();
  await expect(page.locator("#filter-search")).toHaveValue("KHC");
  await expect(page.locator(".change-card").first()).toContainText("KHC");
  const save = page.locator(".change-card .save-record").first();
  await save.click();
  await expect(page.locator("#shortlist-count")).toHaveText("1");
  await expect(page.locator("#export-shortlist")).toBeEnabled();
  const downloadPromise = page.waitForEvent("download");
  await page.locator("#export-shortlist").click();
  expect((await downloadPromise).suggestedFilename()).toBe("pure-news-intelligence-shortlist.txt");
  await page.locator("#clear-shortlist").click();
  await expect(page.locator("#shortlist-count")).toHaveText("0");
  await page.getByRole("button", { name: "Clear all" }).click();
  await page.getByLabel("Sort").selectOption("confidence");
  await expect(page.locator(".change-card .status-chip").first()).toContainText("0.990");
  await page.getByRole("button", { name: "Table" }).click();
  await expect(page.locator(".cards-table")).toBeVisible();
  await page.getByRole("button", { name: "Cards" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.locator("#page-status")).toContainText("Page 2");
});

test("case grouping, novelty contrast, and ex-ante/ex-post boundaries are explicit", async ({ page }) => {
  await page.goto("/demo/case_studies.html");
  for (const heading of ["New risk disclosure", "Previously anticipated change", "Liquidity or credit change", "Operational or cybersecurity change", "Low-materiality or null example"]) {
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }
  await expect(page.locator(".case-card")).toHaveCount(8);
  await page.goto("/demo/case_study_walkthrough.html");
  await expect(page.getByText("Available at filing time", { exact: true })).toHaveCount(2);
  await expect(page.getByText("Observed after the filing — not used in the original classification", { exact: true })).toBeVisible();
  await page.goto("/demo/evidence_packets/02_KHC.html");
  await expect(page.locator(".five-part li")).toHaveCount(5);
  await expect(page.getByText("Observed after the filing — not used in the original classification", { exact: true })).toBeVisible();
});

test("innovation, pilot, materials, and research decision pages expose required content", async ({ page }) => {
  await page.goto("/demo/innovation_framework.html");
  for (const label of ["Target user", "Buyer", "Technical gatekeeper", "Beachhead use case"]) await expect(page.getByText(label, { exact: true })).toBeVisible();
  await page.goto("/demo/pilot_plan.html");
  await expect(page.getByText(/Proposed measurement—not actual performance/)).toBeVisible();
  for (const rule of ["Go", "Revise", "Stop"]) await expect(page.getByText(rule, { exact: true })).toBeVisible();
  await page.goto("/demo/professor_materials.html");
  await expect(page.locator("a[download]")).toHaveCount(14);
  await page.goto("/demo/research_results.html");
  await expect(page.locator(".study-panel")).toHaveCount(4);
  await expect(page.getByText("Negative and null results were preserved rather than tuned away.", { exact: true })).toBeVisible();
});

test("interactive controls have accessible names, visible focus, and no serious axe violations", async ({ page }) => {
  for (const route of ["/", "/demo/professor_presentation.html", "/demo/ranked_change_feed.html", "/demo/case_studies.html", "/demo/research_results.html", "/demo/innovation_framework.html", "/demo/pilot_plan.html", "/demo/methodology.html"]) {
    await page.goto(route);
    if (route.includes("ranked")) await page.waitForSelector(".change-card");
    const unnamed = await page.locator("button, input, select, textarea").evaluateAll((controls) => controls.filter((control) => {
      const label = control.labels?.[0]?.textContent?.trim();
      return !(label || control.getAttribute("aria-label") || control.getAttribute("aria-labelledby") || control.textContent.trim());
    }).map((control) => `${control.tagName}#${control.id}`));
    expect(unnamed, route).toEqual([]);
    const results = await new AxeBuilder({ page }).analyze();
    const severe = results.violations.filter((item) => ["serious", "critical"].includes(item.impact));
    expect(severe, `${route}: ${severe.map((v) => v.id).join(", ")}`).toEqual([]);
  }
  await page.goto("/demo/ranked_change_feed.html");
  await page.keyboard.press("Tab");
  expect(await page.locator(":focus").evaluate((node) => getComputedStyle(node).outlineStyle)).not.toBe("none");
});

for (const viewport of [{ width: 1920, height: 1080 }, { width: 1440, height: 900 }, { width: 1024, height: 768 }, { width: 390, height: 844 }]) {
  test(`all public surfaces avoid horizontal overflow at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    for (const route of [...corePages, ...packets]) {
      await page.goto(route);
      if (route.includes("ranked")) await page.waitForSelector(".change-card");
      const { scrollWidth, clientWidth } = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
      expect(scrollWidth, route).toBeLessThanOrEqual(clientWidth + 1);
    }
  });
}

test("first-page rendering remains deterministic", async ({ page }) => {
  await page.goto("/demo/ranked_change_feed.html");
  await page.waitForSelector(".change-card");
  const first = await page.locator(".change-card").first().innerText();
  await page.reload(); await page.waitForSelector(".change-card");
  expect(await page.locator(".change-card").first().innerText()).toBe(first);
});
