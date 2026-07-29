(() => {
  "use strict";

  const byId = (id) => document.getElementById(id);
  const navToggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector(".primary-nav");

  // Keep one concise, audience-neutral visitor path across public pages.
  if (nav) {
    const inDemo = location.pathname.includes("/demo/");
    const prefix = inDemo ? "" : "demo/";
    const overview = inDemo ? "../index.html" : "index.html";
    const currentFile = location.pathname.split("/").pop() || "index.html";
    const items = [
      [overview, "Overview", currentFile === "index.html"],
      [`${prefix}ranked_change_feed.html`, "Ranked Changes", currentFile === "ranked_change_feed.html"],
      [`${prefix}case_studies.html`, "Case Studies", currentFile === "case_studies.html"],
      [`${prefix}research_ideas.html`, "Research Ideas", currentFile.startsWith("research_idea")],
      [`${prefix}research_results.html`, "Research Results", currentFile === "research_results.html"],
      [`${prefix}methodology.html`, "Methodology", currentFile === "methodology.html" || currentFile === "research_idea_methodology.html"],
      [`${prefix}pilot_plan.html`, "Pilot Plan", currentFile === "pilot_plan.html"]
    ];
    nav.replaceChildren(...items.map(([href, label, active]) => {
      const link = document.createElement("a");
      link.href = href;
      link.textContent = label;
      if (active) link.setAttribute("aria-current", "page");
      return link;
    }));
  }

  if (navToggle && nav) {
    navToggle.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(open));
    });
  }

  // Keep the locked research-results HTML byte-identical while layering the
  // bounded V2 public-demo section at render time.
  if (location.pathname.endsWith("/research_results.html")) {
    document.title = "Research Program Results | Pure News Intelligence";
    document.querySelector('meta[name="description"]')?.setAttribute("content", "Four-stage research program: null return-prediction findings, a disclosure-change workflow, and bounded grounded research hypotheses.");
    const heroLede = document.querySelector(".hero .lede");
    if (heroLede) heroLede.textContent = "Four locked stages separate what the evidence supports, does not support, leaves inconclusive, and has not tested.";
    const finalCta = document.querySelector("main > .section-block:last-of-type");
    if (finalCta && !byId("idea-v2-results")) {
      const ideaResults = document.createElement("section");
      ideaResults.className = "section-block study-panel";
      ideaResults.setAttribute("aria-labelledby", "idea-v2-results");
      ideaResults.innerHTML = `<p class="eyebrow">Bounded experimental result</p>
        <h2 id="idea-v2-results">Research Idea Engine V2</h2>
        <h3>Can the system generate grounded, falsifiable research hypotheses while rejecting unsupported narratives?</h3>
        <dl class="study-plain">
          <div><dt>Question</dt><dd>Can full-prior evidence, atomic claims, numeric-role checks, and skeptical review produce bounded research agendas without forcing a story?</dd></div>
          <div><dt>Result</dt><dd>8 cases evaluated; 2 publishable hypotheses; 6 safe failures; 0 actionable trade views; 1.00 evidence coverage for the published packets.</dd></div>
          <div><dt>Decision</dt><dd><span class="status teal">READY_FOR_PUBLIC_DEMO</span> Demonstrate the frozen bounded outputs.</dd></div>
          <div><dt>Supported</dt><dd>Two grounded, falsifiable hypothesis packets and transparent safe failure.</dd></div>
          <div><dt>Not supported</dt><dd>Broad generation, analyst validation, or investment-performance claims.</dd></div>
          <div><dt>Inconclusive</dt><dd>Analyst usefulness and edit burden until blinded ratings are complete.</dd></div>
          <div><dt>Not tested</dt><dd>Information coefficient, Sharpe ratio, hit rate, signal decay, or realized performance.</dd></div>
        </dl>
        <p class="boundary-note"><strong>Boundary:</strong> the 60-case phase remains blocked. Zero trade views reflects conservative gating, not a missing display field.</p>
        <p><a href="research_ideas.html">Review the bounded gallery</a></p>`;
      finalCta.before(ideaResults);
    }
  }

  document.querySelectorAll('a[target="_blank"]').forEach((link) => {
    link.rel = "noreferrer noopener";
  });

  const footer = document.querySelector("footer");
  if (footer && !footer.querySelector('a[href*="innovation_framework"]')) {
    const depth = location.pathname.includes("/evidence_packets/") || location.pathname.includes("/materials/") ? "../" : "";
    const resources = document.createElement("nav");
    resources.setAttribute("aria-label", "Project resources");
    resources.innerHTML = `<a href="${depth}innovation_framework.html">Innovation Framework</a><a href="${depth}pilot_plan.html">Pilot Plan</a><a href="${depth}professor_materials.html">Professor Materials</a>`;
    footer.prepend(resources);
  }

  // Evidence packets share a deterministic five-part analyst review frame.
  const packetMeta = document.querySelector(".evidence-meta");
  const packetComparison = document.querySelector(".comparison");
  if (packetMeta && packetComparison && location.pathname.includes("/evidence_packets/")) {
    const metaBlocks = [...packetMeta.children];
    const currentDate = metaBlocks[0]?.querySelector("span")?.textContent?.trim() || "Current filing";
    const priorDate = metaBlocks[1]?.querySelector("span")?.textContent?.trim() || "Prior filing";
    const classification = metaBlocks[2]?.querySelector("span")?.textContent?.trim() || "Disclosure change";
    const novelty = metaBlocks[3]?.querySelector("span")?.textContent?.trim() || "Analyst review required";
    const careHeading = [...document.querySelectorAll("h2")].find((heading) => heading.textContent.includes("Why an analyst may care"));
    const why = careHeading?.nextElementSibling?.textContent?.trim() || "Review the change against company context and the original filing.";
    const review = document.createElement("section");
    review.className = "packet-review";
    review.setAttribute("aria-label", "Five-part analyst review");
    review.innerHTML = `<div class="case-boundary"><strong>Available at filing time</strong><span>Prior filing, current filing, and strictly earlier bounded study sources</span></div>
      <ol class="five-part">
        <li><strong>1. Analyst question</strong><span>What changed in ${classification}, and does it merit review?</span></li>
        <li><strong>2. What changed</strong><span>Compare the exact prior and current excerpts below.</span></li>
        <li><strong>3. Was it disclosed earlier?</strong><span>${novelty}. Verify the linked earlier evidence.</span></li>
        <li><strong>4. Why it may matter</strong><span>${why}</span></li>
        <li><strong>5. What this does not prove</strong><span>No causal, trading, alpha, or future-performance conclusion.</span></li>
      </ol>
      <div class="timeline packet-timeline" aria-label="Filing evidence timeline">
        <div class="event"><time>${priorDate}</time><p>Prior 10-K establishes the baseline language.</p></div>
        <div class="event"><time>Strictly earlier evidence</time><p>The bounded 8-K and headline check determines the novelty label.</p></div>
        <div class="event"><time>${currentDate}</time><p>Current 10-K contains the classified change.</p></div>
      </div>`;
    packetMeta.after(review);
    const exPost = document.querySelector(".ex-post");
    if (exPost) {
      const detail = exPost.textContent.replace(/^.*classification:\s*/i, "").trim();
      exPost.innerHTML = `<strong>Observed after the filing — not used in the original classification</strong><p>${detail}</p>`;
    }
  }

  const presentationToggle = document.querySelector("[data-presentation-toggle]");
  const allSlides = [...document.querySelectorAll(".story-section")];
  const progress = document.querySelector(".presentation-progress span");
  const progressBar = document.querySelector(".presentation-progress");
  const position = document.querySelector("[data-presentation-position]");
  const nextLabel = document.querySelector("[data-next-idea]");
  const notesToggle = document.querySelector("[data-notes-toggle]");
  const modeButtons = [...document.querySelectorAll("[data-duration-mode]")];
  const exitStatus = byId("presentation-exit-status");
  let current = 0;
  let durationMode = "10";
  let presentationActive = false;
  let notesVisible = false;

  function visibleSlides() {
    return allSlides.filter((slide) => durationMode === "10" || slide.dataset.optional !== "true");
  }

  function currentSlides() {
    const slides = visibleSlides();
    current = Math.min(Math.max(0, current), Math.max(0, slides.length - 1));
    return slides;
  }

  function updatePresentation({ focus = true } = {}) {
    const slides = currentSlides();
    allSlides.forEach((slide) => {
      const slideIndex = slides.indexOf(slide);
      const active = slideIndex === current;
      slide.classList.toggle("is-current", active);
      slide.classList.toggle("is-skipped", slideIndex === -1);
      slide.setAttribute("aria-hidden", String(!active && presentationActive));
    });
    if (progress) progress.style.width = `${slides.length ? ((current + 1) / slides.length) * 100 : 0}%`;
    if (progressBar) {
      progressBar.setAttribute("aria-valuemax", String(slides.length));
      progressBar.setAttribute("aria-valuenow", String(current + 1));
    }
    if (position) position.textContent = `${current + 1} / ${slides.length}`;
    if (nextLabel) nextLabel.textContent = slides[current]?.dataset.next || "Continue";
    if (focus) slides[current]?.focus({ preventScroll: true });
  }

  function setNotes(visible) {
    notesVisible = visible;
    document.body.classList.toggle("notes-visible", notesVisible);
    notesToggle?.setAttribute("aria-pressed", String(notesVisible));
    if (notesToggle) notesToggle.textContent = notesVisible ? "Hide notes (N)" : "Notes (N)";
  }

  async function requestFullscreen() {
    if (!document.fullscreenElement) {
      try { await document.documentElement.requestFullscreen(); } catch (_) { /* Browser may deny. */ }
    }
  }

  async function exitFullscreen() {
    if (document.fullscreenElement) {
      try { await document.exitFullscreen(); } catch (_) { /* Browser may deny. */ }
    }
  }

  function setPresentation(active, { requestFullScreen = false } = {}) {
    presentationActive = active;
    document.body.classList.toggle("presentation-active", active);
    presentationToggle?.setAttribute("aria-pressed", String(active));
    presentationToggle?.querySelector("span")?.replaceChildren(active ? "Exit presentation (F)" : "Present full screen (F)");
    allSlides.forEach((slide) => slide.removeAttribute("aria-hidden"));
    if (active) {
      updatePresentation();
      if (requestFullScreen) requestFullscreen();
    } else {
      setNotes(false);
      exitFullscreen();
      allSlides.forEach((slide) => slide.classList.remove("is-current", "is-skipped"));
      exitStatus?.replaceChildren("Presentation exited. Standard page view restored.");
      presentationToggle?.focus();
    }
  }

  function goToOffset(offset) {
    const slides = currentSlides();
    current = Math.min(slides.length - 1, Math.max(0, current + offset));
    updatePresentation();
  }

  function goToSlideId(id) {
    const slides = currentSlides();
    const index = slides.findIndex((slide) => slide.id === id);
    if (index >= 0) {
      current = index;
      if (!presentationActive) setPresentation(true);
      else updatePresentation();
    }
  }

  function setDurationMode(mode) {
    durationMode = mode;
    document.body.dataset.durationMode = mode;
    modeButtons.forEach((button) => {
      const active = button.dataset.durationMode === mode;
      button.setAttribute("aria-pressed", String(active));
      button.classList.toggle("is-active", active);
    });
    current = 0;
    if (presentationActive) updatePresentation();
  }

  presentationToggle?.addEventListener("click", () => {
    setPresentation(!presentationActive, { requestFullScreen: !presentationActive });
  });
  notesToggle?.addEventListener("click", () => setNotes(!notesVisible));
  modeButtons.forEach((button) => button.addEventListener("click", () => setDurationMode(button.dataset.durationMode)));
  document.querySelector("[data-presentation-next]")?.addEventListener("click", () => goToOffset(1));
  document.querySelector("[data-presentation-previous]")?.addEventListener("click", () => goToOffset(-1));
  document.querySelector("[data-jump-demo]")?.addEventListener("click", () => goToSlideId("slide-workflow"));
  document.querySelector("[data-print-presentation]")?.addEventListener("click", () => window.print());

  document.addEventListener("keydown", (event) => {
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement || event.target instanceof HTMLTextAreaElement) return;
    if (event.key.toLowerCase() === "f") {
      event.preventDefault();
      setPresentation(!presentationActive, { requestFullScreen: !presentationActive });
      return;
    }
    if (!presentationActive) return;
    if (["ArrowRight", "ArrowDown", "PageDown", " "].includes(event.key)) {
      event.preventDefault();
      goToOffset(1);
    } else if (["ArrowLeft", "ArrowUp", "PageUp"].includes(event.key)) {
      event.preventDefault();
      goToOffset(-1);
    } else if (event.key === "Home") {
      event.preventDefault();
      current = 0;
      updatePresentation();
    } else if (event.key === "End") {
      event.preventDefault();
      current = currentSlides().length - 1;
      updatePresentation();
    } else if (event.key === "Escape") {
      event.preventDefault();
      setPresentation(false);
    } else if (event.key.toLowerCase() === "n") {
      event.preventDefault();
      setNotes(!notesVisible);
    }
  });

  document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement && presentationActive) {
      presentationActive = false;
      document.body.classList.remove("presentation-active");
      setNotes(false);
      allSlides.forEach((slide) => slide.classList.remove("is-current", "is-skipped"));
      presentationToggle?.setAttribute("aria-pressed", "false");
      presentationToggle?.querySelector("span")?.replaceChildren("Present full screen (F)");
    }
  });

  setDurationMode("10");
})();
