(() => {
  "use strict";

  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector(".primary-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  document.querySelectorAll('a[target="_blank"]').forEach((link) => {
    link.rel = "noreferrer noopener";
  });

  const presentationButton = document.querySelector("[data-presentation-toggle]");
  const storySections = [...document.querySelectorAll(".story-section")];
  const progress = document.querySelector(".presentation-progress span");
  const position = document.querySelector("[data-presentation-position]");
  let current = 0;

  function updatePresentation() {
    storySections.forEach((section, index) => {
      section.classList.toggle("is-current", index === current);
      section.setAttribute("aria-hidden", String(index !== current));
    });
    if (progress) progress.style.width = `${((current + 1) / storySections.length) * 100}%`;
    if (position) position.textContent = `${current + 1} / ${storySections.length}`;
    storySections[current]?.focus({ preventScroll: true });
  }

  function setPresentation(active) {
    document.body.classList.toggle("presentation-active", active);
    presentationButton?.setAttribute("aria-pressed", String(active));
    presentationButton?.querySelector("span")?.replaceChildren(active ? "Exit presentation" : "Presentation mode");
    storySections.forEach((section) => section.removeAttribute("aria-hidden"));
    if (active) updatePresentation();
  }

  presentationButton?.addEventListener("click", () => {
    setPresentation(!document.body.classList.contains("presentation-active"));
  });

  document.querySelector("[data-presentation-next]")?.addEventListener("click", () => {
    current = Math.min(storySections.length - 1, current + 1);
    updatePresentation();
  });
  document.querySelector("[data-presentation-previous]")?.addEventListener("click", () => {
    current = Math.max(0, current - 1);
    updatePresentation();
  });

  document.addEventListener("keydown", (event) => {
    if (!document.body.classList.contains("presentation-active")) return;
    if (["ArrowRight", "ArrowDown", "PageDown", " "].includes(event.key)) {
      event.preventDefault();
      current = Math.min(storySections.length - 1, current + 1);
      updatePresentation();
    } else if (["ArrowLeft", "ArrowUp", "PageUp"].includes(event.key)) {
      event.preventDefault();
      current = Math.max(0, current - 1);
      updatePresentation();
    } else if (event.key === "Home") {
      event.preventDefault();
      current = 0;
      updatePresentation();
    } else if (event.key === "End") {
      event.preventDefault();
      current = storySections.length - 1;
      updatePresentation();
    } else if (event.key === "Escape") {
      setPresentation(false);
    }
  });
})();
