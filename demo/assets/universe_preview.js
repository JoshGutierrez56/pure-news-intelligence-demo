(() => {
  "use strict";

  const PAGE_SIZE = 100;
  const state = { records: [], filtered: [], page: 1 };
  const byId = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;");
  const formatNumber = (value) => Number(value).toLocaleString("en-US");
  const formatDate = (value) => value ? String(value).slice(0, 10) : "Unavailable";

  function statusClass(status) {
    if (status === "Fully validated") return "teal";
    if (status === "Partial metadata") return "amber";
    if (status === "Missing source coverage") return "danger";
    return "neutral";
  }

  function availability(record, field) {
    if (field === "10k") return Boolean(record.latest_10k_date);
    if (field === "8k") return record.recent_8k_count > 0;
    return record.news_metadata_count !== null;
  }

  function renderSummary(summary) {
    const values = [
      [summary.total_issuers_indexed, "total issuers indexed"],
      [summary.issuers_with_10k_metadata, "with 10-K metadata"],
      [summary.issuers_with_recent_8k_metadata, "with recent 8-K metadata"],
      [summary.issuers_with_permitted_news_metadata, "with permitted news metadata"],
      [summary.issuers_fully_validated, "fully validated in the demo"],
      [summary.issuers_not_yet_processed, "not yet processed"]
    ];
    byId("universe-summary").innerHTML = values.map(([value, label], index) =>
      `<div class="metric${index < 2 ? " primary" : ""}"><strong>${formatNumber(value)}</strong><span>${escapeHtml(label)}</span></div>`
    ).join("");
    byId("universe-summary").removeAttribute("aria-busy");
    byId("universe-as-of").textContent = formatDate(summary.as_of_timestamp);
  }

  function matches(record) {
    const query = byId("universe-search").value.trim().toLowerCase();
    const status = byId("universe-status").value;
    const tenK = byId("universe-10k").value;
    const eightK = byId("universe-8k").value;
    const news = byId("universe-news").value;
    const validated = byId("universe-validated").value;
    if (query && !`${record.ticker || ""} ${record.company_name || ""} ${record.cik}`.toLowerCase().includes(query)) return false;
    if (status && record.processing_status !== status) return false;
    if (tenK && availability(record, "10k") !== (tenK === "available")) return false;
    if (eightK && availability(record, "8k") !== (eightK === "available")) return false;
    if (news && availability(record, "news") !== (news === "available")) return false;
    if (validated === "validated" && record.validated_demo_status === "Not validated in current demo") return false;
    if (validated === "idea" && record.validated_demo_status !== "Research Idea Engine reviewed") return false;
    if (validated === "not_validated" && record.validated_demo_status !== "Not validated in current demo") return false;
    return true;
  }

  function sourceCoverage(record) {
    const sources = [
      [Boolean(record.latest_10k_date), "10-K"],
      [record.recent_8k_count > 0, "8-K"],
      [record.news_metadata_count !== null, "News"]
    ];
    return sources.map(([available, label]) =>
      `<span class="coverage-chip ${available ? "available" : "missing"}">${escapeHtml(label)}: ${available ? "available" : "missing"}</span>`
    ).join("");
  }

  function rowHtml(record) {
    const tenK = record.latest_10k_date
      ? `<a href="${escapeHtml(record.latest_10k_url)}" target="_blank">${escapeHtml(formatDate(record.latest_10k_date))}</a><small>${escapeHtml(record.latest_10k_accession || "")}</small>`
      : `<span class="missing-value">Unavailable</span>`;
    const news = record.news_metadata_count === null
      ? `<span class="missing-value">News metadata unavailable</span>`
      : `<strong>${formatNumber(record.news_metadata_count)}</strong><small>Latest ${escapeHtml(formatDate(record.latest_news_timestamp))}</small>`;
    return `<tr>
      <td><strong>${escapeHtml(record.ticker || "—")}</strong><small>CIK ${escapeHtml(record.cik)}</small></td>
      <td>${escapeHtml(record.company_name || "Company name unavailable")}</td>
      <td>${tenK}</td>
      <td><strong>${formatNumber(record.recent_8k_count)}</strong><small>Latest ${escapeHtml(formatDate(record.latest_8k_date))}</small></td>
      <td>${news}</td>
      <td><span class="status ${statusClass(record.processing_status)}">${escapeHtml(record.processing_status)}</span></td>
      <td>${escapeHtml(record.validated_demo_status)}</td>
      <td><div class="coverage-chips">${sourceCoverage(record)}</div><details><summary>Gaps and provenance</summary><p><strong>Missing:</strong> ${escapeHtml(record.missing_fields.join(", ") || "None in indexed fields")}</p><p><strong>Sources:</strong> ${escapeHtml(record.source_provenance.join(", "))}</p></details></td>
    </tr>`;
  }

  function render() {
    state.filtered = state.records.filter(matches);
    const pages = Math.max(1, Math.ceil(state.filtered.length / PAGE_SIZE));
    state.page = Math.min(state.page, pages);
    const start = (state.page - 1) * PAGE_SIZE;
    const pageRecords = state.filtered.slice(start, start + PAGE_SIZE);
    byId("universe-rows").innerHTML = pageRecords.length
      ? pageRecords.map(rowHtml).join("")
      : `<tr><td colspan="8"><strong>No issuers match these filters.</strong> Reset filters or broaden the search.</td></tr>`;
    byId("universe-result-count").textContent =
      `${formatNumber(state.filtered.length)} of ${formatNumber(state.records.length)} issuers shown`;
    byId("universe-page").textContent = `Page ${state.page} of ${pages}`;
    byId("universe-previous").disabled = state.page <= 1;
    byId("universe-next").disabled = state.page >= pages;
  }

  async function initialize() {
    try {
      const [summaryResponse, coverageResponse] = await Promise.all([
        fetch("data/universe_preview/universe_summary.json"),
        fetch("data/universe_preview/universe_coverage.json")
      ]);
      if (!summaryResponse.ok || !coverageResponse.ok) throw new Error("Coverage files unavailable");
      const [summary, coverage] = await Promise.all([summaryResponse.json(), coverageResponse.json()]);
      renderSummary(summary);
      state.records = coverage.records;
      render();
    } catch (error) {
      byId("universe-result-count").textContent = `Universe preview unavailable: ${error.message}`;
      byId("universe-rows").innerHTML = `<tr><td colspan="8">Frozen coverage data could not be loaded.</td></tr>`;
    }
  }

  byId("universe-filters").addEventListener("input", () => { state.page = 1; render(); });
  byId("universe-filters").addEventListener("change", () => { state.page = 1; render(); });
  byId("universe-filters").addEventListener("reset", () => setTimeout(() => { state.page = 1; render(); }));
  byId("universe-previous").addEventListener("click", () => { state.page -= 1; render(); byId("universe-table-title").focus?.(); });
  byId("universe-next").addEventListener("click", () => { state.page += 1; render(); byId("universe-table-title").focus?.(); });
  initialize();
})();
