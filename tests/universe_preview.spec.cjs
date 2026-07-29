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

test("summary metrics reconcile and indexing boundary is explicit", async ({ page }) => {
  const issues = monitor(page);
  await page.goto("/demo/universe_coverage_preview.html");
  await expect(page.getByRole("heading", { name: "See what is indexed, validated, and still missing." })).toBeVisible();
  await expect(page.getByText("6,190", { exact: true })).toBeVisible();
  await expect(page.getByText("149", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("3,072", { exact: true })).toBeVisible();
  await expect(page.getByText("776", { exact: true })).toBeVisible();
  await expect(page.getByText("2,973", { exact: true })).toBeVisible();
  await expect(page.getByText("Metadata indexing does not mean full disclosure-change analysis has been completed.", { exact: false })).toBeVisible();
  expect(issues).toEqual([]);
});

test("search and all coverage filters work", async ({ page }) => {
  await page.goto("/demo/universe_coverage_preview.html");
  await page.locator("#universe-search").fill("EFX");
  await expect(page.locator("#universe-rows tr")).toHaveCount(1);
  await expect(page.locator("#universe-rows")).toContainText("EQUIFAX");
  await expect(page.locator("#universe-rows")).toContainText("Research Idea Engine reviewed");
  await page.locator("#universe-search").fill("");
  await page.locator("#universe-status").selectOption({ label: "Metadata indexed" });
  await expect(page.locator("#universe-result-count")).toContainText("506 of 6,190");
  await page.locator("#universe-status").selectOption("");
  await page.locator("#universe-news").selectOption("missing");
  await expect(page.locator("#universe-result-count")).toContainText("5,414 of 6,190");
  await page.locator("#universe-news").selectOption("");
  await page.locator("#universe-validated").selectOption("idea");
  await expect(page.locator("#universe-result-count")).toContainText("8 of 6,190");
  await page.locator("#universe-10k").selectOption("available");
  await page.locator("#universe-8k").selectOption("available");
  await expect(page.locator("#universe-rows tr").first()).toBeVisible();
});

test("missing news is unavailable rather than zero", async ({ page }) => {
  await page.goto("/demo/universe_coverage_preview.html");
  await page.locator("#universe-news").selectOption("missing");
  await expect(page.locator("#universe-rows").getByText("News metadata unavailable").first()).toBeVisible();
});

for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  test(`preview is accessible and responsive at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    const issues = monitor(page);
    await page.setViewportSize(viewport);
    await page.goto("/demo/universe_coverage_preview.html");
    const axe = await new AxeBuilder({ page }).analyze();
    expect(axe.violations.filter((item) => ["serious", "critical"].includes(item.impact))).toEqual([]);
    const widths = await page.evaluate(() => [document.body.scrollWidth, document.documentElement.clientWidth]);
    expect(widths[0]).toBeLessThanOrEqual(widths[1] + 1);
    await page.locator("#universe-search").focus();
    await expect(page.locator("#universe-search")).toBeFocused();
    expect(issues).toEqual([]);
  });
}

test("homepage exposes only a secondary universe preview link", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "View Universe Coverage Preview" })).toBeVisible();
  await expect(page.getByText("Explore which companies have filing and permitted news metadata indexed for future staged analysis.")).toBeVisible();
});

test("preview print keeps the coverage ledger and hides navigation", async ({ page }) => {
  await page.goto("/demo/universe_coverage_preview.html");
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".site-header")).toBeHidden();
  await expect(page.getByRole("heading", { name: "Search and filter the frozen universe" })).toBeVisible();
});
