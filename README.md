# Pure News Intelligence

**Evidence-linked disclosure research: what changed, what supports it, and what to investigate next.**

This prototype compares 10-K disclosures, traces source excerpts, and challenges unsupported narratives. Locked tests **did not support its original return-prediction thesis**; the project pivoted to inspectable disclosure research, not trading signals.

[**Explore the frozen demo**](https://joshgutierrez56.github.io/pure-news-intelligence-demo/) · [Research results](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/research_results.html) · [Methodology](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/methodology.html) · [Browse the build and audit code](scripts/)

**Public mode:** the static public-safe layer serves frozen research packets. It does not run live model inference or execute trades, and provides no personalized recommendations.

## A five-minute review

1. [Ranked Changes](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/ranked_change_feed.html): select a disclosure change and trace its source evidence.
2. [Case Studies](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/case_studies.html): compare the change with prior disclosures and context.
3. [Research Ideas](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/research_ideas.html): contrast the RH/DVN hypothesis-only packets with EFX's rejected comparison.
4. [Research Results](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/research_results.html): inspect the negative findings and the boundary between evidence coverage and investment validity.

## What the frozen evidence shows

| Result | Evidence and interpretation |
| :--- | :--- |
| **150 consecutive 10-K pairs in the study** | Reported study scope; [claim reconciliation](reports/final_polish_claim_reconciliation.md) |
| **995 evidence-backed changes; 629 high-confidence** | [Change records](demo/data/changes.json); confidence labels are not measured predictive accuracy |
| **1,990 excerpt-offset checks** | Checks that the cited spans match the disclosure record; [claim reconciliation](reports/final_polish_claim_reconciliation.md) |
| **8 idea cases: 2 publishable hypotheses, 6 safe failures** | [V2 manifest](demo/data/research_ideas/v2/manifest.json); **0 actionable trade views** |
| **RH / DVN: `PASS_HYPOTHESIS_ONLY`** | [RH packet](demo/data/research_ideas/v2/rh.json) and [DVN packet](demo/data/research_ideas/v2/dvn.json), each with evidence coverage **1.00** |
| **EFX: `REJECT_MISLEADING_COMPARISON`** | [Rejected packet](demo/data/research_ideas/v2/efx_rejection.json): distinct financial quantities must not be presented as like-for-like |

“Publishable” is the bounded packet gate, not external peer review. Evidence coverage 1.00 means the published packet's factual propositions have cited support; it does **not** validate the hypothesis, usefulness to analysts, or investment performance. Formal blinded human ratings remain pending; the 60-case phase is blocked and has not run.

## Engineering workflow

The core **Disclosure Change Engine** supports change detection and source tracing. The secondary **Experimental Research Idea Engine** turns selected changes into falsifiable questions and can hold or reject a packet.

```text
Frozen filings and permitted context
  → formation-time evidence bundle and exact source spans
  → structured hypothesis and separate skeptical review
  → quantity normalization, counterevidence, and integrity checks
  → frozen public-safe packet
  → analyst review in the static interface
```

| Component | Browse the implementation |
| :--- | :--- |
| Evidence inputs and prior context | [Input builder](scripts/build_research_idea_inputs.py), [prior-evidence index](scripts/build_full_prior_evidence_index.py) |
| Structured generation and review | [V2 generator](scripts/generate_research_idea_packets_v2.py), [review stage](scripts/review_research_idea_packets.py), [prompts](prompts/), [schemas](schemas/) |
| Financial and evidence checks | [Quantity normalization](scripts/normalize_financial_quantities.py), [counterevidence search](scripts/search_counterevidence.py), [V2 validation](scripts/validate_research_idea_packets_v2.py), [audit](scripts/audit_research_idea_v2.py) |
| Public delivery | [Public-safe builder](scripts/build_public_research_ideas.py), [static interface](demo/), [frozen receipts](artifacts/), [integrity and browser tests](tests/) |

Generation runs separately and locally. Analyst notes use browser-local storage; they never modify frozen packets or imply approval. [Architecture walkthrough](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/public_architecture.html)

**Stack:** Python validation/build utilities, JSON schemas, JavaScript/HTML/CSS, and Playwright accessibility/browser checks.

## Run the public demo locally

A static preview needs **Python 3 only**, with no API keys, model download, or data subscription:

```bash
git clone https://github.com/JoshGutierrez56/pure-news-intelligence-demo.git
cd pure-news-intelligence-demo
python -m http.server 4173 --bind 127.0.0.1
```

Open **http://127.0.0.1:4173/**. Keep the server running while reviewing; stop it with `Ctrl+C` before browser tests, which start their own server on that port.

### Check release claims and packet integrity

From a Python virtual environment:

```bash
python -m pip install -r requirements-research-idea.txt
python -m pytest -q tests/test_final_polish_release_candidate.py tests/test_final_packet_git_blobs.py
```

For browser checks, install Node.js/npm and the configured **Microsoft Edge** browser:

```bash
npm ci
npx playwright install msedge
npm test
```

Skip Edge installation if it is already installed; the [test configuration](playwright.config.cjs) selects `msedge`, not default Chromium. The focused Python checks verify public claims and canonical packet bytes. The [broader suites](tests/) also cover time boundaries, browser behavior, accessibility, exports, and EFX rejection; some historical checks pin an earlier deployment commit or exact checkout bytes. Test scope is not investment effectiveness.

## Universe coverage preview

The [coverage preview](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/universe_coverage_preview.html) indexes **6,190 normalized CIKs** from frozen 2012–2024 SEC 8-K metadata, with permitted 2015–2024 news metadata and curated 10-K context, as of **2024-12-31**. This is broad U.S. public-company **metadata coverage**, not Russell 3000 membership or completed full-universe analysis.

Missing news coverage is `null`/unavailable, not zero news. Gaps include 6,041 issuers without curated 10-K metadata, 5,414 without permitted news metadata, and 3,118 without 8-K metadata in the frozen 2024 window. [Scope](reports/universe_preview_scope.md) · [Coverage receipt](demo/data/universe_preview/universe_summary.json) · [Known gaps](reports/universe_preview_known_gaps.md)

## Boundaries and next evidence gate

The project has **not** demonstrated alpha, return prediction, causality, analyst time savings/adoption, commercial success, or institutional validation. The frozen interface is a research demonstration, not an operating investment service. [Full limitations](share/KNOWN_LIMITATIONS.md) · [Supported and unsupported claims](share/RESEARCH_CLAIMS.md)

The next gate is formal blinded human review. Broader scaling remains blocked; workflow pilots and prospective investment tests are separate, future evaluations.

GitHub Pages serves the **`gh-pages` default branch**. Packet hashes and byte-preservation rules protect frozen evidence. [Provenance and deployment reports](reports/research_idea_deployment_verification.md)

## Project notes

[One-page summary](share/ONE_PAGE_SUMMARY.md) · [Demo guide](share/DEMO_GUIDE.md) · [FAQ](share/FAQ.md) · [Future research](share/FUTURE_RESEARCH.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Citation](CITATION.cff)

No open-source license has been selected; public visibility alone does not grant reuse rights. See [license status](LICENSE_STATUS.md).
