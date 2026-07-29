# Final Polish Claim Reconciliation

| Public claim | Frozen source | Exact metric/status | Public routes | Approved wording |
|---|---|---|---|---|
| 8 cases reviewed | `demo/data/research_ideas/v2/manifest.json` | `cases_reviewed: 8` | Overview, Research Ideas, Results, FAQ | “8 cases reviewed” |
| 2 publishable hypotheses | Public manifest | `publishable_hypotheses: 2` | Overview, Research Ideas, Results | “2 publishable research hypotheses” |
| 6 safe failures | Public manifest | `safe_failures: 6` | Overview, Research Ideas, Results | “6 safe failures” |
| 0 actionable trade views | Public manifest | `actionable_trade_views: 0` | All idea pages and public summaries | “0 actionable trade views” |
| RH evidence coverage | `demo/data/research_ideas/v2/rh.json` | `1.0` | RH, Research Ideas, FAQ | “RH evidence coverage: 1.00” |
| DVN evidence coverage | `demo/data/research_ideas/v2/dvn.json` | `1.0` | DVN, Research Ideas, FAQ | “DVN evidence coverage: 1.00” |
| EFX rejection | `demo/data/research_ideas/v2/efx_rejection.json` | `REJECT_MISLEADING_COMPARISON` | EFX, Research Ideas, Case Studies | “EFX: REJECT_MISLEADING_COMPARISON” |
| EFX quantity roles | EFX public packet | $125M conditional top-up; $346.7M remaining balance; ~$345M cash deposit | EFX, FAQ | Exact role language only |
| Human ratings pending | Public manifest | human-review status ends in pending | Idea pages, Overview, FAQ, Limitations | “Formal blinded human ratings remain pending” |
| 60-case blocked | Public manifest and V2 receipts | `broader_generation: BLOCKED` | Methodology, FAQ, Limitations, Future Research | “60-case phase remains blocked and not run” |
| Null trading findings | Locked research results and research receipts | final classification `INSUFFICIENT_EVIDENCE` | Overview, Research Results, FAQ | “The original return-prediction thesis was not supported” |
| Disclosure demonstration | Locked `demo/data/catalog.json`, `demo/data/changes.json`, and research results | 150 pairs, 995 changes, 629 high-confidence, 1,990 offsets | Overview, Research Results | Exact bounded counts |
| Manifest integrity | `artifacts/research_idea_public_redeployment_receipt.json` | SHA-256 `1611006a…77f2d7` | Repository documentation | Exact full hash when reported |

## Unsupported claims intentionally excluded

No page claims Sharpe-ratio improvement, information-coefficient improvement, validated return prediction, causality, personalized advice, analyst adoption, customer adoption, institutional validation, or commercial success.

## Result

PASS — every material public number and conclusion maps to a frozen source artifact.
