# Universe Preview Data Provenance

## Frozen sources

1. `demo/data/catalog.json` and 13 SEC gzip partitions
   - 296,119 parsed 8-K metadata records
   - 2012-01-03 through 2024-12-31
   - issuer, ticker, CIK, accession identifier, date, acceptance time, items, category, public URL, hash, and text length
   - filing bodies are not duplicated in preview outputs
2. Ten permitted-news metadata partitions
   - 731,682 headline-level metadata records
   - 2015-02-02 through 2024-12-31
   - ticker, headline where permitted, host, timestamp, and identifiers
   - article bodies are excluded
3. `demo/data/changes.json`
   - 995 curated disclosure-change records
   - 149 unique issuer CIKs represented in the public records
   - supplies the preview’s available latest 10-K date, accession, and URL
4. `demo/data/research_ideas/v2/manifest.json`
   - eight bounded issuer review outcomes

Every input hash is recorded in `demo/data/universe_preview/source_manifest.json`.

## Important count distinction

The locked disclosure-change study reports 150 issuer-disjoint filing pairs. The public `changes.json` records map to 149 unique CIKs with retained public changes. The preview therefore reports 149 issuer records as fully validated, without changing the locked 150-pair research claim.

## Missing-value policy

- No permitted news match → `news_metadata_count: null` and `latest_news_timestamp: null`.
- No curated 10-K record → 10-K fields are `null`.
- No 2024 8-K record in the frozen corpus → `recent_8k_count: 0`.
- Every missing field is named in `missing_fields`.

Zero is used only when the bounded SEC corpus supports a true zero count. Missing news is never treated as zero.
