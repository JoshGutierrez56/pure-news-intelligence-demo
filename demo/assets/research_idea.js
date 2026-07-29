(() => {
  "use strict";

  const DATA_ROOT = "data/research_idea_packets/v1/";
  const INDEX_URL = `${DATA_ROOT}index.json`;
  const STORAGE_KEY = "pni-research-idea-dispositions-v1";
  const GUIDED_CHANGE_ID = "8f5336b55618ffe68e8a";
  const DISCLAIMER = "AI-generated research hypothesis based on the cited evidence. It is not a fact, personalized investment advice, or a validated trading signal. Analyst review is required.";
  const TRADE_TITLE = "Illustrative Trade Hypothesis — Analyst Review Required";
  const page = document.body.dataset.researchIdeaPage;
  const byId = (id) => document.getElementById(id);
  const all = (selector, root = document) => [...root.querySelectorAll(selector)];
  const list = (value) => Array.isArray(value) ? value : [];
  const text = (value, fallback = "Not reported") => value === null || value === undefined || value === "" ? fallback : String(value);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[character]);
  const humanize = (value) => text(value).replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  const formatScore = (value) => Number.isFinite(Number(value)) ? Number(value).toFixed(3) : "Not reported";
  const formatDate = (value) => {
    if (!value) return "Not reported";
    const parts = String(value).slice(0, 10).split("-");
    if (parts.length !== 3) return text(value);
    const date = new Date(Date.UTC(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2])));
    return Number.isNaN(date.valueOf()) ? text(value) : new Intl.DateTimeFormat("en-US", {
      year: "numeric", month: "short", day: "numeric", timeZone: "UTC"
    }).format(date);
  };
  const formatTimestamp = (value) => {
    if (!value) return "Not reported";
    const date = new Date(value);
    return Number.isNaN(date.valueOf()) ? text(value) : new Intl.DateTimeFormat("en-US", {
      year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
      timeZoneName: "short"
    }).format(date);
  };

  function sourceLink(url, label) {
    if (!/^https:\/\//i.test(String(url || ""))) return `<span>${escapeHtml(label)} unavailable</span>`;
    return `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer noopener" aria-label="${escapeHtml(label)} (opens in a new tab)">${escapeHtml(label)} <span aria-hidden="true">↗</span></a>`;
  }

  function statusClass(status) {
    if (status === "PUBLISHABLE" || status === "PASS" || status === "PASS_WITH_EDITS" || status === "READY_FOR_ANALYST_RESEARCH") return "teal";
    if (String(status).startsWith("HOLD") || status === "PENDING_REVIEW" || status === "DRAFT_PENDING_SKEPTIC") return "amber";
    if (status === "REJECTED_BY_SKEPTIC" || status === "REJECTED" || status === "FAIL") return "red";
    return "outline";
  }

  function statusPill(status) {
    return `<span class="status ${statusClass(status)}">${escapeHtml(text(status))}</span>`;
  }

  function renderRefs(values) {
    const refs = list(values).filter(Boolean);
    if (!refs.length) return `<span class="ri-no-reference">No evidence reference reported</span>`;
    return `<span class="ri-reference-list" aria-label="Evidence references">${refs.map((ref) => `<code>${escapeHtml(ref)}</code>`).join("")}</span>`;
  }

  function renderStringList(values, emptyLabel = "None reported.") {
    const items = list(values).filter((item) => item !== null && item !== undefined && item !== "");
    if (!items.length) return `<p class="ri-empty-inline">${escapeHtml(emptyLabel)}</p>`;
    return `<ul>${items.map((item) => `<li>${escapeHtml(typeof item === "string" ? item : JSON.stringify(item))}</li>`).join("")}</ul>`;
  }

  function readStoredDispositions() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch (_) {
      return {};
    }
  }

  function writeStoredDispositions(dispositions) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(dispositions));
      return true;
    } catch (_) {
      return false;
    }
  }

  function analystOverlay(packet) {
    const stored = readStoredDispositions()[packet.change_id];
    if (stored && typeof stored === "object") {
      return {
        status: text(stored.status, "UNREVIEWED"),
        analyst_notes: text(stored.analyst_notes, ""),
        edited_fields: list(stored.edited_fields),
        review_timestamp: stored.review_timestamp || null,
        saved_locally_only: true
      };
    }
    const base = packet.analyst_disposition || {};
    return {
      status: text(base.status, "UNREVIEWED"),
      analyst_notes: text(base.analyst_notes, ""),
      edited_fields: list(base.edited_fields),
      review_timestamp: base.review_timestamp || null,
      saved_locally_only: true
    };
  }

  function saveOverlay(packet, overlay) {
    const dispositions = readStoredDispositions();
    dispositions[packet.change_id] = {
      status: overlay.status,
      analyst_notes: overlay.analyst_notes,
      edited_fields: overlay.edited_fields,
      review_timestamp: overlay.review_timestamp,
      saved_locally_only: true
    };
    return writeStoredDispositions(dispositions);
  }

  function stableValue(value) {
    if (Array.isArray(value)) return value.map(stableValue);
    if (value && typeof value === "object") {
      return Object.keys(value).sort().reduce((result, key) => {
        result[key] = stableValue(value[key]);
        return result;
      }, {});
    }
    return value;
  }

  function downloadJson(packet, overlay) {
    const exported = {
      analyst_overlay: overlay,
      export_version: "1.0",
      source_packet: packet
    };
    const payload = `${JSON.stringify(stableValue(exported), null, 2)}\n`;
    const url = URL.createObjectURL(new Blob([payload], { type: "application/json;charset=utf-8" }));
    const filename = `research-idea-${String(packet.change_id).replace(/[^A-Za-z0-9._-]/g, "-")}.json`;
    const anchor = Object.assign(document.createElement("a"), { href: url, download: filename });
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  function normalizeIndex(payload) {
    let raw = [];
    if (Array.isArray(payload)) raw = payload;
    else if (Array.isArray(payload?.packets)) raw = payload.packets;
    else if (Array.isArray(payload?.records)) raw = payload.records;
    else if (Array.isArray(payload?.entries)) raw = payload.entries;
    else if (Array.isArray(payload?.items)) raw = payload.items;
    else if (payload?.packets && typeof payload.packets === "object") {
      raw = Object.entries(payload.packets).map(([changeId, entry]) => typeof entry === "string"
        ? { change_id: changeId, packet_path: entry }
        : { change_id: changeId, ...entry });
    } else if (payload?.packet_files && typeof payload.packet_files === "object") {
      raw = Object.entries(payload.packet_files).map(([changeId, packetPath]) => ({ change_id: changeId, packet_path: packetPath }));
    }
    return raw.map((entry) => {
      if (typeof entry === "string") {
        const filename = entry.split("/").pop() || entry;
        return { change_id: filename.replace(/\.json$/i, ""), packet_path: entry };
      }
      return entry && typeof entry === "object" ? entry : {};
    }).filter((entry) => entry.change_id || entry.packet_id || entry.id || entry.packet);
  }

  function entryId(entry) {
    return text(entry.change_id || entry.packet?.change_id || entry.packet_id || entry.id, "");
  }

  function packetPath(entry) {
    const id = entryId(entry);
    let candidate = entry.packet_path || entry.path || entry.file || entry.href || `${id}.json`;
    candidate = String(candidate).replace(/\\/g, "/").replace(/^\.?\//, "");
    if (!candidate || candidate.includes("..") || /^[a-z]+:/i.test(candidate)) return `${DATA_ROOT}${encodeURIComponent(id)}.json`;
    if (candidate.startsWith("demo/")) candidate = candidate.slice(5);
    if (candidate.startsWith("data/")) return candidate;
    if (candidate.startsWith("research_idea_packets/")) return `data/${candidate}`;
    if (candidate.includes("/")) candidate = candidate.split("/").pop();
    return `${DATA_ROOT}${candidate}`;
  }

  async function fetchJson(url) {
    const response = await fetch(url, { cache: "force-cache" });
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return response.json();
  }

  async function loadIndex() {
    const payload = await fetchJson(INDEX_URL);
    const entries = normalizeIndex(payload);
    if (!entries.length) throw new Error("The validated packet index is empty.");
    return { payload, entries };
  }

  async function loadPacket(entry) {
    if (entry.packet && typeof entry.packet === "object") return entry.packet;
    const packet = await fetchJson(packetPath(entry));
    if (!packet || typeof packet !== "object" || !packet.change_id) throw new Error("Packet content is invalid.");
    return packet;
  }

  function errorMarkup(title, detail, retry = false) {
    return `<div class="error-state" role="alert">
      <h2>${escapeHtml(title)}</h2>
      <p>${escapeHtml(detail)}</p>
      ${retry ? `<button class="secondary" type="button" data-ri-retry>Retry</button>` : ""}
    </div>`;
  }

  function sectionHeading(number, stageClass, stage, id, title, description = "") {
    return `<header class="ri-section-heading">
      <span class="ri-section-number" aria-hidden="true">${escapeHtml(number)}</span>
      <div><span class="ri-stage-label ${stageClass}">${escapeHtml(stage)}</span><h2 id="${id}">${escapeHtml(title)}</h2>${description ? `<p>${escapeHtml(description)}</p>` : ""}</div>
    </header>`;
  }

  function renderEvidence(packet) {
    const evidence = packet.evidence || {};
    const prior8k = list(evidence.related_prior_8k);
    const priorNews = list(evidence.related_prior_news);
    const sourceRange = (range) => range
      ? `<span>${range.document_id ? `${escapeHtml(range.document_id)} · ` : ""}offsets ${escapeHtml(range.start)}–${escapeHtml(range.end)} ${range.verified === true || evidence.evidence_offsets_verified === true ? "· verified" : ""}</span>`
      : `<span>Not present</span>`;
    return `<section class="ri-packet-section" aria-labelledby="ri-source-title">
      ${sectionHeading("01", "ri-stage-evidence", "EVIDENCE", "ri-source-title", "Source evidence", "Immutable filing-time evidence and strictly earlier sources.")}
      <div class="ri-source-ledger">
        <div><strong>Issuer</strong><span>${escapeHtml(packet.issuer)} (${escapeHtml(packet.ticker)})</span></div>
        <div><strong>Filing date</strong><span>${escapeHtml(formatDate(packet.filing_date))}</span></div>
        <div><strong>Formation timestamp</strong><span>${escapeHtml(formatTimestamp(packet.formation_timestamp))}</span></div>
        <div><strong>Section</strong><span>${escapeHtml(packet.section)}</span></div>
        <div><strong>Change ID</strong><code>${escapeHtml(packet.change_id)}</code></div>
        <div><strong>Evidence offsets</strong><span>${evidence.evidence_offsets_verified ? "Verified" : "Not verified"}</span></div>
        <div class="ri-ledger-wide"><strong>Current source</strong>${sourceLink(evidence.current_source_url || packet.source_url, "Open current SEC filing")}</div>
        <div class="ri-ledger-wide"><strong>Prior source</strong>${sourceLink(evidence.prior_source_url, "Open prior SEC filing")}</div>
      </div>
      <div class="ri-evidence-comparison">
        <article class="ri-excerpt ri-prior">
          <div class="ri-card-kicker"><span>Prior filing</span>${renderRefs([evidence.evidence_ids?.prior_excerpt || evidence.evidence_ids?.prior_excerpt_id])}</div>
          <blockquote tabindex="0" aria-label="Prior filing excerpt">${escapeHtml(text(evidence.prior_excerpt))}</blockquote>
          <p class="ri-offset">${sourceRange(evidence.evidence_offsets?.prior || evidence.evidence_offsets?.prior_excerpt)}</p>
        </article>
        <article class="ri-excerpt ri-current">
          <div class="ri-card-kicker"><span>Current filing</span>${renderRefs([evidence.evidence_ids?.current_excerpt || evidence.evidence_ids?.current_excerpt_id])}</div>
          <blockquote tabindex="0" aria-label="Current filing excerpt">${escapeHtml(text(evidence.current_excerpt))}</blockquote>
          <p class="ri-offset">${sourceRange(evidence.evidence_offsets?.current || evidence.evidence_offsets?.current_excerpt)}</p>
        </article>
      </div>
      <div class="ri-delta-grid">
        <article class="ri-delta-added"><h3>Added language</h3><p tabindex="0" aria-label="Added filing language">${escapeHtml(text(evidence.added_text, "No added language reported."))}</p>${renderRefs(evidence.evidence_ids?.added_text ? [evidence.evidence_ids.added_text] : evidence.evidence_ids?.added_text_id ? [evidence.evidence_ids.added_text_id] : [])}</article>
        <article class="ri-delta-removed"><h3>Removed language</h3><p tabindex="0" aria-label="Removed filing language">${escapeHtml(text(evidence.removed_text, "No removed language reported."))}</p>${renderRefs(evidence.evidence_ids?.removed_text ? [evidence.evidence_ids.removed_text] : evidence.evidence_ids?.removed_text_id ? [evidence.evidence_ids.removed_text_id] : [])}</article>
      </div>
      <div class="ri-prior-source-grid">
        <article>
          <h3>Related prior 8-K evidence <span class="status outline">${prior8k.length}</span></h3>
          ${prior8k.length ? `<ul class="ri-source-list">${prior8k.map((item) => `<li><strong>${escapeHtml(item.information_date || item.acceptance_timestamp || "Earlier filing")} · ${escapeHtml(text(item.accession_number, "8-K"))}</strong><span>${escapeHtml([item.primary_category, item.item_codes].filter(Boolean).join(" · ") || "Related prior 8-K evidence")}</span>${sourceLink(item.url || item.source_url, `Open 8-K ${text(item.accession_number, "")}`)}${renderRefs([item.evidence_id])}</li>`).join("")}</ul>` : `<p class="ri-empty-inline">No related prior 8-K evidence is recorded in this packet.</p>`}
        </article>
        <article>
          <h3>Related prior news <span class="status outline">${priorNews.length}</span></h3>
          ${priorNews.length ? `<ul class="ri-source-list">${priorNews.map((item) => `<li><strong>${escapeHtml(formatTimestamp(item.publication_timestamp))} · ${escapeHtml(text(item.provider_host, "headline source"))}</strong><span>${escapeHtml(item.headline)}</span><span>Headline-only evidence</span>${renderRefs([item.evidence_id])}</li>`).join("")}</ul>` : `<p class="ri-empty-inline">No related prior news is recorded in this packet.</p>`}
        </article>
      </div>
      <aside class="ri-stage-panel ri-stage-expost-panel">
        <span class="ri-stage-label ri-stage-expost">EX-POST OUTCOME</span>
        <p><strong>No ex-post outcome is loaded into this research idea.</strong> Later returns, drawdowns, filings, news, and commentary were excluded from generation.</p>
      </aside>
    </section>`;
  }

  function renderInterpretation(packet) {
    const interpretation = packet.system_interpretation || {};
    return `<section class="ri-packet-section" aria-labelledby="ri-change-title">
      ${sectionHeading("02", "ri-stage-interpretation", "SYSTEM INTERPRETATION", "ri-change-title", "What changed", "Facts and inferences remain visibly separate.")}
      <div class="ri-plain-change"><strong>Plain-language change</strong><p>${escapeHtml(text(interpretation.plain_language_change))}</p></div>
      <div class="ri-fact-inference-grid">
        <article class="ri-fact-panel">
          <span class="ri-stage-label ri-stage-evidence">EVIDENCE FACTS</span>
          <h3>Traceable statements</h3>
          ${list(interpretation.evidence_facts).length ? `<ol>${list(interpretation.evidence_facts).map((fact) => `<li><p>${escapeHtml(fact.statement)}</p><span>${escapeHtml(humanize(fact.fact_type))}</span>${renderRefs(fact.evidence_ids)}</li>`).join("")}</ol>` : `<p class="ri-empty-inline">No evidence facts reported.</p>`}
        </article>
        <article class="ri-inference-panel">
          <span class="ri-stage-label ri-stage-interpretation">SYSTEM INTERPRETATION</span>
          <h3>Inferences—not facts</h3>
          ${list(interpretation.inferences).length ? `<ol>${list(interpretation.inferences).map((inference) => `<li><p>${escapeHtml(inference.statement)}</p><p class="ri-caveat"><strong>Caveat:</strong> ${escapeHtml(inference.caveat)}</p><span>${escapeHtml(humanize(inference.inference_type))} · confidence ${escapeHtml(formatScore(inference.confidence))}</span>${renderRefs(inference.evidence_ids)}</li>`).join("")}</ol>` : `<p class="ri-empty-inline">No system inferences reported.</p>`}
        </article>
      </div>
      <div class="ri-uncertainty-panel">
        <h3>What remains uncertain</h3>
        ${list(interpretation.uncertainties).length ? `<div class="ri-card-grid">${list(interpretation.uncertainties).map((item) => `<article><strong>${escapeHtml(item.uncertainty)}</strong><p>${escapeHtml(item.why_it_matters)}</p><h4>Data needed</h4>${renderStringList(item.data_needed)}</article>`).join("")}</div>` : `<p class="ri-empty-inline">No uncertainties reported.</p>`}
      </div>
    </section>`;
  }

  function renderClassification(packet) {
    const classification = packet.frozen_classification || {};
    const confidence = packet.confidence || {};
    return `<section class="ri-packet-section" aria-labelledby="ri-classification-title">
      ${sectionHeading("03", "ri-stage-interpretation", "SYSTEM INTERPRETATION", "ri-classification-title", "Novelty and materiality", "Frozen classifications are preserved exactly as recorded.")}
      <div class="ri-classification-grid">
        <div><strong>Category</strong><span>${escapeHtml(text(classification.category))}</span></div>
        <div><strong>Direction</strong><span class="badge ${escapeHtml(classification.direction || "ambiguous")}">${escapeHtml(humanize(classification.direction))}</span></div>
        <div><strong>Materiality</strong><span class="badge ${escapeHtml(classification.materiality || "low")}">${escapeHtml(humanize(classification.materiality))}</span></div>
        <div><strong>Novelty</strong><span>${escapeHtml(text(classification.novelty))}</span></div>
        <div><strong>Frozen confidence</strong><span>${escapeHtml(formatScore(classification.confidence))}</span></div>
      </div>
      <div class="ri-confidence-strip" aria-label="Packet confidence scores">
        ${Object.entries({
          Evidence: confidence.evidence,
          Novelty: confidence.novelty,
          Mechanism: confidence.mechanism,
          Hypothesis: confidence.hypothesis,
          "Trade readiness": confidence.trade_readiness
        }).map(([label, score]) => `<div><strong>${escapeHtml(label)}</strong><span>${escapeHtml(formatScore(score))}</span></div>`).join("")}
      </div>
      <p class="ri-score-boundary">These scores support review triage. They are not probabilities of return.</p>
    </section>`;
  }

  function renderMechanisms(packet) {
    const mechanisms = list(packet.economic_mechanisms);
    return `<section class="ri-packet-section" aria-labelledby="ri-mechanism-title">
      ${sectionHeading("04", "ri-stage-interpretation", "SYSTEM INTERPRETATION", "ri-mechanism-title", "Economic mechanisms", "Possible economic chains, each paired with evidence and a counterargument.")}
      ${mechanisms.length ? `<div class="ri-mechanism-grid">${mechanisms.map((item, index) => `<article class="ri-mechanism-card">
        <div class="ri-card-kicker"><span>Mechanism ${index + 1}</span><span>Confidence ${escapeHtml(formatScore(item.mechanism_confidence))}</span></div>
        <h3>${escapeHtml(item.mechanism)}</h3>
        <p><strong>Affected financial driver:</strong> ${escapeHtml(item.affected_financial_driver)}</p>
        <ol class="ri-causal-chain">${list(item.causal_chain).map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>
        <div class="ri-counterargument"><strong>Counterargument</strong><p>${escapeHtml(item.counterargument)}</p></div>
        ${renderRefs(item.supporting_evidence_ids)}
      </article>`).join("")}</div>` : `<div class="ri-withheld"><h3>No sufficiently grounded mechanism was published</h3><p>Review the packet status and skeptical findings below.</p></div>`}
    </section>`;
  }

  function renderHypotheses(packet) {
    const hypotheses = list(packet.research_hypotheses);
    return `<section class="ri-packet-section" aria-labelledby="ri-hypothesis-title">
      ${sectionHeading("05", "ri-stage-hypothesis", "AI-GENERATED HYPOTHESIS", "ri-hypothesis-title", "Falsifiable research hypotheses", "Each hypothesis defines what to test, what data to use, and what would reject it.")}
      ${hypotheses.length ? `<div class="ri-hypothesis-list">${hypotheses.map((item, index) => `<article class="ri-hypothesis-card">
        <div class="ri-card-kicker"><span>Hypothesis ${index + 1}</span><span>Grounding ${escapeHtml(formatScore(item.grounding_score))} · testability ${escapeHtml(formatScore(item.testability_score))}</span></div>
        <h3>${escapeHtml(item.title)}</h3>
        <p class="ri-hypothesis-statement">${escapeHtml(item.hypothesis)}</p>
        <dl class="ri-inline-meta">
          <div><dt>Expected direction</dt><dd>${escapeHtml(item.expected_direction)}</dd></div>
          <div><dt>Time horizon</dt><dd>${escapeHtml(item.time_horizon)}</dd></div>
          <div><dt>Unit of analysis</dt><dd>${escapeHtml(item.unit_of_analysis)}</dd></div>
          <div><dt>Novelty assessment</dt><dd>${escapeHtml(item.novelty_assessment)}</dd></div>
        </dl>
        <div class="ri-test-grid">
          <div><h4>Required data</h4>${renderStringList(item.required_data)}</div>
          <div class="ri-confirm"><h4>Confirmation conditions</h4>${renderStringList(item.confirmation_conditions)}</div>
          <div class="ri-falsify"><h4>Falsification conditions</h4>${renderStringList(item.falsification_conditions)}</div>
          <div><h4>Confounders</h4>${renderStringList(item.confounders)}</div>
        </div>
        ${renderRefs(item.evidence_ids)}
      </article>`).join("")}</div>` : `<div class="ri-withheld"><h3>No publishable research hypothesis</h3><p>No sufficiently grounded research or trade hypothesis can be generated from this disclosure change.</p></div>`}
    </section>`;
  }

  function renderQuestions(packet) {
    const questions = list(packet.analyst_questions);
    return `<section class="ri-packet-section" aria-labelledby="ri-questions-title">
      ${sectionHeading("06", "ri-stage-review", "ANALYST REVIEW", "ri-questions-title", "Analyst questions", "Follow-up questions tied to the specific disclosure and identifiable data.")}
      ${questions.length ? `<ol class="ri-question-list">${questions.map((item) => `<li><h3>${escapeHtml(item.question)}</h3><p>${escapeHtml(item.why_it_matters)}</p><details><summary>Required data and evidence</summary><div><h4>Required data</h4>${renderStringList(item.required_data)}${renderRefs(item.evidence_ids)}</div></details></li>`).join("")}</ol>` : `<p class="ri-empty-inline">No analyst questions were published.</p>`}
    </section>`;
  }

  function renderEntities(packet) {
    const entities = list(packet.affected_entities);
    return `<section class="ri-packet-section" aria-labelledby="ri-entities-title">
      ${sectionHeading("07", "ri-stage-interpretation", "SYSTEM INTERPRETATION", "ri-entities-title", "Affected entities", "Potential exposure maps for investigation—not asserted outcomes.")}
      ${entities.length ? `<div class="ri-card-grid">${entities.map((item) => `<article>
        <div class="ri-card-kicker"><span>${escapeHtml(item.entity_or_group)}</span><span>Confidence ${escapeHtml(formatScore(item.confidence))}</span></div>
        <h3>${escapeHtml(item.relationship)}</h3>
        <p><strong>Possible effect:</strong> ${escapeHtml(item.possible_effect)}</p>
        <p>${escapeHtml(item.reason)}</p>
        ${renderRefs(item.evidence_ids)}
      </article>`).join("")}</div>` : `<p class="ri-empty-inline">No affected entity was sufficiently grounded.</p>`}
    </section>`;
  }

  function renderScenarios(packet) {
    const scenarios = packet.scenario_analysis || {};
    const labels = [["bull", "Bull"], ["base", "Base"], ["bear", "Bear"]];
    return `<section class="ri-packet-section" aria-labelledby="ri-scenarios-title">
      ${sectionHeading("08", "ri-stage-hypothesis", "AI-GENERATED HYPOTHESIS", "ri-scenarios-title", "Bull, base, and bear scenarios", "Conditional research frames, not forecasts.")}
      <div class="ri-scenario-grid">${labels.map(([key, label]) => {
        const scenario = scenarios[key] || {};
        return `<article class="ri-scenario-${key}">
          <span class="ri-scenario-label">${label}</span>
          <h3>${escapeHtml(text(scenario.scenario))}</h3>
          <h4>Conditions</h4>${renderStringList(scenario.conditions)}
          <h4>Implications</h4>${renderStringList(scenario.implications)}
          ${renderRefs(scenario.evidence_ids)}
        </article>`;
      }).join("")}</div>
    </section>`;
  }

  function renderTrade(packet) {
    const trade = packet.illustrative_trade_hypothesis || {};
    return `<section class="ri-packet-section" aria-labelledby="ri-trade-title">
      ${sectionHeading("09", "ri-stage-hypothesis", "AI-GENERATED HYPOTHESIS", "ri-trade-title", TRADE_TITLE, "Optional market expression for further research; no instruction to transact.")}
      <div class="ri-trade-guard">
        <div class="ri-trade-status">
          <div><strong>Packet trade status</strong>${statusPill(trade.status || "INSUFFICIENT_EVIDENCE")}</div>
          <div><strong>Trade readiness</strong>${statusPill(trade.trade_readiness || "NOT_READY")}</div>
          <div><strong>Candidate view</strong><span>${escapeHtml(text(trade.candidate_view, "insufficient evidence"))}</span></div>
          <div><strong>Instrument class to investigate</strong><span>${escapeHtml(text(trade.preferred_instrument_class_to_investigate, "no instrument identified"))}</span></div>
          <div><strong>Expected horizon</strong><span>${escapeHtml(text(trade.expected_horizon))}</span></div>
        </div>
        <div class="ri-trade-rationale"><h3>Instrument rationale</h3><p>${escapeHtml(text(trade.instrument_rationale))}</p><p><strong>Readiness reason:</strong> ${escapeHtml(text(trade.trade_readiness_reason))}</p>${renderRefs(trade.evidence_ids)}</div>
        <div class="ri-test-grid">
          <div><h4>Entry or confirmation conditions</h4>${renderStringList(trade.entry_or_confirmation_conditions)}</div>
          <div class="ri-falsify"><h4>Invalidation conditions</h4>${renderStringList(trade.invalidation_conditions)}</div>
          <div><h4>Key risks</h4>${renderStringList(trade.key_risks)}</div>
          <div><h4>Market data required before action</h4>${renderStringList(trade.market_data_required_before_action)}</div>
          <div class="ri-test-wide"><h4>Liquidity and cost checks</h4>${renderStringList(trade.liquidity_and_cost_checks)}</div>
        </div>
        <ul class="ri-guardrails" aria-label="Trade hypothesis guardrails">
          <li>Current market data used: <strong>${trade.current_market_data_used === false ? "No" : "Not verified"}</strong></li>
          <li>Analyst review required: <strong>${trade.analyst_review_required === true ? "Yes" : "Not verified"}</strong></li>
          <li>No position size generated: <strong>${trade.no_position_size_generated === true ? "Yes" : "Not verified"}</strong></li>
        </ul>
      </div>
    </section>`;
  }

  function renderSkeptic(packet) {
    const review = packet.skeptical_review || {};
    return `<section class="ri-packet-section" aria-labelledby="ri-skeptic-title">
      ${sectionHeading("10", "ri-stage-review", "ANALYST REVIEW", "ri-skeptic-title", "Skeptical review", "Adversarial objections, alternatives, and removed claims.")}
      <div class="ri-review-summary">
        <div><strong>Final review status</strong>${statusPill(review.final_review_status || "NOT_REVIEWED")}</div>
        <div><strong>Critical grounding defect</strong><span>${review.critical_grounding_defect === true ? "Yes" : review.critical_grounding_defect === false ? "No" : "Not reviewed"}</span></div>
        <p>${escapeHtml(text(review.review_summary))}</p>
      </div>
      <div class="ri-review-grid">
        <article><h3>Critical objections</h3>${renderStringList(review.critical_objections)}</article>
        <article><h3>Alternative explanations</h3>${renderStringList(review.alternative_explanations)}</article>
        <article><h3>Pricing or attention concerns</h3>${renderStringList(review.pricing_or_attention_concerns)}</article>
        <article><h3>Unsupported claims removed</h3>${renderStringList(review.unsupported_claims_removed, "No removed claim reported.")}</article>
      </div>
      <p class="ri-reviewed-evidence"><strong>Evidence reviewed:</strong> ${renderRefs(review.evidence_ids_reviewed)}</p>
    </section>`;
  }

  function renderAnalystControls(packet) {
    const overlay = analystOverlay(packet);
    const actions = [
      ["ACCEPTED", "Accept"],
      ["ACCEPTED_WITH_EDITS", "Edit"],
      ["REJECTED", "Reject"],
      ["ESCALATED", "Escalate"],
      ["SAVED_FOR_DISCUSSION", "Save for discussion"]
    ];
    return `<section class="ri-packet-section" aria-labelledby="ri-disposition-title">
      ${sectionHeading("11", "ri-stage-review", "ANALYST REVIEW", "ri-disposition-title", "Analyst disposition", "Your decision is stored only in this browser and never changes the source packet.")}
      <fieldset class="ri-disposition-fieldset">
        <legend>Choose an analyst disposition</legend>
        <div class="ri-disposition-actions">${actions.map(([status, label]) => `<button type="button" class="${status === "REJECTED" ? "ghost" : "secondary"}" data-ri-disposition="${status}" aria-pressed="${overlay.status === status}">${label}</button>`).join("")}</div>
      </fieldset>
      <label class="ri-notes-label" for="ri-analyst-notes">Analyst notes
        <textarea id="ri-analyst-notes" maxlength="12000" placeholder="Record edits, concerns, required checks, or the reason for your disposition.">${escapeHtml(overlay.analyst_notes)}</textarea>
      </label>
      <p class="ri-local-status">Current local status: <strong id="ri-current-disposition">${escapeHtml(overlay.status)}</strong>${overlay.review_timestamp ? ` · reviewed ${escapeHtml(formatTimestamp(overlay.review_timestamp))}` : ""}</p>
    </section>
    <section class="ri-packet-section" aria-labelledby="ri-save-title">
      ${sectionHeading("12", "ri-stage-review", "ANALYST REVIEW", "ri-save-title", "Save or export", "Preserve analyst judgment as a separate overlay; the frozen packet remains immutable.")}
      <div class="ri-save-panel">
        <div><h3>Browser-local record</h3><p>Save the current notes and status on this device. Clearing browser storage removes the overlay.</p></div>
        <div class="button-row">
          <button type="button" id="ri-save-overlay">Save local review</button>
          <button type="button" class="secondary" id="ri-export-packet">Export evidence and hypothesis packet</button>
        </div>
      </div>
      <p class="ri-export-boundary">The export contains the unchanged source packet and a separately labeled analyst overlay. It contains no ex-post outcome.</p>
    </section>`;
  }

  function renderDetail(packet) {
    const container = byId("research-idea-detail");
    const classification = packet.frozen_classification || {};
    const review = packet.skeptical_review || {};
    const overlay = analystOverlay(packet);
    document.title = `${packet.ticker} AI Research Idea | Pure News Intelligence`;
    byId("idea-title").textContent = `${packet.issuer} (${packet.ticker})`;
    byId("idea-subtitle").textContent = `${classification.category || "Disclosure change"} · ${formatDate(packet.filing_date)} · ${packet.section}`;
    byId("idea-packet-status").textContent = packet.packet_status;
    byId("idea-packet-status").className = `status ${statusClass(packet.packet_status)}`;
    byId("idea-review-status").textContent = review.final_review_status || "NOT_REVIEWED";
    byId("idea-formation-time").textContent = formatTimestamp(packet.formation_timestamp);
    byId("idea-disposition-summary").textContent = overlay.status;
    container.innerHTML = [
      renderEvidence(packet),
      renderInterpretation(packet),
      renderClassification(packet),
      renderMechanisms(packet),
      renderHypotheses(packet),
      renderQuestions(packet),
      renderEntities(packet),
      renderScenarios(packet),
      renderTrade(packet),
      renderSkeptic(packet),
      renderAnalystControls(packet)
    ].join("");
    container.setAttribute("aria-busy", "false");
    bindAnalystControls(packet);
    byId("research-idea-live").textContent = `${packet.ticker} research idea loaded. Packet status ${humanize(packet.packet_status)}.`;
  }

  function bindAnalystControls(packet) {
    const notes = byId("ri-analyst-notes");
    const current = byId("ri-current-disposition");
    const heroDisposition = byId("idea-disposition-summary");
    const live = byId("research-idea-live");

    function persist(status, message) {
      const existing = analystOverlay(packet);
      const noteValue = notes.value.trim();
      const overlay = {
        status: status || existing.status,
        analyst_notes: noteValue,
        edited_fields: noteValue || status === "ACCEPTED_WITH_EDITS" ? ["/analyst_disposition/analyst_notes"] : [],
        review_timestamp: new Date().toISOString(),
        saved_locally_only: true
      };
      const saved = saveOverlay(packet, overlay);
      current.textContent = overlay.status;
      heroDisposition.textContent = overlay.status;
      all("[data-ri-disposition]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.riDisposition === overlay.status)));
      live.textContent = saved ? message : "The browser blocked local storage. Your packet remains unchanged.";
      return overlay;
    }

    all("[data-ri-disposition]").forEach((button) => button.addEventListener("click", () => {
      const status = button.dataset.riDisposition;
      persist(status, `${humanize(status)} saved locally for ${packet.ticker}.`);
      if (status === "ACCEPTED_WITH_EDITS") notes.focus();
    }));
    byId("ri-save-overlay").addEventListener("click", () => persist(null, `Local analyst review saved for ${packet.ticker}.`));
    byId("ri-export-packet").addEventListener("click", () => {
      const existing = analystOverlay(packet);
      const noteValue = notes.value.trim();
      const overlay = noteValue === existing.analyst_notes ? existing : persist(null, `Local review saved and export prepared for ${packet.ticker}.`);
      downloadJson(packet, overlay);
      live.textContent = `Export prepared for ${packet.ticker}. The source packet was not changed.`;
    });
  }

  async function initializeDetail() {
    const container = byId("research-idea-detail");
    try {
      const { payload, entries } = await loadIndex();
      const requested = new URLSearchParams(location.search).get("change_id");
      const preferred = requested || payload.guided_example_change_id || GUIDED_CHANGE_ID;
      const entry = entries.find((item) => entryId(item) === preferred)
        || (!requested ? entries.find((item) => item.ticker === "KHC") : null)
        || (!requested ? entries.find((item) => item.packet_status === "PUBLISHABLE") : null)
        || (!requested ? entries[0] : null);
      if (!entry) {
        container.innerHTML = errorMarkup("Research idea not yet generated for this record.", "Return to the gallery to browse available validated packets.");
        container.setAttribute("aria-busy", "false");
        byId("idea-title").textContent = "Research idea unavailable";
        byId("idea-subtitle").textContent = "No frozen packet is indexed for the requested disclosure change.";
        byId("idea-packet-status").textContent = "NOT AVAILABLE";
        byId("idea-review-status").textContent = "NOT AVAILABLE";
        byId("idea-formation-time").textContent = "NOT AVAILABLE";
        return;
      }
      const packet = await loadPacket(entry);
      renderDetail(packet);
    } catch (error) {
      container.innerHTML = errorMarkup("The research idea could not be loaded", error.message, true);
      container.setAttribute("aria-busy", "false");
      byId("idea-title").textContent = "Research idea unavailable";
      byId("idea-subtitle").textContent = "The frozen public packet could not be read.";
      byId("idea-packet-status").textContent = "UNAVAILABLE";
      byId("idea-review-status").textContent = "UNAVAILABLE";
      byId("idea-formation-time").textContent = "UNAVAILABLE";
      container.querySelector("[data-ri-retry]")?.addEventListener("click", initializeDetail);
    }
  }

  function packetRecord(packet, entry) {
    const trade = packet.illustrative_trade_hypothesis || {};
    const classification = packet.frozen_classification || {};
    const hypotheses = list(packet.research_hypotheses);
    const overlay = analystOverlay(packet);
    return {
      packet,
      entry,
      issuerSearch: `${packet.issuer} ${packet.ticker}`.toLowerCase(),
      year: String(packet.filing_date || "").slice(0, 4),
      category: text(classification.category, ""),
      novelty: text(classification.novelty, ""),
      materiality: text(classification.materiality, ""),
      asset: text(trade.preferred_instrument_class_to_investigate, ""),
      horizons: [...new Set(hypotheses.map((item) => text(item.time_horizon, "")).filter(Boolean))],
      review: text(packet.skeptical_review?.final_review_status, "PENDING_REVIEW"),
      disposition: overlay.status,
      readiness: text(trade.trade_readiness, "NOT_READY"),
      evidenceScore: Number(packet.confidence?.evidence || 0),
      testabilityScore: Math.max(0, ...hypotheses.map((item) => Number(item.testability_score || 0)))
    };
  }

  function populateSelect(id, values) {
    const select = byId(id);
    [...new Set(values.filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b))).forEach((value) => select.add(new Option(value, value)));
  }

  function galleryCard(record) {
    const packet = record.packet;
    const classification = packet.frozen_classification || {};
    const hypothesis = list(packet.research_hypotheses)[0];
    const trade = packet.illustrative_trade_hypothesis || {};
    const description = hypothesis?.title || (packet.packet_status === "PUBLISHABLE" ? "Research agenda available" : "No publishable hypothesis");
    return `<article class="ri-gallery-card">
      <div class="ri-card-kicker"><span>${escapeHtml(packet.ticker)} · ${escapeHtml(formatDate(packet.filing_date))}</span>${statusPill(packet.packet_status)}</div>
      <h3>${escapeHtml(packet.issuer)}</h3>
      <p class="ri-gallery-category">${escapeHtml(text(classification.category))}</p>
      <div class="badge-row" aria-label="Packet classifications">
        <span class="badge ${escapeHtml(classification.materiality || "low")}">${escapeHtml(humanize(classification.materiality))} materiality</span>
        <span class="badge ${escapeHtml(classification.direction || "ambiguous")}">${escapeHtml(humanize(classification.direction))} direction</span>
      </div>
      <dl class="ri-gallery-meta">
        <div><dt>Novelty</dt><dd>${escapeHtml(text(classification.novelty))}</dd></div>
        <div><dt>Evidence confidence</dt><dd>${escapeHtml(formatScore(record.evidenceScore))}</dd></div>
        <div><dt>Top testability</dt><dd>${escapeHtml(formatScore(record.testabilityScore))}</dd></div>
        <div><dt>Idea review</dt><dd>${escapeHtml(record.review)}</dd></div>
        <div><dt>Analyst disposition</dt><dd>${escapeHtml(record.disposition)}</dd></div>
        <div><dt>Instrument class</dt><dd>${escapeHtml(record.asset || "no instrument identified")}</dd></div>
        <div><dt>Trade readiness</dt><dd>${escapeHtml(record.readiness)}</dd></div>
      </dl>
      <div class="ri-gallery-hypothesis"><span class="ri-stage-label ri-stage-hypothesis">AI-GENERATED HYPOTHESIS</span><p>${escapeHtml(description)}</p></div>
      <div class="card-actions"><a class="button secondary" href="research_idea.html?change_id=${encodeURIComponent(packet.change_id)}" aria-label="Open ${escapeHtml(packet.ticker)} research idea">Open research idea</a><span>${escapeHtml(text(trade.candidate_view, "insufficient evidence"))}</span></div>
    </article>`;
  }

  function initializeGalleryControls(records) {
    populateSelect("ri-filter-year", records.map((record) => record.year).sort().reverse());
    populateSelect("ri-filter-category", records.map((record) => record.category));
    populateSelect("ri-filter-novelty", records.map((record) => record.novelty));
    populateSelect("ri-filter-asset", records.map((record) => record.asset));
    populateSelect("ri-filter-horizon", records.flatMap((record) => record.horizons));
  }

  function bindGallery(records) {
    const container = byId("research-idea-gallery");
    const form = byId("research-idea-filters");
    const materialityRank = { high: 3, medium: 2, low: 1 };
    const dispositionRank = {
      ACCEPTED: 6, ACCEPTED_WITH_EDITS: 5, SAVED_FOR_DISCUSSION: 4,
      ESCALATED: 3, REJECTED: 2, UNREVIEWED: 1
    };

    function render() {
      const values = Object.fromEntries(new FormData(form).entries());
      const query = String(values.issuer || "").trim().toLowerCase();
      const filtered = records.filter((record) =>
        (!query || record.issuerSearch.includes(query))
        && (!values.year || record.year === values.year)
        && (!values.category || record.category === values.category)
        && (!values.novelty || record.novelty === values.novelty)
        && (!values.materiality || record.materiality === values.materiality)
        && (!values.asset || record.asset === values.asset)
        && (!values.horizon || record.horizons.includes(values.horizon))
        && (!values.review || record.review === values.review)
        && (!values.readiness || record.readiness === values.readiness)
      );
      const sort = values.sort || "evidence";
      filtered.sort((a, b) => {
        if (sort === "testability") return b.testabilityScore - a.testabilityScore || a.packet.change_id.localeCompare(b.packet.change_id);
        if (sort === "materiality") return (materialityRank[b.materiality] || 0) - (materialityRank[a.materiality] || 0) || b.evidenceScore - a.evidenceScore;
        if (sort === "date") return String(b.packet.filing_date).localeCompare(String(a.packet.filing_date)) || a.packet.change_id.localeCompare(b.packet.change_id);
        if (sort === "disposition") return (dispositionRank[b.disposition] || 0) - (dispositionRank[a.disposition] || 0) || a.packet.change_id.localeCompare(b.packet.change_id);
        return b.evidenceScore - a.evidenceScore || a.packet.change_id.localeCompare(b.packet.change_id);
      });
      byId("ri-gallery-count").textContent = `${filtered.length} of ${records.length} validated packets`;
      container.innerHTML = filtered.length ? filtered.map(galleryCard).join("") : `<div class="empty-state">
        <h3>No research ideas match these filters</h3>
        <p>Clear one or more filters to broaden the analyst-review queue.</p>
        <button class="secondary" type="button" data-ri-clear-empty>Clear filters</button>
      </div>`;
      container.setAttribute("aria-busy", "false");
      container.querySelector("[data-ri-clear-empty]")?.addEventListener("click", clear);
    }

    function clear() {
      all("input, select", form).forEach((control) => { control.value = control.name === "sort" ? "evidence" : ""; });
      render();
      byId("ri-filter-issuer").focus();
    }

    all("input, select", form).forEach((control) => control.addEventListener(control.type === "search" ? "input" : "change", render));
    byId("ri-clear-filters").addEventListener("click", clear);
    render();
  }

  async function initializeGallery() {
    const container = byId("research-idea-gallery");
    try {
      const { entries } = await loadIndex();
      const loaded = await Promise.allSettled(entries.map(async (entry) => ({ entry, packet: await loadPacket(entry) })));
      const records = loaded.filter((result) => result.status === "fulfilled").map((result) => packetRecord(result.value.packet, result.value.entry));
      if (!records.length) throw new Error("No validated packet could be loaded.");
      initializeGalleryControls(records);
      bindGallery(records);
      const failed = loaded.length - records.length;
      if (failed) byId("ri-gallery-count").textContent = `${records.length} packets loaded; ${failed} unavailable`;
    } catch (error) {
      container.innerHTML = errorMarkup("The idea gallery could not be loaded", error.message, true);
      container.setAttribute("aria-busy", "false");
      byId("ri-gallery-count").textContent = "Packet index unavailable";
      container.querySelector("[data-ri-retry]")?.addEventListener("click", initializeGallery);
    }
  }

  function guidedExampleMarkup(packet) {
    const evidence = packet.evidence || {};
    const mechanism = list(packet.economic_mechanisms)[0];
    const hypothesis = list(packet.research_hypotheses)[0];
    const review = packet.skeptical_review || {};
    const trade = packet.illustrative_trade_hypothesis || {};
    return `<div class="ri-guided-flow">
      <article>
        <span class="ri-guide-step">1</span><span class="ri-stage-label ri-stage-evidence">EVIDENCE</span>
        <h3>Read the changed filing language</h3>
        <blockquote tabindex="0" aria-label="Guided example current filing excerpt">${escapeHtml(text(evidence.current_excerpt))}</blockquote>
        ${sourceLink(evidence.current_source_url || packet.source_url, "Open current SEC filing")}
      </article>
      <article>
        <span class="ri-guide-step">2</span><span class="ri-stage-label ri-stage-interpretation">SYSTEM INTERPRETATION</span>
        <h3>Inspect the proposed mechanism</h3>
        <p>${escapeHtml(text(mechanism?.mechanism, "No mechanism was sufficiently grounded."))}</p>
        ${mechanism ? `<p><strong>Counterargument:</strong> ${escapeHtml(mechanism.counterargument)}</p>` : ""}
      </article>
      <article>
        <span class="ri-guide-step">3</span><span class="ri-stage-label ri-stage-hypothesis">AI-GENERATED HYPOTHESIS</span>
        <h3>Ask what would falsify it</h3>
        <p>${escapeHtml(text(hypothesis?.hypothesis, "No publishable hypothesis was generated."))}</p>
        ${hypothesis ? `<h4>Falsification conditions</h4>${renderStringList(hypothesis.falsification_conditions)}` : ""}
      </article>
      <article>
        <span class="ri-guide-step">4</span><span class="ri-stage-label ri-stage-review">ANALYST REVIEW</span>
        <h3>Confront the skeptical objection</h3>
        ${renderStringList(review.critical_objections, "No critical objection reported.")}
        <p><strong>Review status:</strong> ${escapeHtml(text(review.final_review_status))}</p>
      </article>
      <article>
        <span class="ri-guide-step">5</span><span class="ri-stage-label ri-stage-hypothesis">AI-GENERATED HYPOTHESIS</span>
        <h3>${TRADE_TITLE}</h3>
        <p><strong>${escapeHtml(text(trade.candidate_view, "insufficient evidence"))}</strong> · ${escapeHtml(text(trade.preferred_instrument_class_to_investigate, "no instrument identified"))}</p>
        <p>${escapeHtml(text(trade.trade_readiness_reason))}</p>
        ${statusPill(trade.trade_readiness || "NOT_READY")}
      </article>
      <article>
        <span class="ri-guide-step">6</span><span class="ri-stage-label ri-stage-review">ANALYST REVIEW</span>
        <h3>Record the human decision</h3>
        <p>The frozen packet remains <strong>${escapeHtml(text(packet.analyst_disposition?.status, "UNREVIEWED"))}</strong>. A professor or analyst must accept, edit, reject, escalate, or save it for discussion.</p>
        <a class="button secondary" href="research_idea.html?change_id=${encodeURIComponent(packet.change_id)}">Open the full guided packet</a>
      </article>
    </div>
    <div class="ri-stage-panel ri-stage-expost-panel">
      <span class="ri-stage-label ri-stage-expost">EX-POST OUTCOME</span>
      <p><strong>None loaded.</strong> This example was selected for evidence clarity and category teaching value—not later performance.</p>
    </div>`;
  }

  async function initializeMethodology() {
    const container = byId("research-idea-guided-example");
    try {
      const { entries } = await loadIndex();
      const entry = entries.find((item) => entryId(item) === GUIDED_CHANGE_ID || item.ticker === "KHC");
      if (!entry) {
        container.innerHTML = errorMarkup("Guided packet not yet available", "The methodology remains available; the frozen Kraft Heinz packet has not been indexed.");
        container.setAttribute("aria-busy", "false");
        return;
      }
      const packet = await loadPacket(entry);
      container.innerHTML = guidedExampleMarkup(packet);
      container.setAttribute("aria-busy", "false");
    } catch (error) {
      container.innerHTML = errorMarkup("The guided packet could not be loaded", error.message, true);
      container.setAttribute("aria-busy", "false");
      container.querySelector("[data-ri-retry]")?.addEventListener("click", initializeMethodology);
    }
  }

  if (page === "detail") initializeDetail();
  else if (page === "gallery") initializeGallery();
  else if (page === "methodology") initializeMethodology();

  // Keep the immutable disclaimer visible even if a malformed packet supplies different text.
  all(".ri-disclaimer").forEach((element) => {
    if (!element.textContent.includes(DISCLAIMER)) element.append(document.createTextNode(` ${DISCLAIMER}`));
  });
})();
