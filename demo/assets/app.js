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
  const PRIVATE_CATEGORY_PRIORITY = [
    "going concern/distress", "impairment", "cyber/operations",
    "litigation/regulatory", "covenant/facility", "debt/refinancing",
    "liquidity", "restructuring", "capex", "new risk factor"
  ];
  const ITEM_LABELS = {
    "1.01": "entry into a material agreement",
    "1.02": "termination of a material agreement",
    "2.01": "completion of an acquisition or disposition",
    "2.02": "results of operations or financial condition",
    "2.03": "creation of a direct financial obligation",
    "2.04": "an event accelerating or increasing a financial obligation",
    "2.05": "costs associated with exit or disposal activities",
    "2.06": "a material impairment",
    "3.01": "a listing or continued-listing notice",
    "4.01": "a change in the registrant's certifying accountant",
    "4.02": "non-reliance on previously issued financial statements",
    "5.02": "a director or executive officer change",
    "5.03": "an amendment to governing documents",
    "5.07": "submission of matters to a shareholder vote",
    "7.01": "Regulation FD disclosure",
    "8.01": "another material corporate event",
    "9.01": "financial statements or exhibits"
  };
  const ITEM_DILIGENCE = {
    "1.01": "Read the agreement and exhibits: identify economics, counterparties, term, termination rights, covenants, and conditions.",
    "1.02": "Quantify lost economics, termination payments, replacement options, and the operating dependency that ended.",
    "2.01": "Rebuild transaction economics: price, consideration mix, financing, acquired earnings, synergies, integration costs, and closing adjustments.",
    "2.02": "Compare reported revenue, margins, EPS, cash flow, and guidance with consensus and the prior period; isolate the source of the variance.",
    "2.03": "Add the obligation to the debt schedule; verify principal, rate, maturity, security, covenants, permitted use, and incremental interest expense.",
    "2.04": "Check the trigger, accelerated amount, cure period, cross-defaults, liquidity available, and creditor remedies.",
    "2.05": "Quantify cash versus non-cash charges, expected savings, timing, payback, and execution or revenue risk.",
    "2.06": "Identify the impaired asset, charge size, valuation assumptions, cash implications, and covenant or tax effects.",
    "3.01": "Check the exchange requirement, cure period, compliance plan, financing implications, and probability of delisting.",
    "4.01": "Review the reason for the auditor change, disagreements, reportable events, transition timing, and any control implications.",
    "4.02": "Stop relying on the affected statements; identify periods and accounts involved, expected restatement size, control failures, and covenant effects.",
    "5.02": "Establish whether the change was planned or abrupt; review succession, interim authority, incentives, strategy continuity, and stated reasons.",
    "5.03": "Read the amendment for changes to shareholder rights, governance protections, voting, authorization, or takeover defenses.",
    "5.07": "Compare vote outcomes with management recommendations and prior support; flag failed proposals or unusually high dissent.",
    "7.01": "Open the furnished material and identify the actual KPI, guidance, financing, or strategic update; Item 7.01 alone does not reveal content.",
    "8.01": "Open the filing and exhibits before escalating; Item 8.01 alone does not identify the underlying event.",
    "9.01": "Use the exhibits as the primary evidence for terms, financial statements, presentations, or press releases."
  };
  const NEWS_RULES = [
    { label: "market recap or listicle", terms: /stock moves|ascends while market falls|market dipped|gained today|what you should know|best stocks|stocks? of 20\d\d|shares (rose|fell|rise|fall)|up today|down today/i,
      why: "Low-information headline: no company-reported fundamental change is identified. Treat this as attention or price context only; look for a filing, release, or estimate revision before escalating." },
    { label: "earnings or guidance", terms: /earnings|revenue|profit|sales|guidance|quarter|eps|forecast|outlook|beat|miss/i,
      why: "Estimate impact: compare reported and guided revenue, margins, EPS, and cash flow with consensus and the prior period; isolate price, volume, mix, and one-offs." },
    { label: "merger, acquisition, or asset transaction", terms: /acqui|merger|deal|buyout|takeover|divest|sale of|strategic alternative/i,
      why: "Rebuild deal economics: price, consideration and financing, acquired earnings, accretion or dilution, synergies, integration cost, approvals, and closing conditions." },
    { label: "financing or capital structure", terms: /debt|bond|loan|credit|financ|offering|capital raise|dividend|buyback|repurchase/i,
      why: "Update the capital structure: amount, rate or issue price, maturity, dilution, use of proceeds, covenant headroom, and effect on interest expense or shareholder distributions." },
    { label: "legal or regulatory development", terms: /lawsuit|court|legal|regulat|investigation|probe|settlement|fine|antitrust|sec /i,
      why: "Determine procedural stage, alleged conduct, claimed or capped damages, reserve and insurance, operating restrictions, remediation, and appeal path." },
    { label: "management or governance change", terms: /ceo|cfo|chair|director|executive|appoint|resign|board|management/i,
      why: "Check whether the transition was planned or abrupt, who holds interim authority, stated reasons, incentive changes, and implications for strategy or controls." },
    { label: "operating or product development", terms: /launch|product|contract|customer|plant|factory|outage|recall|cyber|breach|production/i,
      why: "Quantify affected revenue, units, capacity, customers, downtime, remediation cost, launch timing, and whether the event changes guidance." },
    { label: "analyst opinion", terms: /upgrade|downgrade|price target|analyst|bull|bear/i,
      why: "This is an opinion or estimate signal, not issuer evidence. Identify the analyst's changed assumptions and consensus dispersion before using it." }
  ];
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
    changes: "10-K change", sec: "SEC 8-K", news: "news", private: "local prototype"
  })[source] || source;
  const setStatus = (message, busy = false) => {
    status.textContent = message;
    status.setAttribute("aria-busy", String(busy));
  };

  function compactText(value, limit = 260) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (!text || text.length <= limit) return text || "No extractive text is available.";
    const clipped = text.slice(0, limit + 1);
    const boundary = Math.max(clipped.lastIndexOf(". "), clipped.lastIndexOf("? "), clipped.lastIndexOf("! "));
    if (boundary >= 90) return clipped.slice(0, boundary + 1);
    const word = clipped.lastIndexOf(" ");
    return `${clipped.slice(0, word > 0 ? word : limit).replace(/[ ,;:]+$/, "")}…`;
  }

  function joinedItems(codes) {
    const material = codes.filter((code) => code !== "9.01");
    const described = material.map((code) => ITEM_LABELS[code]).filter(Boolean);
    if (!described.length) return `Items ${codes.join(", ") || "not specified"}`;
    const items = described.slice(0, 3).map((label, index) => `Item ${material[index]} (${label})`);
    return items.join("; ") + (codes.includes("9.01") ? "; with exhibits" : "");
  }

  function analystContext(record) {
    if (state.source === "changes") {
      return {
        summary: record.summary,
        why: record.why,
        basis: "Audited disclosure-change classification"
      };
    }
    if (state.source === "sec") {
      const codes = String(record.items || "").split(/\s+/).filter(Boolean);
      const primaryCodes = codes.filter((code) => code !== "9.01");
      const questions = [...new Set(primaryCodes.map((code) => ITEM_DILIGENCE[code]).filter(Boolean))];
      return {
        summary: `${record.issuer || record.ticker || "The issuer"} filed ${joinedItems(codes)}.`,
        why: questions.slice(0, 2).join(" ") || "The archive metadata does not identify the event. Open the filing and exhibits before drawing a conclusion.",
        basis: "SEC-item readout; filing text and exhibits require source review"
      };
    }
    if (state.source === "news") {
      const match = NEWS_RULES.find((rule) => rule.terms.test(record.headline || ""));
      return {
        summary: compactText(record.headline),
        why: match?.why || "Unclassified headline. Identify the specific financial driver, magnitude, timing, and primary-source confirmation before changing an investment view.",
        basis: `${match?.label || "unclassified"} · headline-only; publisher article body unavailable`
      };
    }
    const privateCategory = (record.categories || [])[0];
    const privateQuestions = {
      "debt/refinancing": "Extract amount, rate, maturity, security, use of proceeds, and covenant headroom; update interest expense and the maturity schedule.",
      "liquidity": "Reconcile cash, revolver availability, working capital, and cash burn; stress-test funding runway.",
      "covenant/facility": "Identify the tested ratio, threshold, headroom, waiver dates, and remedies.",
      "going concern/distress": "Verify cash runway, default or waiver status, funding dependency, and auditor language.",
      "impairment": "Identify the asset, charge, valuation assumptions, cash impact, and covenant or tax effects.",
      "litigation/regulatory": "Identify forum, stage, damages, reserves, insurance, remedies, and operational restrictions.",
      "cyber/operations": "Determine whether an event occurred, systems or data affected, downtime, recovery cost, and legal exposure.",
      "restructuring": "Quantify charges, savings, timing, payback, and execution or revenue risk.",
      "capex": "Quantify spend, timing, funding, free-cash-flow effect, capacity, and expected return.",
      "new risk factor": "Identify the new exposure, probability, severity, affected financial lines, and mitigants."
    };
    return {
      summary: compactText(record.excerpt),
      why: (record.categories || []).includes("unclassified")
        ? "No fixed-rule theme was detected. Identify the event, affected financial driver, magnitude, timing, and primary evidence before escalating."
        : privateQuestions[privateCategory] || `Verify the detected ${(record.categories || []).join(", ")} language against the full document and quantify its financial effect.`,
      basis: "Provisional browser-local extract; analyst validation required"
    };
  }

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
      .map(([category]) => category)
      .sort((a, b) => PRIVATE_CATEGORY_PRIORITY.indexOf(a) - PRIVATE_CATEGORY_PRIORITY.indexOf(b));
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
    const context = analystContext(record);
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
      <td class="analyst-context">
        <p><strong>Short summary</strong><br>${escapeHtml(context.summary)}</p>
        <p class="why"><strong>Why it matters</strong><br>${escapeHtml(context.why)}</p>
        <span class="basis-label">${escapeHtml(context.basis)}</span>
      </td>
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
    state.page = 1;
    render();
    setStatus(
      `${formatNumber(state.records.length)} records loaded for ${year}. Searches run across this complete annual partition.`,
      false
    );
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
