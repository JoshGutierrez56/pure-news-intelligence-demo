const { test, expect } = require("@playwright/test");
const path = require("node:path");

const surfaces = [
  ["homepage", "/"],
  ["ranked-feed", "/demo/ranked_change_feed.html"],
  ["rh", "/demo/research_idea_rh.html"],
  ["dvn", "/demo/research_idea_dvn.html"],
  ["efx", "/demo/research_idea_efx.html"],
  ["research-results", "/demo/research_results.html"],
  ["methodology", "/demo/methodology.html"],
  ["professor-presentation", "/demo/professor_presentation.html"],
  ["innovation-framework", "/demo/innovation_framework.html"],
  ["pilot-plan", "/demo/pilot_plan.html"],
  ["public-architecture", "/demo/public_architecture.html"]
];

const viewports = [
  [1920, 1080],
  [1440, 900],
  [1024, 768],
  [390, 844]
];

for (const [width, height] of viewports) {
  test(`capture final release-candidate surfaces at ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    for (const [name, route] of surfaces) {
      await page.goto(route);
      await page.evaluate(() => document.fonts.ready);
      await expect(page.locator("h1")).toBeVisible();
      const overflow = await page.evaluate(() => document.body.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);
      await page.screenshot({
        path: path.join("reports", "screenshots", "final_polish_release_candidate", `${name}-${width}x${height}.png`),
        fullPage: true
      });
    }
  });
}
