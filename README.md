# Pure News Intelligence — professor demonstration

Pure News Intelligence is an evidence-linked disclosure-change workflow for institutional research analysts. The public GitHub Pages demonstration compares consecutive 10-K filings, ranks meaningful changes, checks whether those changes appeared in strictly earlier 8-Ks or news headlines, and exposes the supporting filing evidence.

## Project journey

The project began as a broad news-to-stock prediction hypothesis. Locked empirical tests did not support incremental alpha from adding 10-K features, and enriched expected-language models did not outperform the prior-10-K persistence baseline. Six customer-discovery interviews pointed to a narrower, more defensible problem: analyst attention, historical comparison, visible provenance, and institutional memory.

The current MVP therefore separates the product from the quantitative research claim. It is an operational evidence workflow with a final research classification of `INSUFFICIENT_EVIDENCE`.

## Public pages

- [Overview](https://joshgutierrez56.github.io/pure-news-intelligence-demo/)
- [Professor presentation](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/professor_presentation.html)
- [Ranked disclosure changes](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/ranked_change_feed.html)
- [Case-study gallery](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/case_studies.html)
- [Research results](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/research_results.html)
- [Methodology and trust](https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/methodology.html)

## Frozen demonstration

- 150 issuer-disjoint companies
- 150 consecutive 10-K pairs
- 995 evidence-backed disclosure changes
- 629 high-confidence changes at the fixed threshold
- 1,990 verified excerpt-offset checks
- 394 previously disclosed changes
- 342 genuinely new changes within the bounded corpus
- 243 partially anticipated changes
- 16 unclear changes
- eight outcome-independent case studies
- zero point-in-time violations

## Local preview

The site has no backend or build step. Serve the repository root over HTTP so browser `fetch()` calls can load the frozen JSON:

```powershell
python -m http.server 4173
```

Then open <http://127.0.0.1:4173/>.

## Validation

Install the bounded browser-test dependency, then run:

```powershell
npm install
npm test
```

The test suite reconciles research counts, internal navigation, source links, feed filters and sorting, pagination, keyboard presentation controls, accessibility labels, responsive widths, deterministic rendering, and console errors. Screenshot capture covers 1920×1080, 1440×900, 1024×768, and 390×844.

## Deployment

GitHub Pages serves the `gh-pages` branch from the repository root.

1. Create and validate changes on a feature branch.
2. Run `npm test`.
3. Review the generated screenshots in `artifacts/screenshots/`.
4. Merge the validated feature branch into `gh-pages`.
5. Verify the public URLs above and confirm the deployed commit.

## Research limitations

The product demonstration is operational; the bounded risk analysis was inconclusive. The site does not support an alpha, causal, trading, customer-adoption, willingness-to-pay, or institutional-validation claim.

“Genuinely new” means no earlier match was found within the frozen, searched 8-K and pre-filing-headline corpus. It is not a claim about all possible public or private information. Provider article bodies are excluded. Same-day news is excluded. Later market outcomes are labeled ex post and were never used for classification or case selection.

The proposed next step is a controlled 2–4 week workflow pilot with 3–6 analysts measuring review time, material-event recall, agreement, correction rate, novelty-label acceptance, repeat use, and institutional-memory usefulness.
