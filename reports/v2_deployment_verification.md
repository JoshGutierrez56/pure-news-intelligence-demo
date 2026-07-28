# V2 deployment verification

## Deployment

- Repository: `JoshGutierrez56/pure-news-intelligence-demo`
- Feature branch: `feat/professor-demo-polish-v2`
- GitHub Pages branch: `gh-pages` (repository default and deployment branch; no separate `main` branch exists)
- Starting commit: `1a8399dbded190197cd466a4d6643b4b361eabfc`
- Validated deployment commit: `69abfbaebb08d913f52e581c0eb26376ca9426d9`
- GitHub Pages workflow: completed successfully for the validated deployment commit

## Public verification

Twenty-seven public resources returned HTTP 200 after deployment:

- overview;
- professor presentation;
- ranked feed;
- case gallery and two-case walkthrough;
- comparisons and timelines;
- research results and methodology;
- innovation framework;
- pilot plan;
- professor materials;
- private experimental workspace;
- five downloadable HTML handouts;
- frozen 995-record JSON;
- eight evidence packets.

The full route receipt is stored in `artifacts/deployment_routes_v2.json`.

## Live browser verification

The deployed pages were opened in Microsoft Edge at 1440×900. Verification confirmed:

- one page-level heading on every checked route;
- 995 of 995 records loaded and 18 cards rendered on the first feed page;
- the 5-minute presentation reported 1 / 7 after entering presentation mode;
- zero console errors and zero page errors;
- new innovation, pilot, walkthrough, and materials routes loaded successfully.

## URLs

- Overview: <https://joshgutierrez56.github.io/pure-news-intelligence-demo/>
- Professor presentation: <https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/professor_presentation.html>
- Ranked changes: <https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/ranked_change_feed.html>
- Case studies: <https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/case_studies.html>
- Innovation framework: <https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/innovation_framework.html>
- Pilot plan: <https://joshgutierrez56.github.io/pure-news-intelligence-demo/demo/pilot_plan.html>

## Result

Deployment gate passed. The prior version remains recoverable at commit `1a8399d`.
