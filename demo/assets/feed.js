(() => {
  "use strict";

  const PAGE_SIZE = 24;
  const CASES = {
    TFC: "01_TFC", KHC: "02_KHC", DLTR: "03_DLTR", DVN: "04_DVN",
    RH: "05_RH", FCX: "06_FCX", EFX: "07_EFX", CHE: "08_CHE"
  };
  const SECTORS = {
    TFC: "Financials", KHC: "Consumer Staples", DLTR: "Consumer Staples", DVN: "Energy",
    RH: "Consumer Discretionary", FCX: "Materials", EFX: "Industrials", CHE: "Health Care"
  };
  const materialityRank = { high: 3, medium: 2, low: 1 };
  const noveltyRank = { "genuinely new": 4, unclear: 3, "partially anticipated": 2, "previously disclosed": 1 };
  const state = { records: [], filtered: [], page: 1, view: "cards" };
  const byId = (id) => document.getElementById(id);
  const results = byId("change-results");

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[character]);
  const formatNumber = (value) => new Intl.NumberFormat("en-US").format(value);
  const titleCase = (value) => String(value || "").replace(/\b\w/g, (letter) => letter.toUpperCase());
  const noveltyOf = (record) => {
    const title = record.title.toLowerCase();
    if (title.includes("genuinely new")) return "genuinely new";
    if (title.includes("previously disclosed") || title.includes("previously covered in news")) return "previously disclosed";
    if (title.includes("partially anticipated")) return "partially anticipated";
    return "unclear";
  };
  const sectionOf = (record) => record.title.split("·")[0].trim();
  const confidenceBand = (value) => value >= .8 ? "high" : value >= .7 ? "medium" : "low";
  const sectorOf = (record) => SECTORS[record.ticker] || "Not mapped";
  const isCase = (record) => Boolean(CASES[record.ticker]);
  const summaryText = (record) => record.summary.replace(/^(Changed passage now says:|Removed or softened language:)\s*/i, "");
  const noveltyLabel = (value) => value === "genuinely new" ? "Genuinely new in bounded corpus" : titleCase(value);
  const noveltyClass = (value) => ({
    "genuinely new": "new", "previously disclosed": "previous", "partially anticipated": "partial", unclear: "unclear"
  })[value];

  function comparisonUrl(record) {
    return isCase(record) ? `company_comparison.html#case-${Object.keys(CASES).indexOf(record.ticker) + 1}` : `company_comparison.html?ticker=${encodeURIComponent(record.ticker)}`;
  }

  function timelineUrl(record) {
    return isCase(record) ? `company_timeline.html#timeline-${Object.keys(CASES).indexOf(record.ticker) + 1}` : `company_timeline.html?ticker=${encodeURIComponent(record.ticker)}`;
  }

  function cardHtml(record) {
    const novelty = noveltyOf(record);
    const direction = record.direction || "ambiguous";
    return `<article class="change-card" data-attention="${escapeHtml(record.materiality)}" data-direction="${escapeHtml(direction)}">
      <div class="change-card-header">
        <div>
          <div class="company-line">${escapeHtml(record.issuer)} <span class="ticker">(${escapeHtml(record.ticker)})</span></div>
          <div class="filing-meta">${escapeHtml(record.date)} · ${escapeHtml(sectionOf(record))} · ${escapeHtml(sectorOf(record))}</div>
        </div>
        <span class="status-chip">Confidence ${Number(record.confidence).toFixed(3)}</span>
      </div>
      <div class="badge-row" aria-label="Change classifications">
        <span class="badge ${escapeHtml(record.materiality)}">${escapeHtml(titleCase(record.materiality))} materiality</span>
        <span class="badge ${noveltyClass(novelty)}">${escapeHtml(noveltyLabel(novelty))}</span>
        <span class="badge ${escapeHtml(direction)}">${escapeHtml(titleCase(direction))} direction</span>
      </div>
      <p class="label">Change category</p>
      <h3>${escapeHtml(record.category)}</h3>
      <p class="change-summary">${escapeHtml(summaryText(record))}</p>
      <div class="why-box"><strong>Why it may matter</strong>${escapeHtml(record.why)}</div>
      <div class="card-actions">
        <a href="${escapeHtml(record.url)}" target="_blank">↗ Original SEC filing</a>
        <a href="${comparisonUrl(record)}">Compare filings</a>
        <a href="${timelineUrl(record)}">Company timeline</a>
        ${isCase(record) ? `<a href="evidence_packets/${CASES[record.ticker]}.html">Evidence packet</a>` : ""}
      </div>
    </article>`;
  }

  function tableHtml(records) {
    return `<div class="table-wrap"><table class="cards-table">
      <thead><tr><th>Company</th><th>Filing</th><th>Classification</th><th>Summary and relevance</th><th>Evidence</th></tr></thead>
      <tbody>${records.map((record) => {
        const novelty = noveltyOf(record);
        return `<tr>
          <td><strong>${escapeHtml(record.issuer)}</strong><br>${escapeHtml(record.ticker)}</td>
          <td>${escapeHtml(record.date)}<br>${escapeHtml(sectionOf(record))}</td>
          <td>${escapeHtml(record.category)}<br><span class="badge ${escapeHtml(record.materiality)}">${escapeHtml(record.materiality)}</span> <span class="badge ${noveltyClass(novelty)}">${escapeHtml(noveltyLabel(novelty))}</span></td>
          <td>${escapeHtml(summaryText(record))}<br><small><strong>Why it may matter:</strong> ${escapeHtml(record.why)}</small></td>
          <td><a href="${escapeHtml(record.url)}" target="_blank">SEC filing</a><br>Confidence ${Number(record.confidence).toFixed(3)}</td>
        </tr>`;
      }).join("")}</tbody>
    </table></div>`;
  }

  function selectedFilters() {
    return {
      search: byId("filter-search").value.trim().toLowerCase(),
      year: byId("filter-year").value,
      section: byId("filter-section").value,
      category: byId("filter-category").value,
      materiality: byId("filter-materiality").value,
      novelty: byId("filter-novelty").value,
      direction: byId("filter-direction").value,
      confidence: byId("filter-confidence").value,
      sector: byId("filter-sector").value,
      caseStatus: byId("filter-case").value
    };
  }

  function sortRecords(records) {
    const order = byId("sort-order").value;
    return records.slice().sort((a, b) => {
      if (order === "date") return b.date.localeCompare(a.date) || a.id.localeCompare(b.id);
      if (order === "confidence") return b.confidence - a.confidence || a.id.localeCompare(b.id);
      if (order === "materiality") return materialityRank[b.materiality] - materialityRank[a.materiality] || b.confidence - a.confidence;
      if (order === "novelty") return noveltyRank[noveltyOf(b)] - noveltyRank[noveltyOf(a)] || b.confidence - a.confidence;
      const priority = (record) => materialityRank[record.materiality] * 100 + (record.direction === "negative" ? 20 : 0) + noveltyRank[noveltyOf(record)] * 5 + record.confidence;
      return priority(b) - priority(a) || b.date.localeCompare(a.date) || a.id.localeCompare(b.id);
    });
  }

  function applyFilters() {
    const filter = selectedFilters();
    state.filtered = sortRecords(state.records.filter((record) => {
      const haystack = `${record.issuer} ${record.ticker}`.toLowerCase();
      return (!filter.search || haystack.includes(filter.search))
        && (!filter.year || record.date.startsWith(filter.year))
        && (!filter.section || sectionOf(record) === filter.section)
        && (!filter.category || record.category === filter.category)
        && (!filter.materiality || record.materiality === filter.materiality)
        && (!filter.novelty || noveltyOf(record) === filter.novelty)
        && (!filter.direction || record.direction === filter.direction)
        && (!filter.confidence || confidenceBand(record.confidence) === filter.confidence)
        && (!filter.sector || sectorOf(record) === filter.sector)
        && (!filter.caseStatus || (filter.caseStatus === "yes") === isCase(record));
    }));
    renderActiveFilters(filter);
    render();
  }

  function renderActiveFilters(filter) {
    const labels = Object.entries(filter)
      .filter(([, value]) => value)
      .map(([key, value]) => `<span class="filter-token">${escapeHtml(titleCase(key.replace("caseStatus", "case study")))}: ${escapeHtml(titleCase(value))}</span>`);
    byId("active-filters").innerHTML = labels.join("") || "None";
  }

  function render() {
    const pageCount = Math.max(1, Math.ceil(state.filtered.length / PAGE_SIZE));
    state.page = Math.min(Math.max(1, state.page), pageCount);
    const start = (state.page - 1) * PAGE_SIZE;
    const pageRecords = state.filtered.slice(start, start + PAGE_SIZE);
    results.className = state.view === "cards" ? "change-grid" : "";
    results.setAttribute("aria-busy", "false");
    results.innerHTML = pageRecords.length
      ? (state.view === "cards" ? pageRecords.map(cardHtml).join("") : tableHtml(pageRecords))
      : `<div class="empty-state"><h3>No changes match these filters</h3><p>Clear one or more filters to broaden the review queue.</p><button type="button" class="secondary" data-clear-empty>Clear all filters</button></div>`;
    results.querySelector("[data-clear-empty]")?.addEventListener("click", clearFilters);
    byId("result-count").textContent = `${formatNumber(state.filtered.length)} of ${formatNumber(state.records.length)} changes · showing ${pageRecords.length ? `${formatNumber(start + 1)}–${formatNumber(start + pageRecords.length)}` : "0"}`;
    byId("page-status").textContent = `Page ${state.page} of ${pageCount}`;
    byId("previous-page").disabled = state.page === 1;
    byId("next-page").disabled = state.page === pageCount;
  }

  function populateSelect(id, values) {
    const select = byId(id);
    values.sort().forEach((value) => select.add(new Option(value, value)));
  }

  function clearFilters() {
    document.querySelectorAll("#filters input, #filters select").forEach((control) => { control.value = ""; });
    state.page = 1;
    applyFilters();
  }

  async function initialize() {
    try {
      const response = await fetch("data/changes.json", { cache: "force-cache" });
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const payload = await response.json();
      if (!payload.records || payload.records.length !== 995) throw new Error("Frozen record count did not reconcile to 995.");
      state.records = payload.records;
      populateSelect("filter-year", [...new Set(state.records.map((record) => record.date.slice(0, 4)))].reverse());
      populateSelect("filter-section", [...new Set(state.records.map(sectionOf))]);
      populateSelect("filter-category", [...new Set(state.records.map((record) => record.category))]);
      populateSelect("filter-direction", [...new Set(state.records.map((record) => record.direction))]);
      populateSelect("filter-sector", [...new Set(state.records.map(sectorOf))]);
      applyFilters();
    } catch (error) {
      results.setAttribute("aria-busy", "false");
      results.innerHTML = `<div class="error-state"><h3>The frozen change set could not be loaded</h3><p>${escapeHtml(error.message)}</p><button type="button" class="secondary" data-retry>Retry</button></div>`;
      byId("result-count").textContent = "Change data unavailable";
      results.querySelector("[data-retry]")?.addEventListener("click", initialize);
    }
  }

  document.querySelectorAll("#filters input, #filters select").forEach((control) => {
    control.addEventListener(control.type === "search" ? "input" : "change", () => { state.page = 1; applyFilters(); });
  });
  byId("sort-order").addEventListener("change", () => { state.page = 1; applyFilters(); });
  byId("clear-filters").addEventListener("click", clearFilters);
  byId("previous-page").addEventListener("click", () => { state.page -= 1; render(); results.scrollIntoView({ behavior: "smooth", block: "start" }); });
  byId("next-page").addEventListener("click", () => { state.page += 1; render(); results.scrollIntoView({ behavior: "smooth", block: "start" }); });
  byId("card-view").addEventListener("click", () => {
    state.view = "cards"; byId("card-view").setAttribute("aria-pressed", "true"); byId("table-view").setAttribute("aria-pressed", "false"); render();
  });
  byId("table-view").addEventListener("click", () => {
    state.view = "table"; byId("card-view").setAttribute("aria-pressed", "false"); byId("table-view").setAttribute("aria-pressed", "true"); render();
  });
  initialize();
})();
