(() => {
  const root = document.querySelector("#institutional-feed");
  if (!root) return;

  const PAGE_SIZE = 100;
  const CATEGORY_PATTERNS = {
    "debt/refinancing": ["debt", "credit facility", "refinanc", "borrow", "maturity"],
    "liquidity": ["liquidity", "cash flow", "working capital", "cash balance"],
    "covenant/facility": ["covenant", "facility", "waiver", "borrowing base"],
    "going concern/distress": ["going concern", "substantial doubt", "bankrupt", "default"],
    "impairment": ["impairment", "write-down", "writeoff", "goodwill charge"],
    "litigation/regulatory": ["litigation", "lawsuit", "subpoena", "investigation", "regulatory"],
    "cyber/operations": ["cyber", "ransomware", "data breach", "outage", "disruption"],
    "restructuring": ["restructur", "layoff", "workforce reduction", "severance"],
    "capex": ["capital expenditure", "capex", "construction", "development spend"],
    "new risk factor": ["risk factor", "material risk", "could adversely affect"]
  };
  const state = {
    source: "changes",
    records: JSON.parse(document.querySelector("#curated-change-data").textContent),
    catalog: null,
    page: 1,
    archiveCache: new Map(),
    privateRecords: []
  };
  const el = (id) => document.getElementById(id);
  const tbody = el("feed-body");
  const status = el("archive-status");
  const sourceTabs = [...document.querySelectorAll("[data-source-tab]")];

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[character]);
  const formatNumber = (value) => new Intl.NumberFormat("en-US").format(Number(value || 0));
  const sourceLabel = (source) => ({
    changes: "10-K change", sec: "SEC 8-K", news: "news", private: "private"
  })[source] || source;
  const setStatus = (message, busy = false) => {
    status.textContent = message;
    status.setAttribute("aria-busy", String(busy));
  };

  async function openPrivateDb() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open("pure-news-private-workspace", 1);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains("documents")) {
          db.createObjectStore("documents", { keyPath: "id" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async function loadPrivateRecords() {
    const db = await openPrivateDb();
    state.privateRecords = await new Promise((resolve, reject) => {
      const request = db.transaction("documents", "readonly")
        .objectStore("documents").getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    db.close();
    state.privateRecords.sort((a, b) => String(b.date).localeCompare(String(a.date)));
    el("private-count").textContent = formatNumber(state.privateRecords.length);
  }

  async function savePrivateRecord(record) {
    const db = await openPrivateDb();
    await new Promise((resolve, reject) => {
      const request = db.transaction("documents", "readwrite")
        .objectStore("documents").put(record);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
    db.close();
  }

  async function clearPrivateRecords() {
    const db = await openPrivateDb();
    await new Promise((resolve, reject) => {
      const request = db.transaction("documents", "readwrite")
        .objectStore("documents").clear();
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
    db.close();
    await loadPrivateRecords();
    if (state.source === "private") {
      state.records = state.privateRecords;
      render();
    }
  }

  async function sha256(text) {
    const bytes = new TextEncoder().encode(text);
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return [...new Uint8Array(digest)]
      .map((byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  function classifyPrivateText(text) {
    const lower = text.toLowerCase();
    const matches = Object.entries(CATEGORY_PATTERNS)
      .filter(([, terms]) => terms.some((term) => lower.includes(term)))
      .map(([category]) => category);
    const severe = /substantial doubt|bankrupt|default|material weakness|ransomware|impairment/i.test(text);
    return {
      categories: matches.length ? matches : ["unclassified"],
      materiality: severe ? "high — provisional" : matches.length ? "medium — provisional" : "unrated",
      confidence: "user content — unvalidated"
    };
  }

  async function extractPdf(file) {
    const pdfjs = await import("./pdf.mjs");
    pdfjs.GlobalWorkerOptions.workerSrc = "./pdf.worker.mjs";
    const document = await pdfjs.getDocument({ data: await file.arrayBuffer() }).promise;
    const pages = [];
    for (let pageNumber = 1; pageNumber <= document.numPages; pageNumber += 1) {
      const page = await document.getPage(pageNumber);
      const content = await page.getTextContent();
      pages.push(content.items.map((item) => item.str).join(" "));
    }
    return pages.join("\n\n");
  }

  async function textFromFile(file) {
    const extension = file.name.split(".").pop().toLowerCase();
    if (extension === "pdf") return extractPdf(file);
    const raw = await file.text();
    if (["html", "htm"].includes(extension)) {
      return new DOMParser().parseFromString(raw, "text/html").body.innerText;
    }
    return raw;
  }

  function currentFilteredRecords() {
    const query = el("search").value.trim().toLowerCase();
    const category = el("category").value;
    const materiality = el("materiality").value;
    return state.records.filter((record) => {
      const haystack = [
        record.issuer, record.ticker, record.headline, record.title, record.category,
        record.items, record.excerpt, record.body, record.id
      ].join(" ").toLowerCase();
      const recordCategory = Array.isArray(record.categories)
        ? record.categories.join(" ")
        : String(record.category || "");
      return (!query || haystack.includes(query))
        && (!category || recordCategory.includes(category))
        && (!materiality || String(record.materiality || "").startsWith(materiality));
    });
  }

  function rowHtml(record) {
    const issuer = record.issuer || record.ticker || "Not mapped";
    let title = record.title || record.headline || record.excerpt || "No title available";
    let classification = record.category || (record.categories || []).join(", ") || "Not classified";
    let evidence = "";
    let provenance = "";
    if (state.source === "changes") {
      evidence = `${record.direction} · ${record.materiality} · confidence ${Number(record.confidence).toFixed(3)}`;
      provenance = `<a href="${escapeHtml(record.url)}" rel="noreferrer">SEC filing</a><br><small>${escapeHtml(record.id)}</small>`;
    } else if (state.source === "sec") {
      title = `Items ${record.items || "not reported"}`;
      evidence = `${record.form} · ${formatNumber(record.textLength)} parsed characters`;
      provenance = `<a href="${escapeHtml(record.url)}" rel="noreferrer">SEC filing</a><br><small>SHA-256 ${escapeHtml(record.hash || "not available")}</small>`;
    } else if (state.source === "news") {
      classification = "Headline-only source record";
      evidence = `${record.host || "host unavailable"} · story chain ${escapeHtml(String(record.chain || "").slice(0, 12))}…`;
      provenance = `<small>Article version ${escapeHtml(record.id)}<br>Provider article body excluded</small>`;
    } else {
      title = record.name;
      evidence = `${record.materiality} · ${record.confidence}`;
      provenance = `<small>Browser-local SHA-256 ${escapeHtml(record.hash)}<br>${formatNumber(record.length)} characters</small>`;
    }
    return `<tr>
      <td>${escapeHtml(String(record.date || "").slice(0, 10))}</td>
      <td><strong>${escapeHtml(issuer)}</strong>${record.ticker ? `<br><small>${escapeHtml(record.ticker)}</small>` : ""}</td>
      <td><span class="source-pill">${escapeHtml(sourceLabel(state.source))}</span></td>
      <td class="record-title"><strong>${escapeHtml(title)}</strong><small>${escapeHtml(evidence)}</small></td>
      <td>${escapeHtml(classification)}</td>
      <td class="provenance">${provenance}</td>
    </tr>`;
  }

  function render() {
    const filtered = currentFilteredRecords();
    const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    state.page = Math.min(Math.max(1, state.page), pageCount);
    const start = (state.page - 1) * PAGE_SIZE;
    tbody.innerHTML = filtered.slice(start, start + PAGE_SIZE).map(rowHtml).join("");
    el("empty").style.display = filtered.length ? "none" : "block";
    el("result-count").textContent =
      `${formatNumber(filtered.length)} matching ${sourceLabel(state.source)} records`
      + (filtered.length ? ` · showing ${formatNumber(start + 1)}–${formatNumber(Math.min(start + PAGE_SIZE, filtered.length))}` : "");
    el("page-status").textContent = `Page ${state.page} of ${pageCount}`;
    el("previous-page").disabled = state.page <= 1;
    el("next-page").disabled = state.page >= pageCount;
  }

  async function readGzipJson(path) {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Archive request failed (${response.status})`);
    if (!("DecompressionStream" in window)) {
      throw new Error("This browser cannot decompress the local archive. Use a current Brave, Chrome, Edge, Firefox, or Safari release.");
    }
    const stream = response.body.pipeThrough(new DecompressionStream("gzip"));
    return JSON.parse(await new Response(stream).text());
  }

  function populateYears(source) {
    const select = el("archive-year");
    const partitions = state.catalog.sources[source]?.partitions || [];
    select.innerHTML = partitions.slice().reverse().map((partition) =>
      `<option value="${partition.year}">${partition.year} · ${formatNumber(partition.records)} records</option>`
    ).join("");
    select.disabled = !partitions.length;
  }

  async function loadArchive(source, year) {
    const partition = state.catalog.sources[source].partitions
      .find((candidate) => String(candidate.year) === String(year));
    if (!partition) throw new Error("Selected archive partition is unavailable.");
    const key = `${source}-${year}`;
    setStatus(`Loading ${formatNumber(partition.records)} ${sourceLabel(source)} records for ${year}…`, true);
    if (!state.archiveCache.has(key)) {
      state.archiveCache.set(key, await readGzipJson(partition.path));
    }
    state.records = state.archiveCache.get(key);
    setStatus(
      `${formatNumber(state.records.length)} records loaded for ${year}. Searches run across this complete annual partition.`,
      false
    );
    state.page = 1;
    render();
  }

  async function selectSource(source) {
    state.source = source;
    state.page = 1;
    sourceTabs.forEach((tab) => tab.setAttribute(
      "aria-selected", String(tab.dataset.sourceTab === source)
    ));
    const archive = ["sec", "news"].includes(source);
    el("archive-year").disabled = !archive;
    el("ingest-panel").open = source === "private";
    if (source === "changes") {
      state.records = JSON.parse(document.querySelector("#curated-change-data").textContent);
      setStatus("Curated 10-K changes loaded. Ranking uses filing-time evidence only.");
      render();
    } else if (source === "private") {
      await loadPrivateRecords();
      state.records = state.privateRecords;
      setStatus("Private workspace loaded from this browser only.");
      render();
    } else {
      populateYears(source);
      await loadArchive(source, el("archive-year").value);
    }
  }

  async function ingest() {
    const button = el("ingest-button");
    const files = [...el("content-files").files];
    const pasted = el("content-text").value.trim();
    if (!files.length && !pasted) {
      setStatus("Choose one or more files or paste text before importing.");
      return;
    }
    button.disabled = true;
    setStatus("Parsing and hashing content locally…", true);
    try {
      const documents = [];
      for (const file of files) {
        documents.push({ name: file.name, text: await textFromFile(file), type: file.type || "file" });
      }
      if (pasted) documents.push({ name: "Pasted content", text: pasted, type: "pasted text" });
      for (const document of documents) {
        const cleaned = document.text.replace(/\s+/g, " ").trim();
        if (!cleaned) continue;
        const hash = await sha256(cleaned);
        const classification = classifyPrivateText(cleaned);
        await savePrivateRecord({
          id: hash,
          hash,
          name: document.name,
          sourceType: el("content-source-type").value,
          issuer: el("content-issuer").value.trim(),
          ticker: el("content-ticker").value.trim().toUpperCase(),
          date: el("content-date").value || new Date().toISOString().slice(0, 10),
          body: cleaned,
          excerpt: cleaned.slice(0, 420),
          length: cleaned.length,
          importedAt: new Date().toISOString(),
          ...classification
        });
      }
      el("content-files").value = "";
      el("content-text").value = "";
      await selectSource("private");
      setStatus(`${documents.length} document${documents.length === 1 ? "" : "s"} imported, hashed, and retained only in this browser.`);
    } catch (error) {
      setStatus(`Import failed: ${error.message}`);
    } finally {
      button.disabled = false;
    }
  }

  function exportPrivateRecords() {
    const payload = JSON.stringify({
      schema: "pure-news-private-workspace-export.v1",
      exportedAt: new Date().toISOString(),
      records: state.privateRecords
    }, null, 2);
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([payload], { type: "application/json" }));
    link.download = "pure-news-private-workspace.json";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  async function initialize() {
    try {
      const response = await fetch("data/catalog.json");
      if (!response.ok) throw new Error(`Catalog request failed (${response.status})`);
      state.catalog = await response.json();
      el("sec-count").textContent = formatNumber(state.catalog.sources.sec.records);
      el("news-count").textContent = formatNumber(state.catalog.sources.news.records);
      await loadPrivateRecords();
      render();
    } catch (error) {
      setStatus(`Archive catalog unavailable: ${error.message}`);
      render();
    }
  }

  sourceTabs.forEach((tab) => tab.addEventListener("click", () => {
    selectSource(tab.dataset.sourceTab).catch((error) => setStatus(`Unable to load source: ${error.message}`));
  }));
  el("archive-year").addEventListener("change", () => {
    if (["sec", "news"].includes(state.source)) {
      loadArchive(state.source, el("archive-year").value).catch((error) => setStatus(`Unable to load archive: ${error.message}`));
    }
  });
  ["search", "category", "materiality"].forEach((id) => {
    el(id).addEventListener(id === "search" ? "input" : "change", () => {
      state.page = 1;
      render();
    });
  });
  el("previous-page").addEventListener("click", () => { state.page -= 1; render(); });
  el("next-page").addEventListener("click", () => { state.page += 1; render(); });
  el("ingest-button").addEventListener("click", ingest);
  el("export-private").addEventListener("click", exportPrivateRecords);
  el("clear-private").addEventListener("click", async () => {
    if (window.confirm("Delete all browser-local Pure News workspace documents on this device?")) {
      await clearPrivateRecords();
      setStatus("Browser-local workspace cleared.");
    }
  });
  initialize();
})();
