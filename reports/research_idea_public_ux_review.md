# Research Idea Public Demo UX Review — Gates P0–P2

Status: **PASS FOR LOCAL PREVIEW**

## Design changes

The public preview replaces the engineering-oriented eight-packet queue with a selective professor-facing narrative:

1. bounded results and visible disclaimer;
2. two publishable hypothesis cards;
3. a prominent EFX grounding correction;
4. compact, transparent safe failures;
5. an explicit scale block.

Detail pages establish a stable evidence-first hierarchy: source evidence, verified novelty, fact/inference/uncertainty, possible mechanism, falsifiable hypothesis, analyst questions, withheld entity/scenario sections, collapsed no-trade status, skeptical review, quantities, and local analyst disposition.

## Trust and provenance

- Evidence uses institutional navy.
- Verified novelty uses restrained teal.
- Hypotheses use muted blue-violet.
- Skeptical review uses amber.
- Rejected claims use muted red plus text labels.
- Analyst controls use neutral/teal states.
- The `Full prior-filing evidence checked` label is sourced from the public-safe frozen contract.
- Missing scores, horizons, units, scenarios, and instruments are explicitly marked rather than invented.

## Accessibility and responsive review

- New Playwright integration tests: 10 passed.
- Full Playwright suite: 49 passed.
- Serious or critical axe violations: 0.
- Broken internal links: 0.
- Console, page, request, and response errors: 0.
- Horizontal overflow: 0 at 1440×900, 1024×768, and 390×844.
- Keyboard-accessible evidence regions, disclosure controls, analyst controls, exports, and notes are present.
- Status is communicated with text and color.

## Print and export

- JSON export works from immutable public-safe data.
- Markdown export works.
- Browser print / save as PDF invokes the print flow.
- Print CSS removes navigation and local controls, expands evidence excerpts, and removes card shadows.

## Performance footprint

The static preview adds:

- shared JavaScript: 26,203 bytes
- public manifest: 5,747 bytes
- RH JSON: 13,622 bytes
- DVN JSON: 14,394 bytes
- EFX JSON: 5,757 bytes

Pages load from static relative assets with no model call, private service, or runtime API.

## Visual QA

Baseline and after screenshots were inspected at desktop, tablet, and mobile widths. The new gallery improves selectivity and disclaimer prominence. The detail page remains long by design because the requested evidence and review hierarchy is exhaustive; sectioning, collapsed trade research, responsive one-column layout, and print controls keep it navigable.

P3 navigation and cross-page demo integration remain intentionally unstarted.
