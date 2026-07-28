(() => {
  "use strict";

  const byId = (id) => document.getElementById(id);
  const navToggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector(".primary-nav");

  if (navToggle && nav) {
    navToggle.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(open));
    });
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
