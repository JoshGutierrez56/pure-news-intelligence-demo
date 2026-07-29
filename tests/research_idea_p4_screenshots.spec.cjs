const { test, expect } = require("@playwright/test");
const fs = require("node:fs");
const path = require("node:path");

const output = path.resolve(__dirname, "..", "reports", "screenshots", "research_idea_public_demo_p4");
fs.mkdirSync(output, { recursive: true });

async function capture(page, route, filename, options = {}) {
  await page.goto(route);
  await page.waitForLoadState("networkidle");
  if (options.ready) await options.ready(page);
  await page.waitForTimeout(450);
  const widths = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
  expect(widths[0], filename).toBeLessThanOrEqual(widths[1] + 1);
  await page.screenshot({ path: path.join(output, filename), fullPage: options.fullPage ?? true });
}

test("capture P4 desktop integration review set", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await capture(page, "/", "homepage-1920x1080.png");
  await capture(page, "/demo/ranked_change_feed.html", "ranked-feed-research-status-1920x1080.png", {
    ready: async (target) => {
      await target.locator("#filter-search").fill("RH");
      await expect(target.locator('.change-card[data-record-id="412b08746bb0ed5a7745"]').getByText("Research idea available", { exact: true }).first()).toBeVisible();
    }
  });
  await capture(page, "/demo/research_results.html", "research-results-1920x1080.png");
  await capture(page, "/demo/methodology.html", "methodology-1920x1080.png");
  await capture(page, "/demo/innovation_framework.html", "innovation-framework-1920x1080.png");
  await capture(page, "/demo/pilot_plan.html", "pilot-plan-1920x1080.png");

  await capture(page, "/demo/professor_presentation.html", "professor-research-question-1920x1080.png", {
    fullPage: false,
    ready: async (target) => {
      await target.getByRole("button", { name: "Present" }).click();
      for (let index = 0; index < 8; index += 1) await target.keyboard.press("ArrowRight");
      await expect(target.locator(".story-section.is-current")).toHaveAttribute("id", "slide-research-question");
    }
  });
  await page.keyboard.press("ArrowRight");
  await expect(page.locator(".story-section.is-current")).toHaveAttribute("id", "slide-safe-failure");
  await page.screenshot({ path: path.join(output, "professor-efx-safe-failure-1920x1080.png") });
});

test("capture P4 mobile and print review set", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await capture(page, "/", "homepage-390x844.png");
  await capture(page, "/demo/research_idea_rh.html", "rh-390x844.png");
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.emulateMedia({ media: "print" });
  await capture(page, "/demo/research_idea_rh.html", "rh-print-1920x1080.png");
});
