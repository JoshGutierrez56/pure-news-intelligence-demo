# Full-Branch Public Deployment

## Deployment

- Source branch: `feat/research-idea-engine-public-demo-v1`
- Exact deployed source: `4f884e92a5229519c229ae89c4d25fe4256cc7ad`
- Prior `gh-pages`: `61c50b0b0f8d95ea9b39edd2a2b02d451ef9890f`
- New `gh-pages`: `4f884e92a5229519c229ae89c4d25fe4256cc7ad`
- Rollback commit: `61c50b0b0f8d95ea9b39edd2a2b02d451ef9890f`
- Deployment URL:
  <https://joshgutierrez56.github.io/pure-news-intelligence-demo/>
- Deployment method: recoverable fast-forward; no force push

The deployment includes the polished demo, Research Idea Engine, supporting
trust pages and materials, and Universe Coverage Preview.

## Pre-deployment gate

- Python: 125/125 passed
- Playwright: 75/75 passed
- Clean-clone focused suite: 19/19 passed
- Packet hashes: 3/3 passed
- Universe hashes: 4/4 passed
- Frozen research preservation: passed

## Post-deployment gate

- Live routes: 19/19 passed
- Internal links: 38 checked, 0 broken
- Console/request errors: 0
- Serious/critical axe violations: 0
- Raw JSON assets: 8/8 exact hash matches and valid JSON
- Responsive, keyboard, print, exports, analyst controls, presentation modes,
  and Universe filters: passed

Rollback was not required.
