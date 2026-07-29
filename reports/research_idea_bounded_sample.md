# Research Idea Engine — Bounded Eight-Case Input Sample

**Status:** PASS  
**Scope:** Phase A gold demonstration set only  
**Outcome information used:** No  
**Packets generated:** Not part of this step

## Source lock

The allowed-input bundle is built only from the authoritative
`pure-news-disclosure-change-demo-v1/reports/tables/case_studies.csv` table.

- Expected source SHA-256:
  `fa7e4fb3809d622ddee4144fc3b75d54314db7091491d3635f194b0f5349396d`
- Expected row count: `8`
- Selection order: ascending `case_order`, exactly `1` through `8`
- Membership lock: exact `(case_order, change_id, ticker)` tuples shown below
- Allowed source-column boundary: `case_order` through
  `change_novelty_method`, inclusive
- Builder:
  `scripts/build_research_idea_inputs.py`
- Output:
  `demo/data/research_idea_inputs/v1/eight_case_inputs.json`

The builder fails before writing output if the source hash, source schema
prefix, row count, ordered IDs, or tickers differ from the lock.

## Membership

| Order | Issuer | Ticker | Change ID | Selection rationale |
|---:|---|:---:|---|---|
| 1 | Truist Financial Corp | TFC | `dbe75bc24f2888f4166a` | Liquidity deterioration |
| 2 | Kraft Heinz Co | KHC | `8f5336b55618ffe68e8a` | Debt/refinancing pressure |
| 3 | Dollar Tree, Inc. | DLTR | `339fae2941721ee094b0` | Impairment |
| 4 | Devon Energy Corp | DVN | `4784f62ad001b2a12af4` | Capex change |
| 5 | RH | RH | `412b08746bb0ed5a7745` | New risk factor |
| 6 | Freeport-McMoRan Inc | FCX | `8d4598f4ea16f15c7048` | Change already anticipated by an intervening 8-K |
| 7 | Equifax Inc | EFX | `279e7d4e407851a19548` | Corpus-bounded genuinely new annual disclosure |
| 8 | Chemed Corp | CHE | `2f22dc2216c9df31d377` | Null or low-materiality comparison |

For all eight rows, the frozen
`selection_used_future_outcomes` flag is `false`.

## Allowed input contract

Only filing-time or earlier fields are copied:

- issuer, ticker, CIK, PERMNO, sector code, filing IDs, accession numbers
- current and prior filing dates and SEC acceptance timestamps
- filing section and current/prior SEC source URLs
- exact current and prior excerpts
- added and removed text
- current and prior evidence offsets
- changed-number, new-entity, and matched-term metadata
- frozen category, direction, materiality, confidence, and alignment metadata
- novelty classification and its bounded prior-source search counts/method
- matched prior 8-K and pre-filing news records
- the existing reason code and explanation
- case-selection rationale and outcome-independence flag
- current/prior parsed-artifact and primary-document SHA-256 hashes

The source table has no separate `reason_code` column. The bundle therefore
uses the frozen `change_category_slug` as `reason.code` and preserves
`change_why_it_matters` as `reason.why_it_matters`.

The formation timestamp is the current filing's SEC acceptance timestamp.
The builder rejects a prior filing, related 8-K, or related news timestamp
later than that timestamp.

## Explicit exclusions

The cutoff excludes `change_novelty_is_causal_claim` and every later source
column. In particular, none of the following enters the bundle:

- 12-month maximum drawdown
- 12-month realized volatility
- drawdown threshold labels
- 6-month or 12-month abnormal returns
- ex-post downside outcomes
- selection or outcome stage labels

The output also omits both local parsed-artifact paths from
`change_evidence_provenance`. Only the four frozen provenance document hashes
are retained. A recursive output audit rejects Windows drive paths,
`file://` URIs, and home-directory paths.

## Deterministic identifiers and hashes

Input IDs use:

`research-idea-input-v1:<change_id>`

Evidence IDs are deterministic for the prior/current 10-K excerpts,
added/removed text, each matched prior 8-K accession, and each matched news
story-chain ID.

Each member hash is SHA-256 over canonical JSON before its
`member_sha256` field is added. The bundle hash is SHA-256 over the
case-ordered manifest:

`input_id<TAB>member_sha256<LF>`

| Order | Ticker | Member SHA-256 |
|---:|:---:|---|
| 1 | TFC | `ab5391740a7256c1de5219fa490b2f50c741055e03ae9f43ca5a9428236331f7` |
| 2 | KHC | `1f1ad41a7c13ba64109bf3604f35ad89849ec0732f509bad4074f6b67ba68931` |
| 3 | DLTR | `99d86312ed7d03498567642cab2581004603af22caf4a9382eac4007f3ed4f41` |
| 4 | DVN | `4f23ed094488118287364da4a04edfaddd7a4ee00b4e09782a5b1018a0191fb8` |
| 5 | RH | `849a672e4aad05b8cf56a7616012f70f98e1435e5b393650906dbe4bec766972` |
| 6 | FCX | `718f9aba0cdd161b4c3ea35d90d0907de0510de5f52a7326daf550db5066c73c` |
| 7 | EFX | `ff3ec52f37c10e27d53634772d5aebec1116f1becd2439f45a0ef8b9862080ac` |
| 8 | CHE | `4ffdcac873359b2a5b8d05ca6c20777d2cfad9156da678a1c98d9ef070ff4a4e` |

- Bundle manifest SHA-256:
  `b79e392fcf82ba13f7dfa9c6b7e539e8e702bea040d0f7bdbb6404dd4ae17322`
- Serialized output SHA-256:
  `8088ed16c4a1d4aee13d9047c440f255f7a51233829f261a46bed7037b6abfcf`

## Reproduction and self-audit

Run from the repository root:

```powershell
python scripts\build_research_idea_inputs.py
```

The builder also accepts explicit `--source` and `--output` paths. The
validation run produced:

```text
status=PASS
case_count=8
member_hashes_verified=8
forbidden_key_count=0
local_path_value_count=0
reproducible_output=true
source_hash_mismatch_rejected=true
```

No human ratings, generated hypotheses, later outcomes, or packet acceptance
decisions are represented in this input bundle.
