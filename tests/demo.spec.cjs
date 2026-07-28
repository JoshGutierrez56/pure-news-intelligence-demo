const { test, expect } = require("@playwright/test");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const changePayload = JSON.parse(fs.readFileSync(path.join(root, "demo/data/changes.json"), "utf8"));
const publicPages = [
  "/", "/demo/professor_presentation.html", "/demo/ranked_change_feed.html",
  "/demo/case_studies.html", "/demo/company_comparison.html",
  "/demo/company_timeline.html", "/demo/research_results.html", "/demo/methodology.html",
  "/demo/private_workspace.html"
];

test("frozen research metrics reconcile", async ({ page }) => {
  expect(changePayload.records).toHaveLength(995);
  const novelty = { previous: 0, new: 0, partial: 0, unclear: 0 };
  let highConfidence = 0;
  for (const record of changePayload.records) {
    expect(record.id).toBeTruthy();
    expect(record.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(record.ticker).toBeTruthy();
    expect(record.issuer).toBeTruthy();
    expect(record.title).toBeTruthy();
    expect(record.summary).toBeTruthy();
    expect(record.why).toBeTruthy();
    expect(record.category).toBeTruthy();
    expect(record.materiality).toMatch(/^(high|medium|low)$/);
    expect(record.confidence).toBeGreaterThan(0);
    expect(record.url).toMatch(/^https:\/\/www\.sec\.gov\//);
    if (record.confidence >= .8) highConfidence += 1;
    const title = record.title.toLowerCase();
    if (title.includes("previously disclosed") || title.includes("previously covered in news")) novelty.previous += 1;
    else if (title.includes("genuinely new")) novelty.new += 1;
    else if (title.includes("partially anticipated")) novelty.partial += 1;
    else novelty.unclear += 1;
  }
  expect(novelty).toEqual({ previous: 394, new: 342, partial: 243, unclear: 16 });
  expect(highConfidence).toBe(629);
  await page.goto("/demo/professor_presentation.html");
  await expect(page.getByText("1,990", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("point-in-time violations", { exact: true })).toBeVisible();
  await expect(page.getByText("point-in-time violations", { exact: true }).locator("..")).toContainText("0");
});

test("public pages have titles, descriptions, headings, navigation, and no console errors", async ({ page }) => {
  const errors = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));
  for (const route of publicPages) {
    await page.goto(route);
    await expect(page).toHaveTitle(/\S+ \| Pure News Intelligence|Pure News Intelligence \|/);
    await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /\S+/);
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.getByRole("link", { name: "Professor Presentation", exact: true })).toHaveCount(1);
  }
  expect(errors).toEqual([]);
});

test("internal navigation targets and case-study links resolve", async ({ request }) => {
  const htmlFiles = fs.readdirSync(path.join(root, "demo")).filter((file) => file.endsWith(".html"));
  for (const file of htmlFiles) {
    const html = fs.readFileSync(path.join(root, "demo", file), "utf8");
    const links = [...html.matchAll(/href="([^"]+)"/g)].map((match) => match[1])
      .filter((href) => !href.startsWith("#") && !href.startsWith("http") && !href.startsWith("data:"));
    for (const href of links) {
      const url = new URL(href, `http://127.0.0.1:4173/demo/${file}`).pathname;
      const response = await request.get(url);
      expect(response.status(), `${file} -> ${href}`).toBe(200);
    }
  }
  for (let index = 1; index <= 8; index += 1) {
    const response = await request.get(`/demo/evidence_packets/0${index}_${["TFC","KHC","DLTR","DVN","RH","FCX","EFX","CHE"][index - 1]}.html`);
    expect(response.status()).toBe(200);
  }
});

