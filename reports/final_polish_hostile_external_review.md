# Final Polish Hostile External Review

Review date: 2026-07-29  
Scope: public pages, public-safe data, repository documentation, and release-candidate claims.

## Skeptical professor

| Finding | Severity | Location | Corrective action | Disposition |
|---|---|---|---|---|
| The Research Results metadata described three studies although the public narrative now has four stages. | High | `demo/research_results.html` rendered view | Preserved the locked HTML bytes and corrected the browser title, description, and four-stage introduction through `demo/assets/site.js`. | Resolved |
| Technical validation could be mistaken for research validity. | High | Methodology and homepage | Added explicit language that test coverage does not validate hypotheses, analyst usefulness, or performance. | Resolved |
| The project pivot risked reading as post hoc success storytelling. | Medium | Homepage and share package | Preserved the null result, explained what changed afterward, and kept commercial and performance claims unsupported. | Disclosed |

## Institutional research director

| Finding | Severity | Location | Corrective action | Disposition |
|---|---|---|---|---|
| General visitors encountered professor and class materials before the core workflow. | High | Shared navigation and homepage | Standardized a seven-step visitor path and moved professor/innovation materials to supporting resources. | Resolved |
| Analyst ownership and public deployment boundaries were distributed across pages. | High | Methodology and detail pages | Added a public architecture page showing frozen data, no live inference, human review, no trade execution, and institutional memory. | Resolved |
| Edit burden remains unmeasured. | Medium | Pilot and limitations | Kept edit burden as a proposed pilot metric and stated that no workflow pilot has run. | Disclosed |

## Equity analyst

| Finding | Severity | Location | Corrective action | Disposition |
|---|---|---|---|---|
| The landing page sounded like a school-project index rather than a research product. | High | `index.html` | Rewrote the hero around the analyst problem, evidence workflow, and direct demo path. | Resolved |
| Readers needed a faster way to compare grounded hypothesis, uncertainty, and rejection. | High | Case Studies | Added the RH, DVN, and EFX three-outcome frame with direct links. | Resolved |
| Public packets are still dense. | Medium | RH and DVN detail pages | Retained the evidence-first hierarchy, collapsed trade-research section, print flow, and distinct fact/inference/uncertainty blocks. | Disclosed |

## Innovation-class grader

| Finding | Severity | Location | Corrective action | Disposition |
|---|---|---|---|---|
| The pivot narrative did not consistently distinguish customer learning from adoption validation. | High | Homepage and share package | Added explicit language that interviews informed design but did not validate adoption. | Resolved |
| The next experiment and stop conditions needed clearer sequencing. | High | Future Research and Pilot Plan | Added five ordered evidence gates, continuation rules, and stop rules. | Resolved |
| Buyer assumptions remain unvalidated. | Medium | Homepage and Innovation Framework | Preserved buyer framing as a proposed value proposition and disclosed absence of commercial validation. | Disclosed |

## GitHub and hiring reviewer

| Finding | Severity | Location | Corrective action | Disposition |
|---|---|---|---|---|
| README led with a professor demonstration and installation rather than product and evidence. | High | `README.md` | Rebuilt the README around problem, workflow, evidence, boundaries, demo path, architecture, and reproducibility. | Resolved |
| Repository governance and external-review documents were missing. | High | Repository root | Added changelog, contributing, security, citation, license-status, and complete `share/` package. | Resolved |
| No concise public architecture existed. | High | Public demo | Added a maintainable inline-SVG architecture page with no remote dependencies. | Resolved |
| The repository contains historical artifacts by design and may feel dense. | Medium | Repository tree | Added a directory map and frozen-artifact explanation; retained artifacts required for provenance. | Disclosed |

## Final review disposition

Unresolved critical findings: 0  
Unresolved high findings: 0  
Unresolved medium findings: 5, all explicitly disclosed as validation limits rather than hidden defects.
