(() => {
  "use strict";

  const page = document.body.dataset.researchIdeasPage;
  if (!page) return;

  const dataRoot = "data/research_ideas/v2";
  const storageKey = "pni-public-research-idea-review-v1";
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
  const list = (values, empty = "None recorded in the frozen packet.") => values?.length
    ? `<ul>${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul>`
    : `<p class="public-empty">${escapeHtml(empty)}</p>`;
  const loadJson = async (url) => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Unable to load ${url} (HTTP ${response.status})`);
    return response.json();
  };
  const evidenceBlock = (label, text, meta = "") => `
    <article class="public-evidence-card">
      <p class="public-card-label">${escapeHtml(label)}</p>
      ${meta ? `<p class="public-evidence-meta">${escapeHtml(meta)}</p>` : ""}
      <blockquote tabindex="0">${escapeHtml(text || "Not separately retained in the public-safe view.")}</blockquote>
    </article>`;
  const sectionHeading = (number, stage, title, description = "") => `
    <div class="public-section-heading">
      <div><span class="public-section-number">${number}</span><span class="public-stage public-stage-${stage.toLowerCase()}">${escapeHtml(stage)}</span></div>
      <h2>${escapeHtml(title)}</h2>
      ${description ? `<p>${escapeHtml(description)}</p>` : ""}
    </div>`;
  const download = (filename, contents, type) => {
    const blob = new Blob([contents], { type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  };
  const readReviews = () => {
    try { return JSON.parse(localStorage.getItem(storageKey) || "{}"); }
    catch { return {}; }
  };

  function renderGallery(manifest) {
    const summary = manifest.summary;
    document.querySelector("#public-idea-metrics").innerHTML = [
      [summary.cases_reviewed, "Cases reviewed"],
      [summary.publishable_hypotheses, "Publishable hypotheses"],
      [summary.safe_failures, "Safe failures"],
      [summary.actionable_trade_views, "Actionable trade views"],
      ["100%", "Evidence coverage for published packets"]
    ].map(([value, label], index) => `<article class="metric ${index === 1 ? "primary" : ""}"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></article>`).join("");
    document.querySelector("#public-idea-metrics").setAttribute("aria-busy", "false");

    document.querySelector("#public-idea-publishable").innerHTML = manifest.publishable.map((item) => `
      <article class="public-idea-card public-published-card">
        <div class="public-card-topline"><span class="status success">PUBLISHABLE HYPOTHESIS</span><span class="status outline">${escapeHtml(item.skeptic_status)}</span></div>
        <h3>${escapeHtml(item.issuer)} (${escapeHtml(item.ticker)})</h3>
        <p class="public-card-category">${escapeHtml(item.category)}</p>
        <dl class="public-card-facts">
          <div><dt>Filed</dt><dd>${escapeHtml(item.filing_date)}</dd></div>
          <div><dt>Section</dt><dd>${escapeHtml(item.section)}</dd></div>
          <div><dt>Final novelty</dt><dd>${escapeHtml(item.final_novelty)}</dd></div>
          <div><dt>Evidence coverage</dt><dd>${Number(item.evidence_coverage_ratio).toFixed(2)}</dd></div>
          <div><dt>Hypotheses</dt><dd>${item.hypothesis_count}</dd></div>
          <div><dt>Trade readiness</dt><dd>NO ACTIONABLE VIEW</dd></div>
        </dl>
        <div class="card-actions"><a class="button secondary" href="${escapeHtml(item.route)}">Explore research hypothesis</a></div>
      </article>`).join("");
    document.querySelector("#public-idea-publishable").setAttribute("aria-busy", "false");

    const efx = manifest.safe_failures.find((item) => item.ticker === "EFX");
    document.querySelector("#public-idea-efx-feature").innerHTML = `
      <article class="public-efx-feature">
        <div><p class="public-stage public-stage-rejected">CORRECT REJECTION</p><h3>${escapeHtml(efx.issuer)} (${escapeHtml(efx.ticker)})</h3><p>The selected prior excerpt omitted the already-disclosed $125 million conditional top-up. The $346.7 million remaining balance and the approximately $345 million cash deposit had different financial roles.</p></div>
        <ul><li>Incomplete prior display excerpt identified</li><li>Unsupported liquidity, reserve, and bondholder claims removed</li><li><strong>No actionable view</strong></li></ul>
        <a class="button secondary" href="${escapeHtml(efx.route)}">View grounding correction</a>
      </article>`;
    document.querySelector("#public-idea-efx-feature").setAttribute("aria-busy", "false");

    const safeFailures = manifest.safe_failures.filter((item) => item.ticker !== "EFX");
    const grid = document.querySelector("#public-idea-safe-failures");
    const filter = document.querySelector("#safe-failure-filter");
    const draw = () => {
      const visible = safeFailures.filter((item) => filter.value === "all" || item.final_status === filter.value);
      grid.innerHTML = visible.map((item) => `<article class="public-safe-failure-card">
        <span class="status danger">${escapeHtml(item.final_status)}</span>
        <h3>${escapeHtml(item.issuer)} (${escapeHtml(item.ticker)})</h3>
        <p>${escapeHtml(item.reason)}</p>
        <dl><div><dt>Published packet</dt><dd>No</dd></div><div><dt>Actionable view</dt><dd>No</dd></div></dl>
      </article>`).join("") || `<div class="empty-state"><h3>No failures match this filter</h3><p>Choose another final disposition.</p></div>`;
      document.querySelector("#safe-failure-count").textContent = `${visible.length} of ${safeFailures.length} safe failures shown`;
      grid.setAttribute("aria-busy", "false");
    };
    filter.addEventListener("change", draw);
    draw();
    document.querySelector("#public-ideas-live").textContent = "Frozen public research idea manifest loaded.";
  }

  function quantityTable(quantities) {
    if (!quantities.length) return `<p class="public-empty">No financial quantity was retained in this frozen packet.</p>`;
    return `<div class="public-table-wrap" tabindex="0" aria-label="Scrollable financial quantity table"><table class="public-data-table">
      <thead><tr><th>Amount</th><th>Role</th><th>Period</th><th>Conditionality</th><th>Paid / remaining</th></tr></thead>
      <tbody>${quantities.map((item) => `<tr><td>${escapeHtml(item.raw_text)}</td><td>${escapeHtml(item.role)}</td><td>${escapeHtml(item.date || "Not specified")}</td><td>${escapeHtml(item.conditionality)}</td><td>${escapeHtml(item.payment_status)}</td></tr>`).join("")}</tbody>
    </table></div>`;
  }

  function renderDetail(packet) {
    const identity = packet.identity;
    const publication = packet.publication;
    const source = packet.source_evidence;
    const novelty = packet.novelty;
    const hypothesis = packet.research_hypotheses[0];
    document.title = `${identity.ticker} Research Hypothesis | Pure News Intelligence`;
    document.querySelector("#public-idea-title").textContent = `${identity.issuer} (${identity.ticker})`;
    document.querySelector("#public-idea-subtitle").textContent = `${identity.filing_date} · ${identity.section} · ${novelty.final_novelty}`;
    document.querySelector("#public-idea-summary").innerHTML = `
      <p class="label">Frozen packet summary</p><p><span class="status success">PASS_HYPOTHESIS_ONLY</span></p>
      <dl><dt>Evidence coverage</dt><dd>${Number(publication.evidence_coverage_ratio).toFixed(2)}</dd><dt>Trade status</dt><dd>NO ACTIONABLE VIEW</dd><dt>Analyst review</dt><dd>Required</dd></dl>`;

    const facts = packet.interpretation_layers.facts;
    const inferences = packet.interpretation_layers.inferences;
    const related8k = source.related_prior_8k || [];
    const relatedNews = source.related_prior_news || [];
    const earliest = source.earliest_occurrence;
    const evidenceIds = Object.entries(source.display_evidence_ids).map(([key, value]) => `<li><strong>${escapeHtml(key.replaceAll("_", " "))}:</strong> <code>${escapeHtml(value)}</code></li>`).join("");
    const offsets = Object.entries(source.display_evidence_offsets).map(([key, value]) => `<li><strong>${escapeHtml(key)}:</strong> ${value.start}–${value.end}</li>`).join("");
    const factCards = facts.length ? facts.map((claim) => `<article><span class="public-stage public-stage-fact">FACT</span><p>${escapeHtml(claim.wording)}</p><small>${escapeHtml(claim.support_status)} · confidence ${Number(claim.confidence).toFixed(2)}</small></article>`).join("") : `<p class="public-empty">No separately retained fact.</p>`;
    const inferenceCards = inferences.length ? inferences.map((claim) => `<article><span class="public-stage public-stage-inference">INFERENCE</span><p>${escapeHtml(claim.wording)}</p><small>${escapeHtml(claim.support_status)} · confidence ${Number(claim.confidence).toFixed(2)}</small></article>`).join("") : `<p class="public-empty">No separately retained inference.</p>`;
    const questions = {
      "Company fundamentals": hypothesis.required_data,
      "Management clarification": ["What issuer-specific control or assumption changed, if any?"],
      "Peer / sector comparison": ["Does comparable peer disclosure support an issuer-specific interpretation?"],
      "Market-data checks": ["What contemporaneous valuation, liquidity, and transaction-cost data would be required before trade research?"],
      "Counterarguments and risks": hypothesis.confounders
    };
    const questionBlocks = Object.entries(questions).map(([group, values]) => `<article><h3>${escapeHtml(group)}</h3>${list(values)}</article>`).join("");
    const reviewState = readReviews()[identity.change_id] || { disposition: "UNREVIEWED", notes: "" };
    const dispositions = ["Accept", "Accept with edits", "Reject", "Escalate", "Save for discussion"];
    const dispositionButtons = dispositions.map((value) => `<button type="button" class="secondary" data-public-disposition="${escapeHtml(value)}" aria-pressed="${String(reviewState.disposition === value)}">${escapeHtml(value)}</button>`).join("");

    const detail = document.querySelector("#public-idea-detail");
    detail.innerHTML = `
      <section class="public-packet-section" aria-labelledby="public-source-title">
        ${sectionHeading("A", "Evidence", "Source evidence", "Direct filing evidence and immutable provenance from the frozen packet.")}
        <div class="public-source-ledger"><div><strong>Issuer</strong><span>${escapeHtml(identity.issuer)} (${escapeHtml(identity.ticker)})</span></div><div><strong>Filed</strong><span>${escapeHtml(identity.filing_date)}</span></div><div><strong>Section</strong><span>${escapeHtml(identity.section)}</span></div><div><strong>Source</strong><a href="${escapeHtml(identity.sec_url)}" target="_blank" rel="noopener">Open SEC filing</a></div></div>
        <p><span class="status success">✓ Full prior-filing evidence checked</span></p>
        <div class="public-evidence-grid">${evidenceBlock("Prior excerpt", source.prior_excerpt)}${evidenceBlock("Current excerpt", source.current_excerpt)}</div>
        <div class="public-change-grid">${evidenceBlock("Removed text", source.removed_text)}${evidenceBlock("Added text", source.added_text)}</div>
        <details><summary>Evidence identifiers and offsets</summary><div class="public-details-body"><div><h3>Evidence IDs</h3><ul>${evidenceIds}</ul></div><div><h3>Character offsets</h3><ul>${offsets}</ul></div></div></details>
      </section>
      <section class="public-packet-section" aria-labelledby="public-novelty-title">
        ${sectionHeading("B", "Verified", "Verified novelty", "Provisional classification is separated from the full-prior result.")}
        <dl class="public-novelty-grid"><div><dt>Provisional novelty</dt><dd>${escapeHtml(novelty.provisional_novelty)}</dd></div><div><dt>Final novelty</dt><dd>${escapeHtml(novelty.final_novelty)}</dd></div><div><dt>Earliest prior occurrence</dt><dd>${escapeHtml(earliest?.filing_date || "No reliable prior occurrence identified")}</dd></div><div><dt>What is actually new</dt><dd>${escapeHtml(novelty.what_is_new)}</dd></div><div><dt>What was already known</dt><dd>${escapeHtml(novelty.what_is_not_new)}</dd></div><div><dt>Unresolved uncertainty</dt><dd>${novelty.unresolved_uncertainty.length ? escapeHtml(novelty.unresolved_uncertainty.join("; ")) : "No retrieval gap recorded"}</dd></div></dl>
        <div class="public-prior-record"><article><h3>Related prior 8-Ks</h3>${related8k.length ? list(related8k.map((item) => `${item.information_date} · ${item.accession_number}`)) : `<p>None retained in the frozen evidence packet.</p>`}</article><article><h3>Related prior news</h3>${relatedNews.length ? list(relatedNews.map((item) => item.headline || item.title || "Eligible prior headline")) : `<p>None retained in the frozen evidence packet.</p>`}</article></div>
      </section>
      <section class="public-packet-section" aria-labelledby="public-interpretation-title">
        ${sectionHeading("C", "Interpretation", "System interpretation", "Facts, inference, and uncertainty are never merged into one paragraph.")}
        <div class="public-layer-grid"><div><h3>FACT</h3>${factCards}</div><div><h3>INFERENCE</h3>${inferenceCards}</div><div><h3>UNCERTAINTY</h3>${list(packet.interpretation_layers.uncertainties)}</div></div>
      </section>
      <section class="public-packet-section" aria-labelledby="public-mechanism-title">
        ${sectionHeading("D", "Hypothesis", "Economic mechanism")}
        <p><span class="public-stage public-stage-hypothesis">${escapeHtml(packet.economic_mechanism.label)}</span></p>
        <div class="public-mechanism-flow"><span>Disclosure change</span><b aria-hidden="true">→</b><span>${escapeHtml(packet.economic_mechanism.affected_financial_driver)}</span><b aria-hidden="true">→</b><span>Possible effect</span><b aria-hidden="true">→</b><span>Research question</span></div>
        <dl class="public-mechanism-facts"><div><dt>Proposed causal chain</dt><dd>${escapeHtml(packet.economic_mechanism.proposed_causal_chain)}</dd></div><div><dt>Supporting evidence</dt><dd>${escapeHtml(packet.economic_mechanism.supporting_evidence_ids.join(", "))}</dd></div><div><dt>Counterargument</dt><dd>${escapeHtml(packet.economic_mechanism.counterargument)}</dd></div><div><dt>Confidence</dt><dd>${escapeHtml(packet.economic_mechanism.confidence)}</dd></div></dl>
      </section>
      <section class="public-packet-section" aria-labelledby="public-hypothesis-title">
        ${sectionHeading("E", "Hypothesis", "Research hypothesis")}
        <article class="public-hypothesis-panel"><p><span class="public-stage public-stage-hypothesis">${escapeHtml(hypothesis.label)}</span></p><h3>${escapeHtml(hypothesis.title)}</h3><p class="public-hypothesis-text">${escapeHtml(hypothesis.hypothesis)}</p><div class="public-hypothesis-grid"><div><strong>Testable prediction</strong><span>${escapeHtml(hypothesis.testable_prediction)}</span></div><div><strong>Expected direction</strong><span>${escapeHtml(hypothesis.expected_direction)}</span></div><div><strong>Time horizon</strong><span>${escapeHtml(hypothesis.time_horizon)}</span></div><div><strong>Unit of analysis</strong><span>${escapeHtml(hypothesis.unit_of_analysis)}</span></div><div><strong>Grounding score</strong><span>${escapeHtml(hypothesis.grounding_score)}</span></div><div><strong>Testability score</strong><span>${escapeHtml(hypothesis.testability_score)}</span></div></div><div class="public-test-grid"><div><h4>Required data</h4>${list(hypothesis.required_data)}</div><div><h4>Confirmation</h4>${list(hypothesis.confirmation_conditions)}</div><div><h4>Falsification</h4>${list(hypothesis.falsification_conditions)}</div><div><h4>Confounders</h4>${list(hypothesis.confounders)}</div></div><p class="notice"><strong>Not outcome-validated:</strong> This hypothesis has not been validated against future outcomes.</p></article>
      </section>
      <section class="public-packet-section" aria-labelledby="public-questions-title">
        ${sectionHeading("F", "Review", "Analyst questions", "Questions structure follow-up work; they do not assert new facts.")}
        <div class="public-question-grid">${questionBlocks}</div>
      </section>
      <section class="public-packet-section" aria-labelledby="public-entities-title">
        ${sectionHeading("G", "Evidence", "Affected entities and instruments")}
        <div class="public-withheld"><h3>No grounded instrument relationship established</h3><p>${escapeHtml(packet.affected_entities_and_instruments.status)}</p></div>
      </section>
      <section class="public-packet-section" aria-labelledby="public-scenarios-title">
        ${sectionHeading("H", "Interpretation", "Bull, base, and bear scenarios")}
        <p class="notice"><strong>Scenarios are structured research frames, not forecasts.</strong></p>
        <div class="public-withheld"><h3>Not produced by the frozen bounded packet</h3><p>No scenario content is added in the public presentation layer.</p></div>
      </section>
      <section class="public-packet-section" aria-labelledby="public-trade-title">
        ${sectionHeading("I", "Review", "Trade-research status")}
        <details class="public-trade-details"><summary>NO ACTIONABLE TRADE VIEW</summary><div><dl><dt>Candidate bias</dt><dd>${escapeHtml(packet.trade_research.candidate_bias)}</dd><dt>Instrument class</dt><dd>${escapeHtml(packet.trade_research.instrument_class || "None established")}</dd><dt>Missing market checks</dt><dd>${packet.trade_research.missing_market_checks.length ? escapeHtml(packet.trade_research.missing_market_checks.join("; ")) : "No market-data workflow was authorized"}</dd><dt>Reason readiness failed</dt><dd>${escapeHtml(packet.trade_research.readiness_failure_reason)}</dd></dl></div></details>
      </section>
      <section class="public-packet-section" aria-labelledby="public-skeptic-title">
        ${sectionHeading("J", "Skeptic", "Skeptical review")}
        <div class="public-skeptic-panel"><h3>Strongest objections</h3>${list(packet.skeptical_review.strongest_objections)}<h3>Alternate explanation</h3><p>${escapeHtml(packet.skeptical_review.alternate_explanation)}</p><h3>Unsupported claims removed</h3>${list(packet.skeptical_review.unsupported_claims_removed)}<p><strong>Final skeptic status:</strong> <span class="status warning">${escapeHtml(packet.skeptical_review.final_status)}</span></p></div>
      </section>
      <section class="public-packet-section" aria-labelledby="public-quantities-title">
        ${sectionHeading("K", "Evidence", "Financial quantities")}
        ${quantityTable(packet.financial_quantities)}
      </section>
      <section class="public-packet-section" aria-labelledby="public-disposition-title">
        ${sectionHeading("L", "Decision", "Analyst disposition", "Controls and notes persist in this browser only and never modify frozen JSON.")}
        <div class="public-disposition-actions" role="group" aria-label="Analyst disposition">${dispositionButtons}</div>
        <label class="public-notes-label" for="public-analyst-notes">Local analyst notes<textarea id="public-analyst-notes" rows="5" placeholder="Saved in this browser only">${escapeHtml(reviewState.notes)}</textarea></label>
        <div class="button-row"><button type="button" id="public-save-review">Save locally</button><button type="button" class="secondary" id="public-export-json">Export JSON</button><button type="button" class="secondary" id="public-export-markdown">Export Markdown</button><button type="button" class="ghost" id="public-print">Print / save as PDF</button></div>
        <p id="public-local-status">Current local disposition: ${escapeHtml(reviewState.disposition)}</p>
      </section>`;
    detail.setAttribute("aria-busy", "false");

    let selectedDisposition = reviewState.disposition;
    detail.querySelectorAll("[data-public-disposition]").forEach((button) => button.addEventListener("click", () => {
      selectedDisposition = button.dataset.publicDisposition;
      detail.querySelectorAll("[data-public-disposition]").forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
      document.querySelector("#public-local-status").textContent = `Current local disposition: ${selectedDisposition} (not yet saved)`;
    }));
    document.querySelector("#public-save-review").addEventListener("click", () => {
      const reviews = readReviews();
      reviews[identity.change_id] = { disposition: selectedDisposition, notes: document.querySelector("#public-analyst-notes").value };
      localStorage.setItem(storageKey, JSON.stringify(reviews));
      document.querySelector("#public-local-status").textContent = `Current local disposition: ${selectedDisposition} · saved in this browser`;
      document.querySelector("#public-idea-live").textContent = `Local review saved as ${selectedDisposition}.`;
    });
    document.querySelector("#public-export-json").addEventListener("click", () => download(`${identity.ticker.toLowerCase()}-research-hypothesis.json`, `${JSON.stringify(packet, null, 2)}\n`, "application/json"));
    document.querySelector("#public-export-markdown").addEventListener("click", () => {
      const markdown = `# ${identity.issuer} (${identity.ticker}) — Experimental Research Hypothesis\n\n${packet.experimental_disclaimer}\n\n## Evidence\n\n**Prior:** ${source.prior_excerpt}\n\n**Current:** ${source.current_excerpt}\n\n## Verified novelty\n\n- Final novelty: ${novelty.final_novelty}\n- What is new: ${novelty.what_is_new}\n- What is not new: ${novelty.what_is_not_new}\n\n## Research hypothesis\n\n${hypothesis.hypothesis}\n\n**Testable prediction:** ${hypothesis.testable_prediction}\n\n**Falsification:** ${hypothesis.falsification_conditions.join("; ")}\n\n## Skeptical review\n\n${packet.skeptical_review.strongest_objections.join("; ")}\n\n## Trade-research status\n\nNO ACTIONABLE TRADE VIEW\n`;
      download(`${identity.ticker.toLowerCase()}-research-hypothesis.md`, markdown, "text/markdown");
    });
    document.querySelector("#public-print").addEventListener("click", () => window.print());
    document.querySelector("#public-idea-live").textContent = `${identity.ticker} frozen public-safe research hypothesis loaded.`;
  }

  function renderEfx(packet) {
    const review = packet.full_prior_evidence_review;
    const result = packet.final_result;
    const target = document.querySelector("#public-efx-detail");
    target.innerHTML = `
      <section class="public-packet-section public-rejected-section" aria-labelledby="efx-v1-title">
        ${sectionHeading("01", "Rejected", "Rejected V1 interpretation")}
        <p><span class="public-stage public-stage-rejected">${escapeHtml(packet.rejected_v1_interpretation.label)}</span></p>
        ${list(packet.rejected_v1_interpretation.defects)}
      </section>
      <section class="public-packet-section" aria-labelledby="efx-evidence-title">
        ${sectionHeading("02", "Evidence", "Full-prior evidence review")}
        <p><span class="status success">✓ Full prior-filing evidence checked</span></p>
        <div class="public-evidence-grid">${evidenceBlock("Prior 2020 filing · outside selected excerpt", review.prior_top_up_evidence.text, `${review.prior_top_up_evidence.evidence_id} · paragraph ${review.prior_top_up_evidence.paragraph_number}`)}${evidenceBlock("Current settlement finality", review.settlement_finality_evidence.text, `${review.settlement_finality_evidence.evidence_id} · paragraph ${review.settlement_finality_evidence.paragraph_number}`)}</div>
        ${evidenceBlock("Current deposit confirmation", review.deposit_evidence.text, `${review.deposit_evidence.evidence_id} · paragraph ${review.deposit_evidence.paragraph_number}`)}
        <div class="public-table-wrap" tabindex="0" aria-label="Scrollable EFX financial role table"><table class="public-data-table"><thead><tr><th>Amount</th><th>Correct role</th><th>Novelty result</th></tr></thead><tbody>${review.quantity_roles.map((item) => `<tr><td>${escapeHtml(item.amount)}</td><td>${escapeHtml(item.correct_role)}</td><td>${escapeHtml(item.novelty_result)}</td></tr>`).join("")}</tbody></table></div>
        <p class="public-incomparable-warning"><strong>${escapeHtml(review.comparison_status)}</strong> — these amounts cannot be treated as substitutes because their financial roles differ.</p>
      </section>
      <section class="public-packet-section" aria-labelledby="efx-result-title">
        ${sectionHeading("03", "Skeptic", "Final result")}
        <div class="public-result-grid"><article><h3>Defensible update</h3>${list(result.defensible_update)}</article><article class="public-rejected-claims"><h3>Rejected claims</h3>${list(result.rejected_claims)}</article><article><h3>Final disposition</h3><p><span class="status danger">${escapeHtml(result.packet_disposition)}</span></p><p><strong>${escapeHtml(result.trade_research_status)}</strong></p></article></div>
        <blockquote class="public-value-callout">${escapeHtml(packet.value_statement)}</blockquote>
      </section>`;
    target.setAttribute("aria-busy", "false");
  }

  const run = page === "gallery"
    ? () => loadJson(`${dataRoot}/manifest.json`).then(renderGallery)
    : page === "detail"
      ? () => loadJson(`${dataRoot}/${document.body.dataset.publicIdea}.json`).then(renderDetail)
      : page === "efx"
        ? () => loadJson(`${dataRoot}/efx_rejection.json`).then(renderEfx)
        : () => Promise.resolve();

  run().catch((error) => {
    const target = document.querySelector("#public-idea-detail, #public-efx-detail, #public-idea-publishable");
    if (target) {
      target.innerHTML = `<div class="error-state"><h2>Unable to load frozen research idea data</h2><p>${escapeHtml(error.message)}</p></div>`;
      target.setAttribute("aria-busy", "false");
    }
  });
})();