test("ranked feed filters, sorts, changes view, paginates, and clears state", async ({ page }) => {
  await page.goto("/demo/ranked_change_feed.html");
  await expect(page.getByText("995 of 995 changes")).toBeVisible();
  await page.getByLabel("Company or ticker").fill("KHC");
  await expect(page.getByText(/of 995 changes/)).not.toHaveText("995 of 995 changes · showing 1–24");
  await expect(page.locator(".change-card")).toHaveCount(await page.locator(".change-card").count());
  expect(await page.locator(".change-card").count()).toBeGreaterThan(0);
  await page.locator("#filter-novelty").selectOption("previously disclosed");
  await expect(page.locator(".change-card").first()).toContainText("Previously Disclosed");
  await page.getByRole("button", { name: "Clear all" }).click();
  await expect(page.getByText("Active filters:").locator("..")).toContainText("None");
  await page.getByLabel("Sort").selectOption("confidence");
  const confidenceText = await page.locator(".change-card .status-chip").first().textContent();
  expect(confidenceText).toContain("0.990");
  await page.getByRole("button", { name: "Table" }).click();
  await expect(page.locator(".cards-table")).toBeVisible();
  await page.getByRole("button", { name: "Cards" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByText(/Page 2 of/)).toBeVisible();
  await expect(page.locator('.change-card a[href^="https://www.sec.gov/"]').first()).toBeVisible();
});

test("presentation mode supports keyboard navigation and exit", async ({ page }) => {
  await page.goto("/demo/professor_presentation.html");
  const toggle = page.getByRole("button", { name: "Presentation mode" });
  await toggle.click();
  await expect(page.locator("body")).toHaveClass(/presentation-active/);
  await expect(page.locator(".story-section.is-current")).toHaveCount(1);
  await expect(page.locator("[data-presentation-position]")).toHaveText("1 / 10");
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("[data-presentation-position]")).toHaveText("2 / 10");
  await page.keyboard.press("End");
  await expect(page.locator("[data-presentation-position]")).toHaveText("10 / 10");
  await page.keyboard.press("Escape");
  await expect(page.locator("body")).not.toHaveClass(/presentation-active/);
});

test("source-boundary and ex-ante/ex-post labels remain explicit", async ({ page }) => {
  await page.goto("/demo/methodology.html");
  await expect(page.getByText("Available at filing time", { exact: true })).toBeVisible();
  await expect(page.getByText("System interpretation", { exact: true })).toBeVisible();
  await expect(page.getByText("Analyst interpretation", { exact: true })).toBeVisible();
  await expect(page.getByText("Observed later", { exact: true })).toBeVisible();
  await expect(page.getByText(/Genuinely new.*bounded search result/)).toBeVisible();
  await page.goto("/demo/professor_presentation.html");
  await expect(page.getByText(/Ex post—observed later, not available at filing time/)).toBeVisible();
});

test("interactive controls expose accessible names and visible focus", async ({ page }) => {
  for (const route of ["/demo/ranked_change_feed.html", "/demo/professor_presentation.html", "/demo/private_workspace.html"]) {
    await page.goto(route);
    const unnamed = await page.locator("button, input, select, textarea").evaluateAll((controls) =>
      controls.filter((control) => {
        const label = control.labels?.[0]?.textContent?.trim();
        return !(label || control.getAttribute("aria-label") || control.getAttribute("aria-labelledby") || control.textContent.trim());
      }).map((control) => `${control.tagName}#${control.id}`)
    );
    expect(unnamed, route).toEqual([]);
  }
  await page.goto("/demo/ranked_change_feed.html");
  await page.keyboard.press("Tab");
  const outlineStyle = await page.locator(":focus").evaluate((element) => getComputedStyle(element).outlineStyle);
  expect(outlineStyle).not.toBe("none");
});

for (const viewport of [
  { width: 1920, height: 1080 }, { width: 1440, height: 900 },
  { width: 1024, height: 768 }, { width: 390, height: 844 }
]) {
  test(`ranked feed has no horizontal page overflow at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/demo/ranked_change_feed.html");
    await page.waitForSelector(".change-card");
    const dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client + 1);
  });
}

test("deterministic first-page rendering", async ({ page }) => {
  await page.goto("/demo/ranked_change_feed.html");
  await page.waitForSelector(".change-card");
  const first = await page.locator(".change-card").first().innerText();
  await page.reload();
  await page.waitForSelector(".change-card");
  expect(await page.locator(".change-card").first().innerText()).toBe(first);
});
