# Research Idea Engine Public Deployment Report

Final classification: **DEPLOYMENT_FAILED — rollback completed**

## Deployment

- Source branch: `feat/research-idea-engine-public-demo-v1`
- Source commit: `934d0d8b8f5450cb89b70514136e98b69c03d697`
- Prior `gh-pages`: `74ec311a7eaf3e848ef242da4f5a8a4ff7b1613a`
- Attempted `gh-pages`: `934d0d8b8f5450cb89b70514136e98b69c03d697`
- Rollback `gh-pages`: `74ec311a7eaf3e848ef242da4f5a8a4ff7b1613a`

The deployment used a normal fast-forward. The mandated rollback used `--force-with-lease` against the exact attempted deployment commit; the attempted commit remains recoverable on the source branch.

## Verification result

The live browser audit passed 14/14 required routes, 61 internal links, RH/DVN/EFX rendering, research-status filtering, presentation modes, browser-local analyst controls, JSON and Markdown export, print flow, mobile overflow checks, console/network monitoring, and axe accessibility.

The deployment failed the required public-manifest byte-hash gate:

- Required SHA-256: `1611006a6a85fa9702846b22af4a957d2a2d2d0597123f7615d65bf71077f2d7`
- Live SHA-256: `b0244bb062351e187411c4f0a8443bd8febb7e2e0c8e4d487393da1f6d6a6928`

The live bytes exactly matched the Git blob. The discrepancy is line-ending normalization: the validated Windows working-tree file used CRLF bytes while Git stored and GitHub Pages served LF bytes (`core.autocrlf=true`; no path-specific `eol` attribute). JSON content and research metrics reconciled, but the explicit byte-hash requirement did not.

Per authorization instructions, the deployment was stopped and `gh-pages` was restored to `74ec311a`.
