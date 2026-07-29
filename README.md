# Pure News Intelligence — professor demonstration

Pure News Intelligence is an evidence-linked disclosure-change workflow for institutional research analysts. It compares consecutive 10-K filings, ranks meaningful changes, checks strictly earlier 8-Ks and news headlines, and keeps the original filing evidence attached.

## Project journey

The project began as a broad news-to-stock prediction hypothesis. Locked tests did not support incremental alpha from added 10-K features, and enriched expected-language models did not outperform the prior-10-K persistence baseline. Six customer-discovery interviews pointed to a narrower problem: analyst attention, historical comparison, visible evidence, workflow fit, and institutional memory.

The current MVP separates the product from the quantitative research claim. It is an operational evidence workflow with a final research classification of `INSUFFICIENT_EVIDENCE`.

## Experimental Research Idea Engine

The bounded V2 extension asks, “What should an analyst investigate next?” Full-prior retrieval, atomic claim review, financial-role normalization, counterevidence search, and an independent skeptical pass are applied before a frozen packet can appear in the public demo.

The eight-case result is deliberately selective:

- 2 publishable research hypotheses: RH and DVN
- 6 safe failures: EFX, CHE, DLTR, FCX, KHC, and TFC
- 0 actionable trade views
- 1.00 factual evidence coverage for both published packets
- formal blinded human ratings pending
- 60-case expansion blocked

EFX is the permanent negative fixture. V2 found that the $125M conditional top-up was previously disclosed, classified $346.7M as a remaining balance and approximately $345M as a cash deposit, rejected the comparison as `INCOMPARABLE_QUANTITIES`, and removed unsupported liquidity, reserve, and bondholder claims.

Public routes:

- `demo/research_ideas.html`
- `demo/research_idea_rh.html`
- `demo/research_idea_dvn.html`
- `demo/research_idea_efx.html`
- `demo/research_idea_methodology.html`

The public-safe layer under `demo/data/research_ideas/v2/` contains only validated derivatives plus a hash manifest. Frozen source packets remain under `data/research_idea_packets/v2/`; their hashes are audited against `artifacts/research_idea_public_demo_start_receipt.json`. Analyst dispositions and notes use browser-local storage and never modify packet JSON.

The public demo uses frozen, validated research-idea packets. It does not run live model inference or generate personalized recommendations. GitHub Pages performs no inference because the site is static: there is no model endpoint, credential, or live generation control. Broader scaling remains blocked pending formal blinded human validation.

## Public pages

- [Overview](https://joshgutierrez56.github.io/pure-news-intelligence-demo/)
- [Professor presentation](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/professor_presentation.html)
- [Ranked disclosure changes](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/ranked_change_feed.html)
- [Case-study gallery](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/case_studies.html)
- [Experimental research ideas](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/research_ideas.html)
- [Two-case walkthrough](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/case_study_walkthrough.html)
- [Research results](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/research_results.html)
- [Methodology and trust](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/methodology.html)
- [Innovation framework](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/innovation_framework.html)
- [Proposed pilot plan](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/pilot_plan.html)
- [Professor materials](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/professor_materials.html)

## Frozen demonstration

- 150 issuer-disjoint companies and 150 consecutive 10-K pairs
- 995 evidence-backed disclosure changes
- 629 high-confidence changes at the fixed threshold
- 1,990 verified excerpt-offset checks
- 394 previously disclosed, 342 genuinely new relative to study sources, 243 partially anticipated, and 16 unclear
- eight outcome-independent case studies
- zero point-in-time violations

## Local preview and validation

```powershell
npm install
npm test
python -m pip install -r requirements-research-idea.txt
python -m pytest -q
python -m pytest -q tests/test_research_idea_public_demo.py
python scripts/validate_research_idea_packets.py --mode final
```

The Playwright configuration starts a local server at `http://127.0.0.1:4173`. Tests cover metrics, links, filters, sorting, pagination, onboarding, the local shortlist, presentation durations, notes and keyboard controls, evidence boundaries, responsive widths, accessibility labels, axe checks, deterministic rendering, and console errors.

The final Research Idea deterministic suite passes 67/67 tests. Its focused permanent browser suite passes 15/15 tests, and the complete browser-suite target is 32/32.

Screenshots are generated at 1920×1080, 1440×900, 1024×768, and 390×844.
The established demo set is under `artifacts/screenshots/v2/`; the 20-image
Research Idea review set is under `artifacts/screenshots/research_idea_v1/`.

Local generation is an explicit experimental workflow and is not needed by the public site:

```powershell
python scripts/build_research_idea_inputs.py
python scripts/generate_research_idea_packets.py
python scripts/review_research_idea_packets.py
python scripts/export_research_idea_packet.py --all
```

The scripts verify the pinned local model digest, use temperature zero and a fixed seed, reject future information, allow at most one schema-repair retry, and cache valid outputs. Do not run generation against the full 995-record corpus; V1 is bounded to the eight case studies.

## Deployment

GitHub Pages serves the `gh-pages` branch from the repository root.

1. Create and validate changes on a feature branch.
2. Run the complete test and accessibility suite.
3. Review screenshots and content reconciliation.
4. Merge the validated branch into `gh-pages`.
5. Verify the deployed commit and every public route.

## Research limitations

The product demonstration is operational; the bounded risk analysis was inconclusive. The site does not support an alpha, causal, trading, customer-adoption, willingness-to-pay, or institutional-validation claim.

“Genuinely new” means no earlier match was found within the frozen filings and headlines available in this study. It is not a claim about all possible public or private information. Provider article bodies are excluded. Same-day news is excluded. Later market outcomes are labeled separately and were never used for classification or case selection.

The proposed next step is a controlled 2–4 week workflow pilot with 3–6 analysts measuring review time, material-event recall, agreement, correction rate, novelty-label acceptance, repeat use, and institutional-memory usefulness. No pilot result is reported.
