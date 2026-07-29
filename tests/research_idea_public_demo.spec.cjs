const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

function monitor(page) {
  const issues = [];
  page.on("console", (message) => {
    if (message.type() === "error") issues.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => issues.push(`page: ${error.message}`));
  page.on("requestfailed", (request) => issues.push(`request: ${request.url()}`));
  return issues;
}

async function noOverflow(page) {
  await expect.poll(() => page.evaluate(() => ({
    body: document.body.scrollWidth,
    viewport: document.documentElement.clientWidth
  }))).toEqual(expect.objectContaining({ body: expect.any(Number), viewport: expect.any(Number) }));
  const widths = await page.evaluate(() => [document.body.scrollWidth, document.documentElement.clientWidth]);
  expect(widths[0]).toBeLessThanOrEqual(widths[1] + 1);
}

test("public gallery reconciles two hypotheses, six safe failures, and zero actionable views", async ({ page }) => {
  const issues = monitor(page);
  await page.goto("/demo/research_ideas.html");
  await expect(page.getByRole("heading", { name: "Experimental Research Ideas" })).toBeVisible();
  await expect(page.locator(".public-published-card")).toHaveCount(2);
  await expect(page.locator(".public-safe-failure-card")).toHaveCount(5);
  await expect(page.getByText("0", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Actionable trade views", { exact: true })).toBeVisible();
  await expect(page.getByText("Formal blinded human ratings remain pending.", { exact: false }).first()).toBeVisible();
  await page.locator("#safe-failure-filter").selectOption("REJECT_PREVIOUSLY_DISCLOSED");
  await expect(page.locator(".public-safe-failure-card")).toHaveCount(2);
  await expect(page.locator("#safe-failure-count")).toContainText("2 of 5");
  expect(issues).toEqual([]);
});

for (const [ticker, route] of [["RH", "research_idea_rh.html"], ["DVN", "research_idea_dvn.html"]]) {
  test(`${ticker} renders evidence, separated interpretation, falsification, skeptic, and no trade view`, async ({ page }) => {
    const issues = monitor(page);
    await page.goto(`/demo/${route}`);
    await expect(page.getByText("Full prior-filing evidence checked", { exact: false })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Source evidence" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Verified novelty" })).toBeVisible();
    await expect(page.getByText("FACT", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("INFERENCE", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("UNCERTAINTY", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("AI-GENERATED RESEARCH HYPOTHESIS", { exact: true })).toBeVisible();
    await expect(page.getByText("Falsification", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Skeptical review" })).toBeVisible();
    await expect(page.getByText("NO ACTIONABLE TRADE VIEW", { exact: true })).toBeVisible();
    await expect(page.getByText("This hypothesis has not been validated against future outcomes.", { exact: false })).toBeVisible();
    expect(issues).toEqual([]);
  });
}

test("EFX correction preserves exact financial roles and rejected claims", async ({ page }) => {
  const issues = monitor(page);
  await page.goto("/demo/research_idea_efx.html");
  await expect(page.getByRole("heading", { name: "When the Evidence Rejects the Idea" })).toBeVisible();
  const rows = page.locator(".public-data-table tbody tr");
  await expect(rows).toHaveCount(3);
  await expect(rows.nth(0)).toContainText("$125M");
  await expect(rows.nth(0)).toContainText("Conditional top-up");
  await expect(rows.nth(0)).toContainText("PREVIOUSLY_DISCLOSED_IN_10K");
  await expect(rows.nth(1)).toContainText("$346.7M");
  await expect(rows.nth(1)).toContainText("Remaining payment balance");
  await expect(rows.nth(2)).toContainText("~$345M");
  await expect(rows.nth(2)).toContainText("Cash deposit");
  await expect(page.getByText("INCOMPARABLE_QUANTITIES", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Rejected claims" })).toBeVisible();
  await expect(page.getByText("Current liquidity stress", { exact: true })).toBeVisible();
  await expect(page.getByText("NO_ACTIONABLE_TRADE_VIEW", { exact: true })).toBeVisible();
  expect(issues).toEqual([]);
});

test("analyst controls persist locally and JSON/Markdown exports work", async ({ page }) => {
  await page.goto("/demo/research_idea_rh.html");
  await page.getByRole("button", { name: "Accept with edits", exact: true }).click();
  await page.locator("#public-analyst-notes").fill("Discuss evidence specificity.");
  await page.getByRole("button", { name: "Save locally" }).click();
  await page.reload();
  await expect(page.getByRole("button", { name: "Accept with edits", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#public-analyst-notes")).toHaveValue("Discuss evidence specificity.");
  const jsonDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON" }).click();
  expect((await jsonDownload).suggestedFilename()).toBe("rh-research-hypothesis.json");
  const markdownDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export Markdown" }).click();
  expect((await markdownDownload).suggestedFilename()).toBe("rh-research-hypothesis.md");
  await page.evaluate(() => { window.__printed = false; window.print = () => { window.__printed = true; }; });
  await page.getByRole("button", { name: "Print / save as PDF" }).click();
  expect(await page.evaluate(() => window.__printed)).toBe(true);
});

test("public methodology exposes the eight-stage grounding workflow and scale block", async ({ page }) => {
  await page.goto("/demo/research_idea_methodology.html");
  await expect(page.getByRole("heading", { name: "How Research Ideas Are Grounded" })).toBeVisible();
  await expect(page.locator(".public-method-grid li")).toHaveCount(8);
  await expect(page.getByRole("heading", { name: "The 60-case phase remains blocked." })).toBeVisible();
  await expect(page.getByText("No position sizing generated", { exact: true })).toBeVisible();
});

for (const viewport of [
  { width: 1440, height: 900 },
  { width: 1024, height: 768 },
  { width: 390, height: 844 }
]) {
  test(`public research idea pages are accessible and responsive at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    for (const route of [
      "research_ideas.html",
      "research_idea_rh.html",
      "research_idea_dvn.html",
      "research_idea_efx.html",
      "research_idea_methodology.html"
    ]) {
      const issues = monitor(page);
      await page.goto(`/demo/${route}`);
      await page.waitForLoadState("networkidle");
      await noOverflow(page);
      const results = await new AxeBuilder({ page }).analyze();
      expect(results.violations.filter((violation) => ["serious", "critical"].includes(violation.impact))).toEqual([]);
      expect(issues).toEqual([]);
    }
  });
}

test("all public research idea internal links resolve with relative GitHub Pages paths", async ({ page, request }) => {
  for (const route of [
    "research_ideas.html",
    "research_idea_rh.html",
    "research_idea_dvn.html",
    "research_idea_efx.html",
    "research_idea_methodology.html"
  ]) {
    await page.goto(`/demo/${route}`);
    const hrefs = await page.locator("a[href]").evaluateAll((links) => links.map((link) => link.getAttribute("href")));
    for (const href of hrefs.filter((value) => value && !value.startsWith("http") && !value.startsWith("#"))) {
      expect((await request.get(new URL(href, page.url()).href)).status(), `${route} -> ${href}`).toBeLessThan(400);
    }
  }
});
