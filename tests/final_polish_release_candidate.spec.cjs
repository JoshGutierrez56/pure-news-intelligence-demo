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

test("homepage leads with the product and seven-step visitor path", async ({ page }) => {
  const issues = monitor(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Find What Changed. Verify the Evidence. Decide What to Investigate." })).toBeVisible();
  await expect(page.getByRole("link", { name: "Explore the Demo" })).toBeVisible();
  await expect(page.getByRole("link", { name: "View the Research Evidence" })).toBeVisible();
  await expect(page.locator("#primary-nav a")).toHaveCount(7);
  await expect(page.locator(".trust-signals li")).toHaveCount(4);
  expect(issues).toEqual([]);
});

for (const [route, heading] of [
  ["/demo/faq.html", "Direct answers about what the project does—and does not prove."],
  ["/demo/known_limitations.html", "The strongest claims are deliberately narrow."],
  ["/demo/future_research.html", "Earn the next claim in the right order."],
  ["/demo/public_architecture.html", "Evidence flows forward. Accountability stays with the analyst."]
]) {
  test(`${route} renders cleanly and passes serious accessibility checks`, async ({ page }) => {
    const issues = monitor(page);
    await page.goto(route);
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations.filter((item) => ["serious", "critical"].includes(item.impact))).toEqual([]);
    const overflow = await page.evaluate(() => document.body.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
    expect(issues).toEqual([]);
  });
}

test("research results presents four-stage metadata without modifying locked HTML", async ({ page }) => {
  await page.goto("/demo/research_results.html");
  await expect(page).toHaveTitle("Research Program Results | Pure News Intelligence");
  await expect(page.getByRole("heading", { name: "Research Idea Engine V2" })).toBeVisible();
  await expect(page.getByText("8 cases evaluated; 2 publishable hypotheses; 6 safe failures; 0 actionable trade views", { exact: false })).toBeVisible();
});

test("mobile navigation and homepage layout remain usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Menu" }).click();
  await expect(page.locator("#primary-nav")).toHaveClass(/open/);
  await expect(page.getByRole("link", { name: "Research Ideas" })).toBeVisible();
  const overflow = await page.evaluate(() => document.body.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});

test("browser metadata and social-preview tags are present", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Pure News Intelligence/);
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /disclosure changes/i);
  await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", /Pure News Intelligence/);
  await expect(page.locator('meta[property="og:description"]')).toHaveAttribute("content", /verify the evidence/i);
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", /^https:\/\//);
});

test("print layout hides navigation and preserves research content", async ({ page }) => {
  await page.goto("/demo/research_idea_rh.html");
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".site-header")).toBeHidden();
  await expect(page.getByRole("heading", { name: "Source evidence" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Skeptical review" })).toBeVisible();
});
