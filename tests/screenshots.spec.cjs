const { test, expect } = require("@playwright/test");
const fs = require("node:fs");
const path = require("node:path");

test.describe.configure({ mode: "serial" });
const output = path.resolve(__dirname, "..", "artifacts", "screenshots", "v2");
fs.mkdirSync(output, { recursive: true });
const viewports = [{ width: 1920, height: 1080 }, { width: 1440, height: 900 }, { width: 1024, height: 768 }, { width: 390, height: 844 }];
const pages = [
  ["overview", "/"],
  ["ranked-feed", "/demo/ranked_change_feed.html", ".change-card"],
  ["case-gallery", "/demo/case_studies.html"],
  ["research-results", "/demo/research_results.html"],
  ["innovation-framework", "/demo/innovation_framework.html"],
  ["pilot-plan", "/demo/pilot_plan.html"]
];

async function presentAt(page, index) {
  await page.goto("/demo/professor_presentation.html");
  await page.getByRole("button", { name: "Present" }).click();
  await page.keyboard.press("Home");
  for (let i = 0; i < index; i += 1) await page.keyboard.press("ArrowRight");
  await page.waitForTimeout(250);
}

for (const viewport of viewports) {
  test(`capture required v2 review set at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    for (const [name, route, ready] of pages) {
      await page.goto(route);
      if (ready) await page.waitForSelector(ready);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, name).toBeLessThanOrEqual(1);
      await page.screenshot({ path: path.join(output, `${name}-${viewport.width}x${viewport.height}.png`), fullPage: false });
    }
    for (const [name, index] of [["presentation-01-problem", 0], ["presentation-03-discovery", 2], ["presentation-06-pivot", 5], ["presentation-08-case", 7]]) {
      await presentAt(page, index);
      await page.screenshot({ path: path.join(output, `${name}-${viewport.width}x${viewport.height}.png`), fullPage: false });
      await page.keyboard.press("Escape");
    }
  });
}
