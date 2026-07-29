const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const packetRoot = path.join(root, "demo", "data", "research_idea_packets", "v1");
const screenshotRoot = path.join(root, "artifacts", "screenshots", "research_idea_v1");
const index = JSON.parse(fs.readFileSync(path.join(packetRoot, "index.json"), "utf8"));
const entries = index.packets;
const packetById = new Map(entries.map((entry) => [
  entry.change_id,
  JSON.parse(fs.readFileSync(path.join(packetRoot, entry.path), "utf8"))
]));
const expectedCases = [
  ["dbe75bc24f2888f4166a", "TFC"],
  ["8f5336b55618ffe68e8a", "KHC"],
  ["339fae2941721ee094b0", "DLTR"],
  ["4784f62ad001b2a12af4", "DVN"],
  ["412b08746bb0ed5a7745", "RH"],
  ["8d4598f4ea16f15c7048", "FCX"],
  ["279e7d4e407851a19548", "EFX"],
  ["2f22dc2216c9df31d377", "CHE"]
];
const ids = Object.fromEntries(expectedCases.map(([id, ticker]) => [ticker, id]));
const detailHeadings = [
  "Source evidence",
  "What changed",
  "Novelty and materiality",
  "Economic mechanisms",
  "Falsifiable research hypotheses",
  "Analyst questions",
  "Affected entities",
  "Bull, base, and bear scenarios",
  "Illustrative Trade Hypothesis — Analyst Review Required",
  "Skeptical review",
  "Analyst disposition",
  "Save or export"
];
const disclaimer = "AI-generated research hypothesis based on the cited evidence. It is not a fact, personalized investment advice, or a validated trading signal. Analyst review is required.";
const viewports = [
  { width: 1920, height: 1080 },
  { width: 1440, height: 900 },
  { width: 1024, height: 768 },
  { width: 390, height: 844 }
];
const reviewSurfaces = [
  ["strongest-grounded-hold-efx", `/demo/research_idea.html?change_id=${ids.EFX}`, "#research-idea-detail[aria-busy=false]"],
  ["rejected-khc", `/demo/research_idea.html?change_id=${ids.KHC}`, "#research-idea-detail[aria-busy=false]"],
  ["no-action-hold-che", `/demo/research_idea.html?change_id=${ids.CHE}`, "#research-idea-detail[aria-busy=false]"],
  ["gallery", "/demo/research_idea_gallery.html", "#research-idea-gallery[aria-busy=false]"],
  ["methodology", "/demo/research_idea_methodology.html", "#research-idea-guided-example[aria-busy=false]"]
];

fs.mkdirSync(screenshotRoot, { recursive: true });

function canonicalJson(value) {
  if (value && typeof value === "object" && Object.keys(value).length === 1 && typeof value.__jsonNumber === "string") {
    return value.__jsonNumber;
  }
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function sha256(value) {
  return crypto.createHash("sha256").update(value, "utf8").digest("hex");
}

function losslessPacket(filePath) {
  const packet = JSON.parse(fs.readFileSync(filePath, "utf8"), (_key, value, context) => (
    typeof value === "number" ? { __jsonNumber: context.source } : value
  ));
  packet.packet_hash = "0".repeat(64);
  return packet;
}

function monitorPage(page) {
  const issues = [];
  page.on("console", (message) => {
    if (message.type() === "error") issues.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => issues.push(`pageerror: ${error.message}`));
  page.on("requestfailed", (request) => {
    issues.push(`requestfailed: ${request.method()} ${request.url()} ${request.failure()?.errorText || ""}`);
  });
  page.on("response", (response) => {
    if (response.url().startsWith("http://127.0.0.1:4173/") && response.status() >= 400) {
      issues.push(`response: ${response.status()} ${response.url()}`);
    }
  });
  return issues;
}

async function openDetail(page, changeId) {
  await page.goto(`/demo/research_idea.html?change_id=${changeId}`);
  await expect(page.locator("#research-idea-detail")).toHaveAttribute("aria-busy", "false");
}

async function noHorizontalOverflow(page, label) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth
  }));
  expect(dimensions.scrollWidth, label).toBeLessThanOrEqual(dimensions.clientWidth + 1);
}

