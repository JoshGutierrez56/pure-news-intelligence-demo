(() => {
  "use strict";

  const PAGE_SIZE = 18;
  const STORAGE = { onboarding: "pni-onboarding-dismissed-v2", shortlist: "pni-shortlist-v2" };
  const CASES = { TFC: "01_TFC", KHC: "02_KHC", DLTR: "03_DLTR", DVN: "04_DVN", RH: "05_RH", FCX: "06_FCX", EFX: "07_EFX", CHE: "08_CHE" };
  const RESEARCH_IDEA_STATUS = {
    "412b08746bb0ed5a7745": { key: "available", label: "Research idea available", action: "View AI Research Hypothesis", href: "research_idea_rh.html" },
    "4784f62ad001b2a12af4": { key: "available", label: "Research idea available", action: "View AI Research Hypothesis", href: "research_idea_dvn.html" },
    "279e7d4e407851a19548": { key: "rejected", label: "Idea rejected after full evidence review", action: "View grounding rejection", href: "research_idea_efx.html" },
    "2f22dc2216c9df31d377": { key: "no-publishable", label: "No publishable research hypothesis" },
    "339fae2941721ee094b0": { key: "no-publishable", label: "No publishable research hypothesis" },
    "8d4598f4ea16f15c7048": { key: "no-publishable", label: "No publishable research hypothesis" },
    "8f5336b55618ffe68e8a": { key: "no-publishable", label: "No publishable research hypothesis" },
    "dbe75bc24f2888f4166a": { key: "no-publishable", label: "No publishable research hypothesis" }
  };
  const SECTORS = { TFC: "Financials", KHC: "Consumer Staples", DLTR: "Consumer Staples", DVN: "Energy", RH: "Consumer Discretionary", FCX: "Materials", EFX: "Industrials", CHE: "Health Care" };
  const materialityRank = { high: 3, medium: 2, low: 1 };
  const noveltyRank = { "genuinely new": 4, unclear: 3, "partially anticipated": 2, "previously disclosed": 1 };
  const state = { records: [], filtered: [], page: 1, view: "cards", saved: new Set(JSON.parse(localStorage.getItem(STORAGE.shortlist) || "[]")) };
  const byId = (id) => document.getElementById(id);
  const results = byId("change-results");
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[c]);
  const titleCase = (value) => String(value || "").replace(/\b\w/g, (letter) => letter.toUpperCase());
  const formatNumber = (value) => new Intl.NumberFormat("en-US").format(value);
  const sectionOf = (record) => record.title.split("·")[0].trim();
  const sectorOf = (record) => SECTORS[record.ticker] || "Not mapped";
  const isCase = (record) => Boolean(CASES[record.ticker]);
  const confidenceBand = (value) => value >= .8 ? "high" : value >= .7 ? "medium" : "low";
  const summaryText = (record) => record.summary.replace(/^(Changed passage now says:|Removed or softened language:)\s*/i, "");
  const noveltyOf = (record) => {
    const title = record.title.toLowerCase();
    if (title.includes("genuinely new")) return "genuinely new";
    if (title.includes("previously disclosed") || title.includes("previously covered in news")) return "previously disclosed";
    if (title.includes("partially anticipated")) return "partially anticipated";
    return "unclear";
  };
  const noveltyLabel = (value) => value === "genuinely new" ? "Genuinely new in study sources" : titleCase(value);
  const noveltyClass = (value) => ({ "genuinely new": "new", "previously disclosed": "previous", "partially anticipated": "partial", unclear: "unclear" })[value];
  const comparisonUrl = (record) => isCase(record) ? `company_comparison.html#case-${Object.keys(CASES).indexOf(record.ticker) + 1}` : `company_comparison.html?ticker=${encodeURIComponent(record.ticker)}`;
  const timelineUrl = (record) => isCase(record) ? `company_timeline.html#timeline-${Object.keys(CASES).indexOf(record.ticker) + 1}` : `company_timeline.html?ticker=${encodeURIComponent(record.ticker)}`;
  const researchIdeaStatus = (record) => RESEARCH_IDEA_STATUS[record.id] || { key: "not-reviewed", label: "Research idea not yet reviewed" };

  function cardHtml(record) {
    const novelty = noveltyOf(record);
    const direction = record.direction || "ambiguous";
    const saved = state.saved.has(record.id);
    const idea = researchIdeaStatus(record);
    return `<article class="change-card" data-record-id="${escapeHtml(record.id)}" data-attention="${escapeHtml(record.materiality)}" data-direction="${escapeHtml(direction)}">
      <div class="change-card-header">
        <div><div class="company-line"><span class="ticker">${escapeHtml(record.ticker)}</span> ${escapeHtml(record.issuer)}</div><div class="filing-meta">${escapeHtml(record.date)} · ${escapeHtml(sectionOf(record))} · ${escapeHtml(sectorOf(record))}</div></div>
        <span class="status-chip">Confidence ${Number(record.confidence).toFixed(3)}</span>
      </div>
      <div class="badge-row" aria-label="Change classifications">
        <span class="badge ${escapeHtml(record.materiality)}">${escapeHtml(titleCase(record.materiality))} materiality</span>
        <span class="badge ${noveltyClass(novelty)}">${escapeHtml(noveltyLabel(novelty))}</span>
        <span class="badge ${escapeHtml(direction)}">${escapeHtml(titleCase(direction))} direction</span>
        <span class="badge research-${escapeHtml(idea.key)}">${escapeHtml(idea.label)}</span>
      </div>
      <p class="label">Change category</p><h3>${escapeHtml(record.category)}</h3>
      <p class="change-summary clamped">${escapeHtml(summaryText(record))}</p>
      <details class="record-detail"><summary>Show full context</summary><div><p>${escapeHtml(summaryText(record))}</p><p><strong>Why it may matter:</strong> ${escapeHtml(record.why)}</p></div></details>
      <p class="why-brief"><strong>Why review:</strong> ${escapeHtml(record.why)}</p>
      <div class="card-actions">
        ${idea.href ? `<a class="button secondary" href="${idea.href}">${escapeHtml(idea.action)}</a>` : `<span class="research-idea-static-status">${escapeHtml(idea.label)}</span>`}
        <a href="${escapeHtml(record.url)}" target="_blank">Original SEC filing ↗</a>
        <a href="${comparisonUrl(record)}">Compare filings</a><a href="${timelineUrl(record)}">Timeline</a>
        ${isCase(record) ? `<a href="evidence_packets/${CASES[record.ticker]}.html">Evidence packet</a>` : ""}
        <button type="button" class="save-record secondary" data-save-record="${escapeHtml(record.id)}" aria-pressed="${saved}">${saved ? "Saved for discussion" : "Save for discussion"}</button>
      </div>
    </article>`;
  }

  function tableHtml(records) {
    return `<div class="table-wrap"><table class="cards-table"><caption>Filtered disclosure-change records</caption>
      <thead><tr><th>Company</th><th>Filing</th><th>Classification</th><th>Why review</th><th>Evidence</th></tr></thead>
      <tbody>${records.map((record) => {
        const novelty = noveltyOf(record);
        const idea = researchIdeaStatus(record);
        return `<tr><td><strong>${escapeHtml(record.ticker)} · ${escapeHtml(record.issuer)}</strong></td><td>${escapeHtml(record.date)}<br>${escapeHtml(sectionOf(record))}</td>
          <td>${escapeHtml(record.category)}<br><span class="badge ${escapeHtml(record.materiality)}">${escapeHtml(record.materiality)}</span> <span class="badge ${noveltyClass(novelty)}">${escapeHtml(noveltyLabel(novelty))}</span><br><span class="badge research-${escapeHtml(idea.key)}">${escapeHtml(idea.label)}</span></td>
          <td>${escapeHtml(record.why)}</td><td>${idea.href ? `<a href="${idea.href}">${escapeHtml(idea.action)}</a><br>` : ""}<a href="${escapeHtml(record.url)}" target="_blank">SEC filing</a><br>Confidence ${Number(record.confidence).toFixed(3)}<br><button type="button" class="save-record table-save" data-save-record="${escapeHtml(record.id)}" aria-pressed="${state.saved.has(record.id)}">${state.saved.has(record.id) ? "Saved" : "Save"}</button></td></tr>`;
      }).join("")}</tbody></table></div>`;
  }

  function selectedFilters() {
    return {
      search: byId("filter-search").value.trim().toLowerCase(), year: byId("filter-year").value,
      section: byId("filter-section").value, category: byId("filter-category").value,
      materiality: byId("filter-materiality").value, novelty: byId("filter-novelty").value,
      direction: byId("filter-direction").value, confidence: byId("filter-confidence").value,
      sector: byId("filter-sector").value, caseStatus: byId("filter-case").value,
      researchIdea: byId("filter-research-idea").value
    };
  }

  function sortRecords(records) {
    const order = byId("sort-order").value;
    return records.slice().sort((a, b) => {
      if (order === "date") return b.date.localeCompare(a.date) || a.id.localeCompare(b.id);
      if (order === "confidence") return b.confidence - a.confidence || a.id.localeCompare(b.id);
      if (order === "materiality") return materialityRank[b.materiality] - materialityRank[a.materiality] || b.confidence - a.confidence;
      if (order === "novelty") return noveltyRank[noveltyOf(b)] - noveltyRank[noveltyOf(a)] || b.confidence - a.confidence;
      const priority = (r) => materialityRank[r.materiality] * 100 + (r.direction === "negative" ? 20 : 0) + noveltyRank[noveltyOf(r)] * 5 + r.confidence;
      return priority(b) - priority(a) || b.date.localeCompare(a.date) || a.id.localeCompare(b.id);
    });
  }

  function applyFilters() {
    const f = selectedFilters();
    state.filtered = sortRecords(state.records.filter((r) => {
      const haystack = `${r.issuer} ${r.ticker}`.toLowerCase();
      return (!f.search || haystack.includes(f.search)) && (!f.year || r.date.startsWith(f.year))
        && (!f.section || sectionOf(r) === f.section) && (!f.category || r.category === f.category)
        && (!f.materiality || r.materiality === f.materiality) && (!f.novelty || noveltyOf(r) === f.novelty)
        && (!f.direction || r.direction === f.direction) && (!f.confidence || confidenceBand(r.confidence) === f.confidence)
        && (!f.sector || sectorOf(r) === f.sector) && (!f.caseStatus || (f.caseStatus === "yes") === isCase(r))
        && (!f.researchIdea || researchIdeaStatus(r).key === f.researchIdea);
    }));
    const labels = Object.entries(f).filter(([, value]) => value).map(([key, value]) => `<span class="filter-token">${escapeHtml(titleCase(key.replace("caseStatus", "case study").replace("researchIdea", "research idea")))}: ${escapeHtml(titleCase(value))}</span>`);
    byId("active-filters").innerHTML = labels.join("") || "None";
    render();
  }

  function render() {
    const pageCount = Math.max(1, Math.ceil(state.filtered.length / PAGE_SIZE));
    state.page = Math.min(Math.max(1, state.page), pageCount);
    const start = (state.page - 1) * PAGE_SIZE;
    const pageRecords = state.filtered.slice(start, start + PAGE_SIZE);
    results.className = state.view === "cards" ? "change-grid" : "";
    results.setAttribute("aria-busy", "false");
    results.innerHTML = pageRecords.length ? (state.view === "cards" ? pageRecords.map(cardHtml).join("") : tableHtml(pageRecords))
      : `<div class="empty-state"><h3>No changes match these filters</h3><p>Clear one or more filters to broaden the review queue.</p><button type="button" class="secondary" data-clear-empty>Clear all filters</button></div>`;
    results.querySelector("[data-clear-empty]")?.addEventListener("click", clearFilters);
    results.querySelectorAll("[data-save-record]").forEach((button) => button.addEventListener("click", () => toggleSaved(button.dataset.saveRecord)));
    byId("result-count").textContent = `${formatNumber(state.filtered.length)} of ${formatNumber(state.records.length)} changes · showing ${pageRecords.length ? `${formatNumber(start + 1)}–${formatNumber(start + pageRecords.length)}` : "0"}`;
    byId("page-status").textContent = `Page ${state.page} of ${pageCount}`;
    byId("previous-page").disabled = state.page === 1; byId("next-page").disabled = state.page === pageCount;
  }

  function renderShortlist() {
    const records = state.records.filter((r) => state.saved.has(r.id));
    byId("shortlist-count").textContent = String(records.length);
    byId("shortlist-items").innerHTML = records.length ? records.map((r) => `<span class="shortlist-token">${escapeHtml(r.ticker)} · ${escapeHtml(r.category)} <button type="button" aria-label="Remove ${escapeHtml(r.ticker)} from shortlist" data-remove-saved="${escapeHtml(r.id)}">×</button></span>`).join("") : `<span class="quiet">No saved records yet.</span>`;
    byId("shortlist-items").querySelectorAll("[data-remove-saved]").forEach((button) => button.addEventListener("click", () => toggleSaved(button.dataset.removeSaved)));
    byId("export-shortlist").disabled = !records.length; byId("clear-shortlist").disabled = !records.length;
  }

  function toggleSaved(id) {
    state.saved.has(id) ? state.saved.delete(id) : state.saved.add(id);
    localStorage.setItem(STORAGE.shortlist, JSON.stringify([...state.saved]));
    renderShortlist(); render();
  }

  function exportShortlist() {
    const records = state.records.filter((r) => state.saved.has(r.id));
    const lines = ["Pure News Intelligence — presentation shortlist", "Local export; analyst judgment required", ""];
    records.forEach((r, i) => lines.push(`${i + 1}. ${r.issuer} (${r.ticker})`, `${r.date} | ${sectionOf(r)} | ${r.category}`, `Materiality: ${r.materiality} | Novelty: ${noveltyOf(r)} | Confidence: ${Number(r.confidence).toFixed(3)}`, `Why review: ${r.why}`, `Source: ${r.url}`, ""));
    const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" }));
    const anchor = Object.assign(document.createElement("a"), { href: url, download: "pure-news-intelligence-shortlist.txt" });
    anchor.click(); URL.revokeObjectURL(url);
  }

  function clearFilters() {
    document.querySelectorAll("#filters input, #filters select").forEach((control) => { control.value = ""; });
    state.page = 1; applyFilters();
  }

  function guidedExample() {
    clearFilters(); byId("filter-search").value = "KHC"; state.page = 1; applyFilters();
    byId("ranked-changes").scrollIntoView({ behavior: "smooth", block: "start" });
    setTimeout(() => results.querySelector(".change-card")?.focus?.(), 220);
  }

  function populateSelect(id, values) {
    const select = byId(id); values.sort().forEach((value) => select.add(new Option(value, value)));
  }

  async function initialize() {
    try {
      const response = await fetch("data/changes.json", { cache: "force-cache" });
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const payload = await response.json();
      if (!payload.records || payload.records.length !== 995) throw new Error("Frozen record count did not reconcile to 995.");
      state.records = payload.records;
      populateSelect("filter-year", [...new Set(state.records.map((r) => r.date.slice(0, 4)))].reverse());
      populateSelect("filter-section", [...new Set(state.records.map(sectionOf))]);
      populateSelect("filter-category", [...new Set(state.records.map((r) => r.category))]);
      populateSelect("filter-direction", [...new Set(state.records.map((r) => r.direction))]);
      populateSelect("filter-sector", [...new Set(state.records.map(sectorOf))]);
      applyFilters(); renderShortlist();
      if (new URLSearchParams(location.search).get("guided") === "khc") guidedExample();
    } catch (error) {
      results.setAttribute("aria-busy", "false");
      results.innerHTML = `<div class="error-state"><h3>The frozen change set could not be loaded</h3><p>${escapeHtml(error.message)}</p><button type="button" class="secondary" data-retry>Retry</button></div>`;
      byId("result-count").textContent = "Change data unavailable";
      results.querySelector("[data-retry]")?.addEventListener("click", initialize);
    }
  }

  if (localStorage.getItem(STORAGE.onboarding) === "true") byId("feed-onboarding").hidden = true;
  document.querySelector("[data-dismiss-onboarding]")?.addEventListener("click", () => { byId("feed-onboarding").hidden = true; localStorage.setItem(STORAGE.onboarding, "true"); });
  document.querySelectorAll("[data-guided-example]").forEach((button) => button.addEventListener("click", guidedExample));
  document.querySelectorAll("#filters input, #filters select").forEach((control) => control.addEventListener(control.type === "search" ? "input" : "change", () => { state.page = 1; applyFilters(); }));
  byId("sort-order").addEventListener("change", () => { state.page = 1; applyFilters(); });
  byId("clear-filters").addEventListener("click", clearFilters);
  byId("previous-page").addEventListener("click", () => { state.page -= 1; render(); results.scrollIntoView({ behavior: "smooth", block: "start" }); });
  byId("next-page").addEventListener("click", () => { state.page += 1; render(); results.scrollIntoView({ behavior: "smooth", block: "start" }); });
  byId("card-view").addEventListener("click", () => { state.view = "cards"; byId("card-view").setAttribute("aria-pressed", "true"); byId("table-view").setAttribute("aria-pressed", "false"); render(); });
  byId("table-view").addEventListener("click", () => { state.view = "table"; byId("card-view").setAttribute("aria-pressed", "false"); byId("table-view").setAttribute("aria-pressed", "true"); render(); });
  byId("export-shortlist").addEventListener("click", exportShortlist);
  byId("clear-shortlist").addEventListener("click", () => { state.saved.clear(); localStorage.removeItem(STORAGE.shortlist); renderShortlist(); render(); });
  initialize();
})();
