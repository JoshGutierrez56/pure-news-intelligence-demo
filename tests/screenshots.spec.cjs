const { test, expect } = require("@playwright/test");
const fs = require("node:fs");
const path = require("node:path");

test.describe.configure({ mode: "serial" });
const output = path.resolve(__dirname, "..", "artifacts", "screenshots", "redesign");
fs.mkdirSync(output, { recursive: true });

for (const viewport of [
  { width: 1920, height: 1080 }, { width: 1440, height: 900 },
  { width: 1024, height: 768 }, { width: 390, height: 844 }
]) {
  test(`capture reviewed pages at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    for (const [name, route, ready] of [
      ["ranked-feed", "/demo/ranked_change_feed.html", ".change-card"],
      ["professor-presentation", "/demo/professor_presentation.html", "#presentation-title"]
    ]) {
      await page.goto(route);
      await page.waitForSelector(ready);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);
      await page.screenshot({
        path: path.join(output, `${name}-${viewport.width}x${viewport.height}.png`),
        fullPage: false
      });
    }
  });
}
