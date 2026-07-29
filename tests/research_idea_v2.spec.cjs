const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const packetRoot = path.join(root, "demo", "data", "research_idea_packets", "v2");
const index = JSON.parse(fs.readFileSync(path.join(packetRoot, "index.json"), "utf8"));
const efxId = "279e7d4e407851a19548";
const viewports = [
  { width: 1440, height: 900 },
  { width: 1024, height: 768 },
  { width: 390, height: 844 }
];

function monitor(page) {
  const issues = [];
  page.on("console", (message) => {
    if (message.type() === "error") issues.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => issues.push(`pageerror: ${error.message}`));
  page.on("requestfailed", (request) => issues.push(`request: ${request.url()}`));
  page.on("response", (response) => {
    if (response.url().startsWith("http://127.0.0.1:4173/") && response.status() >= 400) {
      issues.push(`http ${response.status()}: ${response.url()}`);
    }
  });
  return issues;
}

async function noOverflow(page) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
}

test("V2 detail renders the repaired EFX verdict and evidence controls", async ({ page }) => {
  const issues = monitor(page);
  await page.goto(`/demo/research_idea_v2.html?change_id=${efxId}`);
  await expect(page.locator("#ri-v2-detail")).toHaveAttribute("aria-busy", "false");
  await expect(page.getByRole("heading", { level: 1, name: /EQUIFAX INC/ })).toBeVisible();
  await expect(page.getByText("Full prior-filing evidence checked", { exact: false })).toBeVisible();
  await expect(page.getByText("REJECT_MISLEADING_COMPARISON", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("RESOLVED_OR_FINALIZED_PRIOR_UNCERTAINTY", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("$346.7 million", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("remaining balance", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("conditional top-up", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("No grounded research hypothesis", { exact: true })).toBeVisible();
  await expect(page.getByText("Default: NOT_READY", { exact: true })).toBeVisible();
  expect(issues).toEqual([]);
});

test("V2 gallery shows all eight cases and only two publishable packets", async ({ page }) => {
  const issues = monitor(page);
  await page.goto("/demo/research_idea_v2_gallery.html");
  await expect(page.locator("#ri-v2-gallery")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator(".ri-gallery-card")).toHaveCount(8);
  await expect(page.getByText("2 publishable · 8 reviewed · 60-case sample blocked")).toBeVisible();
  await expect(page.locator(".ri-gallery-card .status.success", { hasText: "PUBLISHABLE" })).toHaveCount(2);
  expect(issues).toEqual([]);
});

test("V2 methodology states the repaired evidence and scale boundaries", async ({ page }) => {
  await page.goto("/demo/research_idea_v2_methodology.html");
  await expect(page.getByRole("heading", { level: 1, name: /excerpt is evidence/i })).toBeVisible();
  await expect(page.getByText("The $125M conditional top-up already appeared", { exact: false })).toBeVisible();
  await expect(page.getByText("Quality is not optimized to force a pass.", { exact: true })).toBeVisible();
});

for (const viewport of viewports) {
  test(`V2 surfaces are accessible and responsive at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    for (const route of [
      `/demo/research_idea_v2.html?change_id=${efxId}`,
      "/demo/research_idea_v2_gallery.html",
      "/demo/research_idea_v2_methodology.html"
    ]) {
      const issues = monitor(page);
      await page.goto(route);
      const busy = page.locator("[aria-busy=true]");
      if (await busy.count()) await expect(busy).toHaveCount(0);
      await noOverflow(page);
      const results = await new AxeBuilder({ page }).analyze();
      expect(results.violations).toEqual([]);
      expect(issues).toEqual([]);
    }
  });
}

test("V2 relative paths and links resolve without public deployment", async ({ page }) => {
  for (const route of [
    "/demo/research_idea_v2.html",
    "/demo/research_idea_v2_gallery.html",
    "/demo/research_idea_v2_methodology.html"
  ]) {
    await page.goto(route);
    const links = await page.locator("a[href]").evaluateAll((nodes) => nodes.map((node) => node.href));
    for (const href of links.filter((value) => value.startsWith("http://127.0.0.1:4173/"))) {
      const response = await page.request.get(href);
      expect(response.status(), href).toBe(200);
    }
  }
  expect(index.packet_count).toBe(8);
});