function collectObjectKeys(value, output = []) {
  if (Array.isArray(value)) {
    value.forEach((item) => collectObjectKeys(item, output));
  } else if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      output.push(key);
      collectObjectKeys(child, output);
    }
  }
  return output;
}

test("final packet index reconciles to the honest eight-packet hold/rejection outcome", async () => {
  expect(index.index_version).toBe("1.0");
  expect(index.packet_version).toBe("1.0");
  expect(index.packet_count).toBe(8);
  expect(entries).toHaveLength(8);
  expect(new Set(entries.map((entry) => entry.change_id)).size).toBe(8);
  expect(entries.map((entry) => [entry.change_id, entry.ticker])).toEqual(expectedCases);

  const indexPreimage = { ...index };
  delete indexPreimage.index_sha256;
  expect(index.index_sha256).toBe(sha256(canonicalJson(indexPreimage)));

  const counts = { PUBLISHABLE: 0, HOLD: 0, REJECTED_BY_SKEPTIC: 0 };
  for (const entry of entries) {
    const packet = packetById.get(entry.change_id);
    expect(entry.path).toBe(`${entry.change_id}.json`);
    expect(packet.change_id).toBe(entry.change_id);
    expect(packet.packet_id).toBe(entry.packet_id);
    expect(packet.packet_hash).toBe(entry.packet_hash);
    expect(packet.packet_hash).toBe(sha256(canonicalJson(losslessPacket(path.join(packetRoot, entry.path)))));
    expect(packet.packet_status).toBe(entry.packet_status);
    expect(packet.ticker).toBe(entry.ticker);
    expect(packet.issuer).toBe(entry.issuer);
    expect(packet.filing_date).toBe(entry.filing_date);
    expect(packet.frozen_classification.category).toBe(entry.category);
    expect(packet.frozen_classification.materiality).toBe(entry.materiality);
    expect(packet.skeptical_review.final_review_status).toBe(entry.idea_review_status);
    expect(packet.illustrative_trade_hypothesis.trade_readiness).toBe(entry.trade_readiness);
    expect(packet.analyst_disposition.status).toBe("UNREVIEWED");
    expect(packet.disclaimer).toBe(disclaimer);
    expect(collectObjectKeys(packet)).not.toContain("outcome");
    expect(collectObjectKeys(packet)).not.toContain("post_filing_news");
    if (packet.packet_status.startsWith("HOLD_")) counts.HOLD += 1;
    else counts[packet.packet_status] += 1;
  }
  expect(counts).toEqual({ PUBLISHABLE: 0, HOLD: 4, REJECTED_BY_SKEPTIC: 4 });
});

test("ranked cards expose only frozen public V2 statuses and no live generation", async ({ page }) => {
  const issues = monitorPage(page);
  await page.goto("/demo/ranked_change_feed.html");
  await expect(page.locator(".change-card").first()).toBeVisible();
  const dismiss = page.getByRole("button", { name: "Dismiss" });
  if (await dismiss.isVisible()) await dismiss.click();

  for (const [changeId, ticker] of expectedCases) {
    await page.locator("#filter-search").fill(packetById.get(changeId).issuer);
    const card = page.locator(`.change-card[data-record-id="${changeId}"]`);
    await expect(card).toBeVisible();
    if (ticker === "RH" || ticker === "DVN") {
      const link = card.getByRole("link", { name: "View AI Research Hypothesis" });
      await expect(link).toHaveAttribute("href", `research_idea_${ticker.toLowerCase()}.html`);
    } else if (ticker === "EFX") {
      await expect(card.getByRole("link", { name: "View grounding rejection" })).toHaveAttribute("href", "research_idea_efx.html");
    } else {
      await expect(card.getByText("No publishable research hypothesis", { exact: true }).first()).toBeVisible();
    }
    await expect(card.getByText("Generate Research Idea", { exact: true })).toHaveCount(0);
  }

  const missingId = "90dfbd96252aa63be9ed";
  await page.locator("#filter-search").fill("UNP");
  const missingCard = page.locator(`.change-card[data-record-id="${missingId}"]`);
  await expect(missingCard).toBeVisible();
  await expect(missingCard.getByText("Research idea not yet reviewed", { exact: true }).first()).toBeVisible();
  await expect(missingCard.getByText("Generate Research Idea", { exact: true })).toHaveCount(0);
  expect(issues).toEqual([]);
});

