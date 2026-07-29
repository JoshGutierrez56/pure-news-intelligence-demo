# Universe Coverage Preview Scope

## Objective

Provide a bounded, metadata-first view of which issuers are present in existing frozen project sources, which source types are available, which issuers are validated in the current demo, and which gaps remain.

## Universe definition

**Label:** Broad U.S. public-company coverage preview  
**Definition:** one normalized issuer record for every valid non-zero CIK observed in the frozen parsed SEC 8-K metadata corpus from 2012-01-03 through 2024-12-31.  
**Issuer count:** 6,190  
**As-of timestamp:** 2024-12-31T23:59:59Z

The latest SEC record supplies the canonical issuer name and ticker. Records are sorted by normalized ten-digit CIK and de-duplicated deterministically.

This is not a dated Russell 3000, S&P, exchange-listing, or comprehensive active-company membership source. Historical issuers, ticker changes, and entities no longer actively traded may remain.

## Included

- issuer identifier, company name, ticker, and CIK
- latest available curated 10-K metadata
- recent 8-K count for the frozen 2024 window and latest 8-K date
- permitted news metadata count and latest timestamp when available
- processing and demo-validation status
- missing fields, source provenance, and as-of timestamp

## Excluded

No filing-body downloads, full-universe comparisons, exhibit extraction, embeddings, inference, research-idea generation, skeptical-review generation, return tests, article bodies, GitHub Pages API calls, 60-case expansion, or deployment.
