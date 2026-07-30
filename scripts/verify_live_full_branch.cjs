const { chromium } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

const BASE = "https://joshgutierrez56.github.io/pure-news-intelligence-demo";
const routes = [
  "/",
  "/demo/ranked_change_feed.html",
  "/demo/case_studies.html",
  "/demo/research_results.html",
  "/demo/methodology.html",
  "/demo/professor_presentation.html",
  "/demo/innovation_framework.html",
  "/demo/pilot_plan.html",
  "/demo/professor_materials.html",
  "/demo/research_ideas.html",
  "/demo/research_idea_rh.html",
  "/demo/research_idea_dvn.html",
  "/demo/research_idea_efx.html",
  "/demo/research_idea_methodology.html",
  "/demo/faq.html",
  "/demo/known_limitations.html",
  "/demo/future_research.html",
  "/demo/public_architecture.html",
  "/demo/universe_coverage_preview.html"
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

(async () => {
  const browser = await chromium.launch({ channel: "msedge", headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
  const page = await context.newPage();
  const errors = [];
  const internal = new Set();
  let axeSeriousCritical = 0;
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console ${message.text()}`);
  });
  page.on("pageerror", (error) => errors.push(`page ${error.message}`));
  page.on("requestfailed", (request) => errors.push(`request ${request.url()}`));

  for (const route of routes) {
    const response = await page.goto(`${BASE}${route}?verify=4f884e9`, { waitUntil: "networkidle" });
    assert(response && response.status() < 400, `${route} returned ${response && response.status()}`);
    assert((await page.title()).trim(), `${route} missing title`);
    assert(await page.locator("h1").count() === 1, `${route} must have one h1`);
    assert(await page.locator('meta[name="description"]').getAttribute("content"), `${route} missing description`);
    const widths = await page.evaluate(() => [document.body.scrollWidth, document.documentElement.clientWidth]);
    assert(widths[0] <= widths[1] + 1, `${route} desktop overflow ${widths}`);
    const axe = await new AxeBuilder({ page }).analyze();
    axeSeriousCritical += axe.violations.filter((item) => ["serious", "critical"].includes(item.impact)).length;
    for (const href of await page.locator("a[href]").evaluateAll((links) => links.map((link) => link.href))) {
      const parsed = new URL(href);
      if (parsed.origin === new URL(BASE).origin && parsed.pathname.startsWith("/pure-news-intelligence-demo/")) {
        parsed.search = "";
        parsed.hash = "";
        internal.add(parsed.href);
      }
    }
  }

  let brokenLinks = 0;
  for (const url of internal) {
    const response = await context.request.get(url);
    if (response.status() >= 400) {
      brokenLinks += 1;
      errors.push(`link ${response.status()} ${url}`);
    }
  }

  await page.goto(`${BASE}/demo/research_ideas.html?verify=4f884e9`, { waitUntil: "networkidle" });
  assert(await page.locator(".public-published-card").count() === 2, "gallery publishable count");
  assert(await page.locator(".public-safe-failure-card").count() === 5, "gallery safe-failure card count");

  await page.goto(`${BASE}/demo/research_idea_rh.html?verify=4f884e9`, { waitUntil: "networkidle" });
  assert(await page.getByText("NO ACTIONABLE TRADE VIEW", { exact: true }).count() > 0, "RH trade boundary");
  await page.getByRole("button", { name: "Accept with edits", exact: true }).click();
  await page.locator("#public-analyst-notes").fill("Live verification");
  await page.getByRole("button", { name: "Save locally" }).click();
  await page.reload({ waitUntil: "networkidle" });
  assert(await page.getByRole("button", { name: "Accept with edits", exact: true }).getAttribute("aria-pressed") === "true", "local disposition");
  const jsonDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON" }).click();
  assert((await jsonDownload).suggestedFilename() === "rh-research-hypothesis.json", "JSON export");
  const markdownDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export Markdown" }).click();
  assert((await markdownDownload).suggestedFilename() === "rh-research-hypothesis.md", "Markdown export");
  await page.evaluate(() => { window.__printed = false; window.print = () => { window.__printed = true; }; });
  await page.getByRole("button", { name: "Print / save as PDF" }).click();
  assert(await page.evaluate(() => window.__printed), "print flow");

  await page.goto(`${BASE}/demo/research_idea_efx.html?verify=4f884e9`, { waitUntil: "networkidle" });
  assert(await page.getByText("INCOMPARABLE_QUANTITIES", { exact: true }).count() > 0, "EFX incomparable quantities");
  assert((await page.locator(".public-data-table tbody tr").nth(1).innerText()).includes("Remaining payment balance"), "EFX balance role");

  await page.goto(`${BASE}/demo/professor_presentation.html?verify=4f884e9`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "5 min" }).click();
  await page.getByRole("button", { name: "Present" }).click();
  assert((await page.locator("[data-presentation-position]").innerText()) === "1 / 8", "5-minute mode");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "10 min" }).click();
  await page.keyboard.press("f");
  assert((await page.locator("[data-presentation-position]").innerText()) === "1 / 12", "10-minute mode");
  await page.keyboard.press("Escape");

  await page.goto(`${BASE}/demo/universe_coverage_preview.html?verify=4f884e9`, { waitUntil: "networkidle" });
  assert(await page.getByText("6,190", { exact: true }).count() > 0, "universe total");
  await page.locator("#universe-search").fill("EFX");
  assert(await page.locator("#universe-rows tr").count() === 1, "universe search");
  await page.locator("#universe-search").fill("");
  await page.locator("#universe-news").selectOption("missing");
  assert((await page.locator("#universe-result-count").innerText()).includes("5,414 of 6,190"), "universe filter");
  await page.locator("#universe-search").focus();
  assert(await page.locator("#universe-search").evaluate((node) => node === document.activeElement), "keyboard focus");
  await page.emulateMedia({ media: "print" });
  assert(!(await page.locator(".site-header").isVisible()), "print navigation");
  await page.emulateMedia({ media: "screen" });

  for (const route of ["/", "/demo/research_idea_rh.html", "/demo/universe_coverage_preview.html"]) {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${BASE}${route}?verify=4f884e9`, { waitUntil: "networkidle" });
    const widths = await page.evaluate(() => [document.body.scrollWidth, document.documentElement.clientWidth]);
    assert(widths[0] <= widths[1] + 1, `${route} mobile overflow ${widths}`);
  }

  assert(axeSeriousCritical === 0, `axe serious/critical ${axeSeriousCritical}`);
  assert(brokenLinks === 0, `broken links ${brokenLinks}`);
  assert(errors.length === 0, errors.join("\n"));
  console.log(JSON.stringify({
    routes_checked: routes.length,
    internal_links_checked: internal.size,
    broken_links: brokenLinks,
    console_request_errors: errors.length,
    serious_critical_axe_violations: axeSeriousCritical,
    responsive: "PASS",
    keyboard: "PASS",
    print: "PASS",
    exports: "PASS",
    analyst_controls: "PASS",
    presentation_modes: "PASS",
    universe_search_filters: "PASS"
  }, null, 2));
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