test("EFX renders a fully inspectable twelve-stage packet despite skeptic hold", async ({ page }) => {
  const issues = monitorPage(page);
  await openDetail(page, ids.EFX);
  await expect(page.getByRole("heading", { level: 1, name: /EQUIFAX INC \(EFX\)/ })).toBeVisible();
  await expect(page.locator("#idea-packet-status")).toHaveText("HOLD_INSUFFICIENT_EVIDENCE");
  await expect(page.locator("#idea-review-status")).toHaveText("HOLD_INSUFFICIENT_EVIDENCE");
  await expect(page.locator(".ri-disclaimer")).toContainText(disclaimer);
  expect(await page.locator("#research-idea-detail > section .ri-section-heading h2").allTextContents()).toEqual(detailHeadings);
  await expect(page.getByLabel("Prior filing excerpt")).not.toBeEmpty();
  await expect(page.getByLabel("Current filing excerpt")).not.toBeEmpty();
  await expect(page.locator(".ri-hypothesis-card")).toHaveCount(2);
  await expect(page.locator(".ri-hypothesis-card").first().getByRole("heading", { level: 3 })).not.toBeEmpty();
  await expect(page.locator(".ri-review-summary")).toContainText("Critical grounding defect");
  await expect(page.locator(".ri-review-summary")).toContainText("Yes");
  await expect(page.getByText("No ex-post outcome is loaded into this research idea.", { exact: false })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Illustrative Trade Hypothesis — Analyst Review Required" })).toBeVisible();
  await expect(page.locator(".ri-trade-status")).toContainText("NOT_READY");
  await expect(page.locator(".ri-guardrails")).toContainText("No position size generated: Yes");
  expect(issues).toEqual([]);
});

test("rejected and held packets preserve skeptic objections and withhold actionable views", async ({ page }) => {
  const issues = monitorPage(page);
  await openDetail(page, ids.KHC);
  await expect(page.locator("#idea-packet-status")).toHaveText("REJECTED_BY_SKEPTIC");
  await expect(page.locator("#idea-review-status")).toHaveText("REJECTED_BY_SKEPTIC");
  await expect(page.locator(".ri-review-summary")).toContainText("Critical grounding defect");
  await expect(page.locator(".ri-review-summary")).toContainText("Yes");
  await expect(page.locator(".ri-trade-status")).toContainText("insufficient evidence");
  await expect(page.locator(".ri-trade-status")).toContainText("NOT_READY");

  await openDetail(page, ids.CHE);
  await expect(page.locator("#idea-packet-status")).toHaveText("HOLD_INSUFFICIENT_EVIDENCE");
  await expect(page.locator("#idea-review-status")).toHaveText("HOLD_INSUFFICIENT_EVIDENCE");
  await expect(page.getByRole("heading", { name: "No sufficiently grounded mechanism was published" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "No publishable research hypothesis" })).toBeVisible();
  await expect(page.getByText("No sufficiently grounded research or trade hypothesis can be generated from this disclosure change.", { exact: true })).toBeVisible();
  await expect(page.locator(".ri-trade-status")).toContainText("insufficient evidence");
  await expect(page.locator(".ri-trade-status")).toContainText("NOT_READY");
  expect(issues).toEqual([]);
});

test("gallery filters every required dimension and applies deterministic sort modes", async ({ page }) => {
  const issues = monitorPage(page);
  await page.goto("/demo/research_idea_gallery.html");
  await expect(page.locator("#research-idea-gallery")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator("#ri-gallery-count")).toHaveText("8 of 8 validated packets");
  await expect(page.locator(".ri-gallery-card")).toHaveCount(8);

  const clear = async () => {
    await page.locator("#ri-clear-filters").click();
    await expect(page.locator("#ri-gallery-count")).toHaveText("8 of 8 validated packets");
  };
  const filter = async (selector, value, expectedCount, expectedTicker) => {
    const control = page.locator(selector);
    if ((await control.getAttribute("type")) === "search") await control.fill(value);
    else await control.selectOption(value);
    await expect(page.locator("#ri-gallery-count")).toHaveText(`${expectedCount} of 8 validated packets`);
    await expect(page.locator(".ri-gallery-card")).toHaveCount(expectedCount);
    if (expectedTicker) await expect(page.locator(".ri-gallery-card").first()).toContainText(expectedTicker);
    await clear();
  };

  await filter("#ri-filter-issuer", "Equifax", 1, "EFX");
  await filter("#ri-filter-year", "2021", 1, "FCX");
  await filter("#ri-filter-category", "Litigation or regulatory escalation", 1, "EFX");
  await filter("#ri-filter-novelty", "genuinely new in the 10-K", 4);
  await filter("#ri-filter-materiality", "medium", 1, "CHE");
  await filter("#ri-filter-asset", "no instrument identified", 8);
  await filter("#ri-filter-horizon", "1-3 quarters", 1, "EFX");
  await filter("#ri-filter-review", "REJECTED_BY_SKEPTIC", 4);
  await filter("#ri-filter-readiness", "NOT_READY", 8);

  const firstTickerForSort = async (sort, ticker) => {
    await page.locator("#ri-gallery-sort").selectOption(sort);
    await expect(page.locator(".ri-gallery-card").first()).toContainText(ticker);
  };
  await firstTickerForSort("evidence", "EFX");
  await firstTickerForSort("testability", "KHC");
  await firstTickerForSort("materiality", "RH");
  await firstTickerForSort("date", "RH");
  await firstTickerForSort("disposition", "EFX");
  expect(issues).toEqual([]);
});

test("all five analyst dispositions, notes, and save action persist only in browser storage", async ({ page }) => {
  const sourcePath = path.join(packetRoot, `${ids.EFX}.json`);
  const sourceBefore = fs.readFileSync(sourcePath);
  await openDetail(page, ids.EFX);
  await page.evaluate(() => localStorage.removeItem("pni-research-idea-dispositions-v1"));
  await page.reload();
  await expect(page.locator("#research-idea-detail")).toHaveAttribute("aria-busy", "false");

  const actions = [
    ["Accept", "ACCEPTED"],
    ["Edit", "ACCEPTED_WITH_EDITS"],
    ["Reject", "REJECTED"],
    ["Escalate", "ESCALATED"],
    ["Save for discussion", "SAVED_FOR_DISCUSSION"]
  ];
  for (const [label, status] of actions) {
    await page.getByRole("button", { name: label, exact: true }).click();
    await expect(page.locator("#ri-current-disposition")).toHaveText(status);
    await expect(page.getByRole("button", { name: label, exact: true })).toHaveAttribute("aria-pressed", "true");
    const stored = await page.evaluate((changeId) => JSON.parse(localStorage.getItem("pni-research-idea-dispositions-v1"))[changeId], ids.EFX);
    expect(stored.status).toBe(status);
    expect(stored.saved_locally_only).toBe(true);
    await page.reload();
    await expect(page.locator("#research-idea-detail")).toHaveAttribute("aria-busy", "false");
    await expect(page.locator("#ri-current-disposition")).toHaveText(status);
  }

  const note = "Confirm reserve roll-forward and settlement-fund claims before discussion.";
  await page.locator("#ri-analyst-notes").fill(note);
  await page.getByRole("button", { name: "Save local review", exact: true }).click();
  await page.reload();
  await expect(page.locator("#research-idea-detail")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator("#ri-analyst-notes")).toHaveValue(note);
  await expect(page.locator("#ri-current-disposition")).toHaveText("SAVED_FOR_DISCUSSION");
  expect(fs.readFileSync(sourcePath)).toEqual(sourceBefore);
});

test("packet export is deterministic, bounded, and preserves an immutable source packet", async ({ page }) => {
  await page.addInitScript(({ changeId }) => {
    localStorage.setItem("pni-research-idea-dispositions-v1", JSON.stringify({
      [changeId]: {
        status: "ESCALATED",
        analyst_notes: "Fixed analyst overlay for deterministic export.",
        edited_fields: ["/analyst_disposition/analyst_notes"],
        review_timestamp: "2026-07-28T20:00:00.000Z",
        saved_locally_only: true
      }
    }));
  }, { changeId: ids.EFX });
  await openDetail(page, ids.EFX);

  const exportOnce = async () => {
    const downloadPromise = page.waitForEvent("download");
    await page.locator("#ri-export-packet").click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(`research-idea-${ids.EFX}.json`);
    return fs.readFileSync(await download.path());
  };
  const first = await exportOnce();
  const second = await exportOnce();
  expect(second).toEqual(first);
  const exported = JSON.parse(first.toString("utf8"));
  expect(Object.keys(exported)).toEqual(["analyst_overlay", "export_version", "source_packet"]);
  expect(exported.export_version).toBe("1.0");
  expect(exported.analyst_overlay.status).toBe("ESCALATED");
  expect(exported.analyst_overlay.saved_locally_only).toBe(true);
  expect(exported.source_packet).toEqual(packetById.get(ids.EFX));
  expect(exported.source_packet.analyst_disposition.status).toBe("UNREVIEWED");
  expect(collectObjectKeys(exported)).not.toContain("outcome");
  expect(collectObjectKeys(exported)).not.toContain("post_filing_news");
});

test("research-idea routes and data loads remain GitHub Pages-relative", async ({ page }) => {
  const productionFiles = [
    "demo/research_idea.html",
    "demo/research_idea_gallery.html",
    "demo/research_idea_methodology.html"
  ];
  for (const relative of productionFiles) {
    const html = fs.readFileSync(path.join(root, relative), "utf8");
    const localTargets = [...html.matchAll(/\b(?:href|src)="([^"]+)"/g)].map((match) => match[1])
      .filter((target) => !target.startsWith("#") && !target.startsWith("http") && !target.startsWith("mailto:") && !target.startsWith("data:"));
    expect(localTargets.every((target) => !target.startsWith("/")), `${relative}: root-absolute target`).toBe(true);
  }

  const requests = [];
  page.on("request", (request) => {
    if (request.url().startsWith("http://127.0.0.1:4173/")) requests.push(new URL(request.url()).pathname);
  });
  await openDetail(page, ids.KHC);
  await expect(page.getByRole("link", { name: "Browse idea gallery" })).toHaveAttribute("href", "research_idea_gallery.html");
  await expect(page.getByRole("link", { name: "Pure News Intelligence" })).toHaveAttribute("href", "../index.html");
  expect(requests).toContain("/demo/assets/research_idea.js");
  expect(requests).toContain("/demo/data/research_idea_packets/v1/index.json");
  expect(requests).toContain(`/demo/data/research_idea_packets/v1/${ids.KHC}.json`);
  expect(requests.every((requestPath) => !requestPath.includes("//"))).toBe(true);
});

test("research-idea controls have keyboard names, visible focus, and no serious axe findings", async ({ page }) => {
  const routes = [
    `/demo/research_idea.html?change_id=${ids.EFX}`,
    `/demo/research_idea.html?change_id=${ids.DVN}`,
    `/demo/research_idea.html?change_id=${ids.TFC}`,
    "/demo/research_idea_gallery.html",
    "/demo/research_idea_methodology.html"
  ];
  for (const route of routes) {
    await page.goto(route);
    if (route.includes("research_idea.html")) {
      await expect(page.locator("#research-idea-detail")).toHaveAttribute("aria-busy", "false");
    } else if (route.includes("gallery")) {
      await expect(page.locator("#research-idea-gallery")).toHaveAttribute("aria-busy", "false");
    } else {
      await expect(page.locator("#research-idea-guided-example")).toHaveAttribute("aria-busy", "false");
    }
    const unnamed = await page.locator("button, input, select, textarea").evaluateAll((controls) => controls.filter((control) => {
      const label = control.labels?.[0]?.textContent?.trim();
      return !(label || control.getAttribute("aria-label") || control.getAttribute("aria-labelledby") || control.textContent.trim());
    }).map((control) => `${control.tagName}#${control.id}`));
    expect(unnamed, route).toEqual([]);
    const results = await new AxeBuilder({ page }).analyze();
    const severe = results.violations.filter((violation) => ["serious", "critical"].includes(violation.impact));
    expect(severe, `${route}: ${severe.map((violation) => violation.id).join(", ")}`).toEqual([]);
  }

  await page.goto(`/demo/research_idea.html?change_id=${ids.EFX}`);
  await expect(page.locator("#research-idea-detail")).toHaveAttribute("aria-busy", "false");
  await page.keyboard.press("Tab");
  await expect(page.locator(".skip-link")).toBeFocused();
  const focus = await page.locator(":focus").evaluate((element) => {
    const style = getComputedStyle(element);
    return { outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth };
  });
  expect(focus.outlineStyle).not.toBe("none");
  expect(focus.outlineWidth).not.toBe("0px");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
  const accept = page.getByRole("button", { name: "Accept", exact: true });
  await accept.focus();
  await expect(accept).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#ri-current-disposition")).toHaveText("ACCEPTED");
});

test("all research-idea surfaces load without console, page, request, or response errors", async ({ page }) => {
  const issues = monitorPage(page);
  for (const [, route, ready] of reviewSurfaces) {
    await page.goto(route);
    await expect(page.locator(ready)).toBeVisible();
  }
  await page.goto("/demo/research_idea.html?change_id=not-indexed");
  await expect(page.getByRole("heading", { name: "Research idea not yet generated for this record." })).toBeVisible();
  expect(issues).toEqual([]);
});

test("all eight packet details render at every required viewport without overflow", async ({ page }) => {
  const issues = monitorPage(page);
  await page.addInitScript(() => localStorage.clear());
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.emulateMedia({ reducedMotion: "reduce" });
    for (const [changeId] of expectedCases) {
      await openDetail(page, changeId);
      expect(
        await page.locator("#research-idea-detail > section .ri-section-heading h2").allTextContents(),
        `${changeId} section order at ${viewport.width}x${viewport.height}`
      ).toEqual(detailHeadings);
      await expect(page.locator(".ri-disclaimer")).toContainText(disclaimer);
      await noHorizontalOverflow(
        page,
        `${changeId} at ${viewport.width}x${viewport.height}`
      );
    }
  }
  expect(issues).toEqual([]);
});

test.describe("deterministic responsive review screenshots", () => {
  test.describe.configure({ mode: "serial" });

  for (const viewport of viewports) {
    test(`captures five review surfaces with no overflow at ${viewport.width}x${viewport.height}`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.addInitScript(() => localStorage.clear());
      for (const [name, route, ready] of reviewSurfaces) {
        const issues = monitorPage(page);
        await page.goto(route);
        await expect(page.locator(ready)).toBeVisible();
        await page.evaluate(() => document.fonts?.ready);
        await noHorizontalOverflow(page, `${name} at ${viewport.width}x${viewport.height}`);
        expect(issues, name).toEqual([]);
        await page.screenshot({
          path: path.join(screenshotRoot, `${name}-${viewport.width}x${viewport.height}.png`),
          fullPage: false,
          animations: "disabled",
          caret: "hide"
        });
      }
    });
  }
});
