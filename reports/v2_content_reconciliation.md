# V2 content reconciliation

## Frozen source verification

- `demo/data/changes.json`: unchanged; SHA-256 `17D3EC79EA48D8AFFA42F6F8A6B775B52A285736BF65853AE849BDB760211271`.
- Eight evidence-packet HTML files: unchanged in Git diff.
- All SEC source URLs in the 995-record file match `https://www.sec.gov/`.
- Every record retains a non-empty ID, filing date, ticker, issuer, title, summary, “why” field, category, materiality, confidence, and SEC URL.

## Reconciled metrics

| Metric | Frozen value | Validation |
|---|---:|---|
| Issuer-disjoint companies | 150 | Existing frozen report and public copy |
| Consecutive 10-K pairs | 150 | Existing frozen report and public copy |
| Evidence-backed changes | 995 | JSON record count |
| High-confidence changes | 629 | Recomputed at confidence ≥ 0.80 |
| Verified excerpt-offset checks | 1,990 | Locked report and public copy |
| Previously disclosed | 394 | Recomputed from frozen titles |
| Genuinely new relative to study sources | 342 | Recomputed from frozen titles |
| Partially anticipated | 243 | Recomputed from frozen titles |
| Unclear | 16 | Recomputed from frozen titles |
| Completed case studies | 8 | Packet inventory |
| Timing violations | 0 | Locked report and public copy |

Novelty reconciliation: `394 + 342 + 243 + 16 = 995`.

## Claim audit

- Final classification remains `INSUFFICIENT_EVIDENCE`.
- The operational product demonstration is explicitly separated from the inconclusive risk test.
- The site does not claim alpha, causality, trading value, customer adoption, willingness to pay, institutional validation, or commercial readiness.
- Later outcomes remain below a divider labeled “Observed after the filing — not used in the original classification.”
- “Genuinely new” is described in primary product language as new relative to the filings and headlines available in this study.
- Fidelity, AEW, and other institutions are not presented as validators.

## Result

Content reconciliation passed. No frozen data or classifications were changed for presentation convenience.
