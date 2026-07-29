(() => {
  "use strict";

  const page = document.body.dataset.riV2Page;
  if (!page) return;

  const root = "data/research_idea_packets/v2";
  const storageKey = "pni-research-idea-v2-dispositions";
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
  const list = (values, empty = "None recorded.") => values?.length
    ? `<ul>${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul>`
    : `<p class="ri-empty-inline">${escapeHtml(empty)}</p>`;
  const statusClass = (value) => value === "PUBLISHABLE" ? "success" : value.startsWith("REJECT") ? "danger" : "warning";
  const loadJson = async (url) => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  };
  const evidenceCard = (title, text, current = false) => `
    <article class="ri-excerpt ${current ? "ri-current" : ""}">
      <p class="ri-card-kicker">${escapeHtml(title)}</p>
      <blockquote tabindex="0">${escapeHtml(text || "Not available.")}</blockquote>
    </article>`;

  function quantityTable(packet) {
    if (!packet.financial_quantities.length) return `<p class="ri-empty-inline">No financial quantity was identified.</p>`;
    return `<div class="ri-v2-table-wrap" tabindex="0" aria-label="Scrollable financial quantity table"><table class="ri-v2-table">
      <thead><tr><th>Amount</th><th>Role</th><th>Period</th><th>Conditionality</th><th>Payment basis</th></tr></thead>
      <tbody>${packet.financial_quantities.map((item) => `<tr>
        <td>${escapeHtml(item.raw_text)}</td><td>${escapeHtml(item.financial_role)}</td>
        <td>${escapeHtml(item.date || "Not specified")}</td><td>${escapeHtml(item.conditionality)}</td>
        <td>${escapeHtml(item.payment_status)}</td>
      </tr>`).join("")}</tbody></table></div>`;
  }

  function renderDetail(packet) {
    document.title = `${packet.ticker} Research Idea V2 | Pure News Intelligence`;
    document.querySelector("#ri-v2-title").textContent = `${packet.issuer} (${packet.ticker})`;
    document.querySelector("#ri-v2-subtitle").textContent = `${packet.filing_date} · ${packet.section} · ${packet.novelty_review.final_novelty}`;
    const status = document.querySelector("#ri-v2-status");
    status.textContent = packet.packet_status;
    status.className = `status ${statusClass(packet.packet_status)}`;
    document.querySelector("#ri-v2-skeptic").textContent = packet.skeptic_review.status;
    document.querySelector("#ri-v2-coverage").textContent = packet.evidence_coverage.evidence_coverage_ratio.toFixed(2);
    document.querySelector("#ri-v2-trade").textContent = packet.illustrative_trade_hypothesis.status;

    const additional = packet.source_evidence.additional_prior_evidence;
    const checked = packet.retrieval_metadata.full_prior_filing_search_completed
      ? `<span class="status success ri-v2-checked">✓ Full prior-filing evidence checked</span>` : "";
    const claims = packet.atomic_claims.map((claim) => `<li>
      <div class="ri-v2-claim-head"><span class="ri-stage-label ri-stage-${claim.claim_type === "fact" ? "evidence" : "hypothesis"}">${escapeHtml(claim.claim_type)}</span><span class="status outline">${escapeHtml(claim.support_status)}</span></div>
      <p>${escapeHtml(claim.exact_wording)}</p>
      <dl class="ri-inline-meta"><div><dt>Novelty</dt><dd>${escapeHtml(claim.novelty_status)}</dd></div><div><dt>Confidence</dt><dd>${Number(claim.confidence).toFixed(2)}</dd></div></dl>
    </li>`).join("");
    const hypotheses = packet.research_hypotheses.length ? packet.research_hypotheses.map((hypothesis) => `<article class="ri-hypothesis-card">
      <span class="ri-stage-label ri-stage-hypothesis">RESEARCH HYPOTHESIS</span>
      <h3>${escapeHtml(hypothesis.hypothesis)}</h3>
      <p><strong>Mechanism:</strong> ${escapeHtml(hypothesis.mechanism)}</p>
      <p><strong>Testable prediction:</strong> ${escapeHtml(hypothesis.testable_prediction)}</p>
      <div class="ri-test-grid"><div><h4>Required data</h4>${list(hypothesis.required_data)}</div><div class="ri-confirm"><h4>Confirm</h4>${list(hypothesis.confirmation_conditions)}</div><div class="ri-falsify ri-test-wide"><h4>Falsify</h4>${list(hypothesis.falsification_conditions)}</div></div>
    </article>`).join("") : `<div class="ri-withheld"><h3>No grounded research hypothesis</h3><p>The packet failed safely before a hypothesis was retained.</p></div>`;
    const counter = packet.counterevidence_review.strongest_counterevidence;
    const saved = JSON.parse(localStorage.getItem(storageKey) || "{}")[packet.change_id] || "UNREVIEWED";
    const buttons = ["ACCEPTED", "EDITED", "REJECTED", "ESCALATED"].map((value) => `<button class="secondary" type="button" data-ri-v2-disposition="${value}" aria-pressed="${saved === value}">${value.replace("_", " ")}</button>`).join("");

    const detail = document.querySelector("#ri-v2-detail");
    detail.innerHTML = `
      <section class="ri-packet-section" aria-labelledby="ri-v2-source-title">
        <div class="ri-section-heading"><div><span class="ri-section-number">01</span><span class="ri-stage-label ri-stage-evidence">SOURCE EVIDENCE</span></div><h2 id="ri-v2-source-title">Display evidence plus retrieved context</h2><p>${checked}</p></div>
        <div class="ri-evidence-comparison">${evidenceCard("Prior display excerpt", packet.source_evidence.prior_excerpt)}${evidenceCard("Current display excerpt", packet.source_evidence.current_excerpt, true)}</div>
        <h3>Additional prior evidence found outside the display excerpt</h3>
        ${additional.length ? `<div class="ri-v2-context-list">${additional.map((item) => evidenceCard(`${item.filing_date || "Earlier"} · ${item.section}`, item.text)).join("")}</div>` : `<p class="ri-empty-inline">No additional matching span retained in this packet.</p>`}
        <p><strong>Earliest occurrence:</strong> ${escapeHtml(packet.source_evidence.earliest_occurrence?.acceptance_timestamp || "No reliable prior occurrence identified.")}</p>
      </section>
      <section class="ri-packet-section" aria-labelledby="ri-v2-novelty-title">
        <div class="ri-section-heading"><div><span class="ri-section-number">02</span><span class="ri-stage-label ri-stage-interpretation">NOVELTY REVIEW</span></div><h2 id="ri-v2-novelty-title">What changed—and what did not</h2></div>
        <div class="ri-classification-grid"><div><strong>Provisional novelty</strong><span>${escapeHtml(packet.novelty_review.provisional_novelty)}</span></div><div><strong>Final novelty</strong><span>${escapeHtml(packet.novelty_review.final_novelty)}</span></div><div><strong>What is new</strong><span>${escapeHtml(packet.novelty_review.what_is_new)}</span></div><div><strong>What is not new</strong><span>${escapeHtml(packet.novelty_review.what_is_not_new)}</span></div></div>
        <ol class="ri-v2-claim-list">${claims}</ol>
      </section>
      <section class="ri-packet-section" aria-labelledby="ri-v2-quantity-title">
        <div class="ri-section-heading"><div><span class="ri-section-number">03</span><span class="ri-stage-label ri-stage-evidence">FINANCIAL QUANTITIES</span></div><h2 id="ri-v2-quantity-title">Role, period, and payment basis</h2><p>Different amounts are not treated as substitutes merely because they are numerically related.</p></div>
        ${quantityTable(packet)}
        <p><strong>Incomparable pairs:</strong> ${packet.quantity_comparisons.filter((item) => item.status === "INCOMPARABLE_QUANTITIES").length}</p>
      </section>
      <section class="ri-packet-section" aria-labelledby="ri-v2-hypothesis-title">
        <div class="ri-section-heading"><div><span class="ri-section-number">04</span><span class="ri-stage-label ri-stage-hypothesis">RESEARCH HYPOTHESIS</span></div><h2 id="ri-v2-hypothesis-title">Bounded, testable research agenda</h2></div>
        <div class="ri-hypothesis-list">${hypotheses}</div>
      </section>
      <section class="ri-packet-section" aria-labelledby="ri-v2-counter-title">
        <div class="ri-section-heading"><div><span class="ri-section-number">05</span><span class="ri-stage-label ri-stage-review">COUNTEREVIDENCE</span></div><h2 id="ri-v2-counter-title">Strongest contrary evidence</h2></div>
        ${counter ? evidenceCard(`${counter.source_type} · ${counter.filing_date || "eligible prior evidence"}`, counter.text) : `<p class="ri-empty-inline">No reliable counterevidence match was found.</p>`}
        <p><strong>Alternate interpretation:</strong> ${escapeHtml(packet.skeptic_review.opposite_interpretation)}</p>
        <h3>Skeptic objections</h3>${list(packet.skeptic_review.objections)}
      </section>
      <section class="ri-packet-section" aria-labelledby="ri-v2-trade-title">
        <div class="ri-section-heading"><div><span class="ri-section-number">06</span><span class="ri-stage-label ri-stage-review">ILLUSTRATIVE TRADE HYPOTHESIS</span></div><h2 id="ri-v2-trade-title">Default: NOT_READY</h2></div>
        <div class="ri-trade-guard"><p><strong>Status:</strong> ${escapeHtml(packet.illustrative_trade_hypothesis.status)}</p><p><strong>View:</strong> ${escapeHtml(packet.illustrative_trade_hypothesis.candidate_view)}</p><p>No instrument is shown unless the evidence and mechanism support it.</p></div>
      </section>
      <section class="ri-packet-section" aria-labelledby="ri-v2-disposition-title">
        <div class="ri-section-heading"><div><span class="ri-section-number">07</span><span class="ri-stage-label ri-stage-review">ANALYST DISPOSITION</span></div><h2 id="ri-v2-disposition-title">Record a browser-local decision</h2></div>
        <div class="ri-disposition-actions" role="group" aria-label="Analyst disposition">${buttons}</div>
        <p class="ri-local-status" id="ri-v2-local-status">Current local disposition: ${escapeHtml(saved)}</p>
      </section>`;
    detail.setAttribute("aria-busy", "false");
    detail.querySelectorAll("[data-ri-v2-disposition]").forEach((button) => button.addEventListener("click", () => {
      const dispositions = JSON.parse(localStorage.getItem(storageKey) || "{}");
      dispositions[packet.change_id] = button.dataset.riV2Disposition;
      localStorage.setItem(storageKey, JSON.stringify(dispositions));
      detail.querySelectorAll("[data-ri-v2-disposition]").forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
      document.querySelector("#ri-v2-local-status").textContent = `Current local disposition: ${button.dataset.riV2Disposition}`;
      document.querySelector("#ri-v2-live").textContent = `Disposition saved as ${button.dataset.riV2Disposition}.`;
    }));
  }

  async function detailPage() {
    const index = await loadJson(`${root}/index.json`);
    const requested = new URLSearchParams(location.search).get("change_id");
    const changeId = index.packets.some((item) => item.change_id === requested) ? requested : index.packets[0].change_id;
    renderDetail(await loadJson(`${root}/${changeId}.json`));
  }

  async function galleryPage() {
    const index = await loadJson(`${root}/index.json`);
    const packets = await Promise.all(index.packets.map((item) => loadJson(`${root}/${item.change_id}.json`)));
    document.querySelector("#ri-v2-gallery-count").textContent = `${packets.filter((item) => item.packet_status === "PUBLISHABLE").length} publishable · ${packets.length} reviewed · 60-case sample blocked`;
    const gallery = document.querySelector("#ri-v2-gallery");
    gallery.innerHTML = packets.map((packet) => `<article class="ri-gallery-card">
      <div><span class="status ${statusClass(packet.packet_status)}">${escapeHtml(packet.packet_status)}</span> ${packet.retrieval_metadata.full_prior_filing_search_completed ? `<span class="status success">✓ Prior filing checked</span>` : ""}</div>
      <h3>${escapeHtml(packet.issuer)} (${escapeHtml(packet.ticker)})</h3>
      <p class="ri-gallery-category">${escapeHtml(packet.novelty_review.final_novelty)}</p>
      <dl class="ri-gallery-meta"><div><dt>Coverage</dt><dd>${packet.evidence_coverage.evidence_coverage_ratio.toFixed(2)}</dd></div><div><dt>Skeptic</dt><dd>${escapeHtml(packet.skeptic_review.status)}</dd></div><div><dt>Hypotheses</dt><dd>${packet.research_hypotheses.length}</dd></div><div><dt>Trade</dt><dd>${escapeHtml(packet.illustrative_trade_hypothesis.status)}</dd></div></dl>
      <div class="card-actions"><a href="research_idea_v2.html?change_id=${encodeURIComponent(packet.change_id)}">Open evidence review</a></div>
    </article>`).join("");
    gallery.setAttribute("aria-busy", "false");
  }

  const run = page === "detail" ? detailPage : page === "gallery" ? galleryPage : async () => {};
  run().catch((error) => {
    const target = document.querySelector("#ri-v2-detail, #ri-v2-gallery");
    if (target) {
      target.innerHTML = `<div class="error-state"><h2>Unable to load V2 evidence</h2><p>${escapeHtml(error.message)}</p></div>`;
      target.setAttribute("aria-busy", "false");
    }
  });
})();
