# Research Idea Accessibility Review

## Result

**PASS — the tested Research Idea interfaces meet the bounded automated and keyboard checks in this review.**

This is an interface result, not a research-quality result. The frozen eight-packet set remains **HOLD_GROUNDING**: four packets are held, four are rejected by the skeptic, and none is publishable.

## Scope and environment

Tested on 2026-07-28 from the local static server at `http://127.0.0.1:4173` using:

- Microsoft Edge `151.0.4129.50`, headless
- Playwright `1.62.0`
- `@axe-core/playwright` `4.10.2`
- WCAG tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, and `wcag22aa`

The primary matrix covered:

- `demo/research_idea.html?change_id=8f5336b55618ffe68e8a`
- `demo/research_idea_gallery.html`
- `demo/research_idea_methodology.html`
- `demo/ranked_change_feed.html`

Each primary surface was tested at `1920×1080`, `1440×900`, `1024×768`, and `390×844`. All eight frozen packet-detail routes were also rendered at all four sizes, and each packet received a separate axe pass at `1440×900`.

## Automated evidence

| Check | Actual result |
|---|---:|
| Primary page/viewport axe runs | 16 |
| Packet-specific axe runs | 8 |
| Total axe runs | 24 |
| Axe A/AA violations | 0 |
| Total rendered page runs used for final QA | 48 |
| HTTP failures | 0 |
| Console errors | 0 |
| Uncaught page errors | 0 |
| Failed requests | 0 |
| Pages left in `aria-busy="true"` | 0 |
| Visible controls without an accessible name | 0 |
| Interactive targets below `24×24` CSS pixels | 0 |

Every tested surface had one `h1`, one `main`, and named navigation landmarks. The final detail pages exposed all required review layers through visible text labels: `EVIDENCE`, `EX-POST OUTCOME`, `SYSTEM INTERPRETATION`, `EVIDENCE FACTS`, `AI-GENERATED HYPOTHESIS`, and `ANALYST REVIEW`.

At desktop width, the detail page exposed eight visible form controls, the gallery eleven, and the ranked feed thirty-nine. At collapsed-navigation widths, the menu toggle increased those counts by one. A corrected DOM label inspection and axe both found zero unnamed controls. The methodology page has no form controls beyond its responsive menu toggle.

## Keyboard and status-message checks

- The first `Tab` stop was **Skip to main content**, with a visible `3px` focus outline (`rgb(241, 184, 75)`). Pressing `Enter` changed the fragment to `#main`.
- At `1024×768`, keyboard activation opened the menu, changed `aria-expanded` to `true`, displayed the navigation, and placed the next `Tab` stop on **Overview**.
- Pressing `Enter` on **Accept** changed its `aria-pressed` state to `true`, changed the local status to `ACCEPTED`, wrote the browser-local overlay, and announced `ACCEPTED saved locally for KHC.` through the polite live region.
- Reloading preserved the accepted state. The test removed the local overlay afterward.
- Pressing `Space` on **Edit** changed the selected state to `ACCEPTED_WITH_EDITS`, announced the change, and moved focus to the labeled **Analyst notes** textarea.
- Keyboard entry of `KHC` in the gallery reduced the live result count to `1 of 8 validated packets`. Activating **Clear filters** restored `8 of 8 validated packets` and returned focus to the issuer filter.

The analyst actions have distinct accessible names: **Accept**, **Edit**, **Reject**, **Escalate**, **Save for discussion**, **Save local review**, and **Export evidence and hypothesis packet**. Selection is communicated with `aria-pressed`, not color alone.

## Target size and focus observations

All controls on the three Research Idea pages measured at least `44px` high in the tested states. The existing ranked-feed **Save for discussion** buttons measured approximately `162.4×38.5px`; this is below the product's preferred `44px` height but above the WCAG 2.2 AA minimum target size of `24×24px`. No target-size axe finding was produced.

The skip link correctly navigated to `#main`, although Edge reported `BODY` rather than `MAIN` as `document.activeElement` after activation. This is recorded as a non-blocking browser-focus nuance, not proof of programmatic focus transfer.

## Visual and semantic review

Viewport and component screenshots were captured to the operating-system temporary directory and inspected for:

- visible focus and control state;
- evidence, inference, hypothesis, skeptical-review, and analyst-review separation;
- non-color status text;
- readable held and rejected states;
- labeled filters, notes, source excerpts, and live result counts.

The frozen final state rendered four `HOLD_INSUFFICIENT_EVIDENCE` packets and four `REJECTED_BY_SKEPTIC` packets. All eight retained the required disclaimer and twelve ordered detail sections without rendering an error state.

## Limitations

- No hands-on NVDA, JAWS, VoiceOver, or TalkBack session was run. Axe and DOM semantics do not replace assistive-technology user testing.
- No Windows High Contrast, forced-colors, 200% browser zoom, OS text scaling, or print-PDF review was run.
- Touch checks used headless Edge emulation, not physical iOS or Android hardware.
- External SEC destinations were not included in this accessibility review.
- Zero automated findings do not establish full WCAG conformance.

## Commands and execution

The local server was started with `node tests/server.cjs`. Focused checks used the repository's installed Playwright and axe packages in transient Node scripts supplied over standard input; no test or production file was created by this review. Version checks used:

```text
node --version
npx playwright --version
npm ls @axe-core/playwright --depth=0
```

The final accessibility classification is **PASS**. The feature-level research classification remains **HOLD_GROUNDING**.
