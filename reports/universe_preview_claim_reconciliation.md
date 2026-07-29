# Universe Preview Claim Reconciliation

## Required public language

The preview now states:

> Broad U.S. public-company coverage preview based on issuers observed in a
> frozen 2012–2024 SEC 8-K metadata corpus.

It also states:

> Metadata indexing does not mean full disclosure-change analysis has been
> completed.

## Frozen metrics

| Claim | Frozen value | Result |
|---|---:|---|
| Total issuers indexed | 6,190 | PASS |
| Curated 10-K metadata | 149 | PASS |
| Recent 8-K metadata | 3,072 | PASS |
| Permitted news metadata | 776 | PASS |
| Fully validated issuers | 149 | PASS |
| Indexed but not fully validated | 6,041 | PASS |
| Exact `Not yet processed` status | 2,973 | PASS |

## Unsupported implications

The public preview does not state or imply that:

- all 6,190 issuers were fully analyzed;
- every issuer has 10-K coverage;
- all news was collected;
- the corpus represents current exchange or Russell 3000 membership;
- 6,190 issuers have evidence packets; or
- research hypotheses were generated across the full universe.

The page continues to label missing news as unavailable rather than zero and
distinguishes metadata indexing from disclosure analysis and Research Idea
Engine review.

## Research preservation

- Research manifest SHA-256:
  `1611006a6a85fa9702846b22af4a957d2a2d2d0597123f7615d65bf71077f2d7`
- Frozen V1/V2 packets and locked research results: unchanged.
- Formal blinded human review: pending.
- 60-case phase: blocked and not run.
- Live `gh-pages`: `61c50b0`; unchanged.

Final claim-reconciliation result: **PASS**.
