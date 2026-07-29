# Pure News Intelligence

Pure News Intelligence is an evidence-linked research workflow for finding what changed in corporate disclosures, tracing the supporting record, preserving institutional memory, and forming testable research questions.

The project began by testing whether “pure news” in 10-K filings predicted returns. The locked tests did **not** support that thesis. The product therefore pivoted toward a narrower and more defensible analyst problem: prioritizing disclosure changes and challenging plausible but unsupported narratives.

[Open the public demo](https://joshgutierrez56.github.io/pure-news-intelligence-demo/) · [Review the research evidence](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/research_results.html) · [Read the methodology](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/methodology.html)

## What the workflow does

1. Retrieves point-in-time public filings and permitted evidence.
2. Compares consecutive disclosures and links exact source spans.
3. Checks prior filings, earlier 8-Ks, and eligible news context.
4. Separates facts, interpretations, uncertainty, and hypotheses.
5. Normalizes financial quantities before comparing them.
6. Searches for counterevidence and permits safe rejection.
7. Leaves the final decision with the analyst.

The Experimental Research Idea Engine is a bounded secondary capability; it does not replace the core Disclosure Change Engine.

The public site is static. Its public-safe layer serves frozen packets and does not run live model inference, personalized recommendations, or trade execution.

## Validated public results

- 150 companies and consecutive 10-K pairs
- 995 evidence-backed disclosure changes
- 629 high-confidence changes
- 1,990 verified excerpt-offset checks
- Research Idea Engine V2: 8 cases reviewed, 2 publishable research hypotheses, 6 safe failures, and 0 actionable trade views
- RH and DVN: `PASS_HYPOTHESIS_ONLY`, evidence coverage 1.00
- EFX: `REJECT_MISLEADING_COMPARISON`
- Formal blinded human ratings: pending
- 60-case phase: blocked and not run

Evidence coverage 1.00 means every factual proposition in a published packet was supported by cited packet evidence. It does not validate the hypothesis, analyst usefulness, or investment performance.

## What the research did not prove

The project did not demonstrate alpha, Sharpe-ratio improvement, information-coefficient improvement, return prediction, causality, analyst adoption, commercial success, or institutional validation. It is not investment advice.

## Recommended demo path

1. [Overview](https://joshgutierrez56.github.io/pure-news-intelligence-demo/)
2. [Ranked Changes](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/ranked_change_feed.html)
3. [Case Studies](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/case_studies.html)
4. [Research Ideas](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/research_ideas.html)
5. [Research Results](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/research_results.html)
6. [Methodology](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/methodology.html)
7. [Pilot Plan](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/pilot_plan.html)

Supporting resources: [FAQ](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/faq.html), [Known Limitations](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/known_limitations.html), [Future Research](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/future_research.html), [Public Architecture](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/public_architecture.html), [Professor Presentation](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/professor_presentation.html), and [Innovation Framework](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/innovation_framework.html).

## Repository map

- `demo/` — static public interface and public-safe data
- `data/` — frozen research inputs, packets, and indexes
- `schemas/` — versioned packet and claim schemas
- `prompts/` — frozen generator and skeptic instructions
- `scripts/` — deterministic build, validation, and audit utilities
- `tests/` — Python integrity tests and Playwright browser tests
- `reports/` — methodology, audit, validation, and screenshot reports
- `artifacts/` — machine-readable receipts and frozen gate decisions
- `share/` — concise external-review package

## Local preview

Requirements: Python 3, Node.js, and npm.

```powershell
npm install
npx playwright install
node tests/server.cjs
```

Then open `http://127.0.0.1:4173/`.

## Tests

```powershell
python -m unittest discover -s tests -p "test_*.py"
npm test
```

The suites cover packet preservation, point-in-time discipline, claim boundaries, accessibility, links, relative paths, browser behavior, responsive layout, exports, and the EFX negative regression fixture.

## Public-safe data and provenance

`demo/data/research_ideas/v2/manifest.json` identifies the three public packets and compact safe-failure metadata. Public derivatives are built from frozen V2 artifacts; packet hashes are recorded in receipts. The manifest’s validated byte sequence is preserved with a path-specific `.gitattributes` rule.

Browser-only analyst dispositions and notes use browser-local storage. They never modify packet JSON or create an approval claim.

## Deployment

GitHub Pages serves the repository’s validated static content from `gh-pages`. There is no server-side model, database, or secret in the public deployment. Deployment receipts record the source commit, manifest hash, live checks, and rollback commit.

## Contributing, security, citation, and license status

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CITATION.cff](CITATION.cff), and [LICENSE_STATUS.md](LICENSE_STATUS.md). No open-source license has been selected; reuse rights are not granted by repository visibility alone.

## Next evidence gate

Formal blinded human review comes next. Broader scaling remains blocked. Only after that gate should the project consider an analyst workflow pilot, prospective hypothesis freezing, broader case evaluation, and—last—separate investment-performance analysis.

Core public route: `demo/research_ideas.html`.
