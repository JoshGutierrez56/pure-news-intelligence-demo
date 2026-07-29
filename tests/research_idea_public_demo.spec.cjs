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

test("homepage and shared navigation expose the experimental engine without displacing the core product", async ({ page }) => {
  await page.goto("/");
  const coreHero = page.locator("main > .hero");
  const experimental = page.locator(".experimental-capability");
  await expect(coreHero).toBeVisible();
  await expect(experimental).toBeVisible();
  expect(await coreHero.evaluate((node) => node.compareDocumentPosition(document.querySelector(".experimental-capability")) & Node.DOCUMENT_POSITION_FOLLOWING)).toBeTruthy();
  await expect(page.getByRole("heading", { name: "Turn a Verified Change into a Testable Research Question" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Explore the Research Idea Engine" })).toHaveAttribute("href", "demo/research_ideas.html");
  for (const route of [
    "/", "/demo/professor_presentation.html", "/demo/ranked_change_feed.html",
    "/demo/case_studies.html", "/demo/research_results.html", "/demo/methodology.html",
    "/demo/innovation_framework.html", "/demo/pilot_plan.html", "/demo/professor_materials.html"
  ]) {
    await page.goto(route);
    await expect(page.locator("#primary-nav").getByRole("link", { name: "Research Ideas", exact: true })).toBeVisible();
  }
});

test("professor presentation includes grounded hypothesis and safe-failure screens in both duration modes", async ({ page }) => {
  await page.goto("/demo/professor_presentation.html");
  await expect(page.locator(".story-section")).toHaveCount(12);
  await expect(page.getByRole("heading", { name: /verified change can become a falsifiable research agenda/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Full-prior retrieval stopped/i })).toBeVisible();
  await expect(page.getByText("no improvement in Sharpe ratio or information coefficient", { exact: false })).toBeAttached();
  await page.getByRole("button", { name: "5 min" }).click();
  await page.getByRole("button", { name: "Present" }).click();
  await expect(page.locator("[data-presentation-position]")).toHaveText("1 / 8");
  await page.keyboard.press("End");
  await expect(page.locator("[data-presentation-position]")).toHaveText("8 / 8");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "10 min" }).click();
  await page.keyboard.press("f");
  await expect(page.locator("[data-presentation-position]")).toHaveText("1 / 12");
  await page.keyboard.press("Escape");
});

test("ranked feed uses frozen research statuses and filtering with no live generation", async ({ page }) => {
  await page.goto("/demo/ranked_change_feed.html");
  await expect(page.getByLabel("Research idea status")).toBeVisible();
  await page.locator("#filter-search").fill("RH");
  const rhCard = page.locator('.change-card[data-record-id="412b08746bb0ed5a7745"]');
  await expect(rhCard.getByText("Research idea available", { exact: true }).first()).toBeVisible();
  await expect(rhCard.getByRole("link", { name: "View AI Research Hypothesis" })).toHaveAttribute("href", "research_idea_rh.html");
  await page.locator("#filter-search").fill("EFX");
  const efxCard = page.locator('.change-card[data-record-id="279e7d4e407851a19548"]');
  await expect(efxCard.getByText("Idea rejected after full evidence review", { exact: true }).first()).toBeVisible();
  await expect(efxCard.getByRole("link", { name: "View grounding rejection" })).toHaveAttribute("href", "research_idea_efx.html");
  await page.locator("#filter-search").fill("");
  await page.locator("#filter-research-idea").selectOption("available");
  await expect(page.locator(".change-card")).not.toHaveCount(0);
  await expect(page.getByText("Generate Research Idea", { exact: true })).toHaveCount(0);
});

test("results, methodology, framework, pilot, and cases reconcile the bounded result", async ({ page }) => {
  const expectations = [
    ["/demo/research_results.html", "Research Idea Engine V2", "READY_FOR_PUBLIC_DEMO"],
    ["/demo/methodology.html", "How Research Ideas Are Grounded", "broader generation remains blocked"],
    ["/demo/innovation_framework.html", "A research-question layer, governed by safe refusal", "Formal human ratings pending"],
    ["/demo/pilot_plan.html", "Measure research-agenda quality before market performance", "Only after hypotheses are frozen prospectively"],
    ["/demo/case_studies.html", "Three Outcomes the Engine Can Produce", "formal analyst validation remains pending"]
  ];
  for (const [route, heading, copy] of expectations) {
    await page.goto(route);
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    await expect(page.getByText(copy, { exact: false }).first()).toBeVisible();
  }
});
