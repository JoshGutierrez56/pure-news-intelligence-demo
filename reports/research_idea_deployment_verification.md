# Research Idea Deployment Verification

## Result

- **Release classification:** `HOLD_GROUNDING`
- **Gate I8 — deploy and verify:** `NOT RUN`
- **Public-site preservation:** `PASS`
- **Checked:** 2026-07-29T02:21:47Z
- **Canonical public URL:** <https://joshgutierrez56.github.io/pure-news-intelligence-demo/>

No research-idea deployment was attempted. The feature remains isolated from the public GitHub Pages site because the bounded eight-case review produced no publishable packet.

## Deployment identity

Read-only GitHub API checks returned:

| Check | Result |
| --- | --- |
| `gh-pages` head | `74ec311a7eaf3e848ef242da4f5a8a4ff7b1613a` |
| Latest `github-pages` deployment ID | `5648331752` |
| Latest deployment commit | `74ec311a7eaf3e848ef242da4f5a8a4ff7b1613a` |
| Deployment created | 2026-07-28T22:09:19Z |
| Deployment status | `success` |
| Status recorded | 2026-07-28T22:09:38Z |

The live root response was also byte-identical to `index.html` fetched from the starting commit:

- live bytes: `8,619`
- starting-commit bytes: `8,619`
- live SHA-256: `32c40b16532dbee69326eea42dea1ff526a6e4037ebf397dd671b3478cbcb288`
- starting-commit SHA-256: `32c40b16532dbee69326eea42dea1ff526a6e4037ebf397dd671b3478cbcb288`

## Established route checks

All principal existing routes returned HTTP 200:

| Route | HTTP | Bytes |
| --- | ---: | ---: |
| `/` | 200 | 8,619 |
| `/demo/ranked_change_feed.html` | 200 | 12,100 |
| `/demo/case_studies.html` | 200 | 8,569 |
| `/demo/company_comparison.html` | 200 | 31,651 |
| `/demo/company_timeline.html` | 200 | 7,828 |
| `/demo/research_results.html` | 200 | 8,865 |
| `/demo/methodology.html` | 200 | 9,509 |
| `/demo/professor_presentation.html` | 200 | 26,161 |

## Research-idea route checks

The three new feature routes are not present on the public deployment:

| Route | HTTP | Expected while held |
| --- | ---: | --- |
| `/demo/research_idea.html` | 404 | Yes |
| `/demo/research_idea_gallery.html` | 404 | Yes |
| `/demo/research_idea_methodology.html` | 404 | Yes |

## Release decision

The public demo remains on the frozen starting commit. Deployment stays
`NOT RUN` while the project is classified `HOLD_GROUNDING`; no merge into or
push to `gh-pages`, deployment, or GitHub settings change was performed as
part of this verification. A feature-branch push does not alter the public
Pages deployment.
