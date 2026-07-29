# Universe Preview Packaging Integrity

## Scope

This audit covers the four generated public JSON assets under
`demo/data/universe_preview/`. The validated preview source is commit
`43beba25a878f52736848288e16e030f30bbacd9`; the packaging repair is
`37af530a62a16a9b8f3289e42bbebfc7498fc35b`.

Git blobs are the source of truth. A path-specific `.gitattributes` rule sets
only the universe-preview JSON assets to `text eol=lf`. Supporting builder and
manifest files also receive narrow LF rules so deterministic checks survive a
Windows clean checkout. No global text-normalization rule was changed.

## Four-way byte audit

For every asset, the working-tree, staged-index, current-commit, and source-
commit SHA-256 values are identical.

| Asset | Bytes | SHA-256 | Semantic JSON SHA-256 |
|---|---:|---|---|
| `build_receipt.json` | 755 | `8baaa7f4bb1c2a15a4a300e19492011759772186a83fae9a9ea8f033fe0bc6ac` | `2b4cabe4a1da5c4145094540d0f9fc90087181d451594dd39ac096373e821088` |
| `source_manifest.json` | 3,870 | `8b896467a719c4f2fb23eacdeb8166239740cd300f7517c82a619b53461f94cb` | `d7e40214147a59e908c103e40281d7751bd813cd9ecbe2828a874766df8a47b4` |
| `universe_coverage.json` | 4,136,821 | `9a5930919767b8295ea82c47109935529e2406ad5b0ecab10d5a029b88e35628` | `970c9459009271a8bd077b0c56ba3914c6a3282b6f212d861e928da4ded3da83` |
| `universe_summary.json` | 914 | `09f35d5ce2f1f8ffbe6a0a357b0b848875d687c94e1d0e8f3d329c388d04d7a2` | `0a5a7fa1cc677e2bfe5cdef02f0a649b67e5a9cb6f53a18702583abaca536798` |

All four assets parse as JSON, contain LF rather than CRLF line endings, and
retain their original semantics and byte hashes from commit `43beba2`.

## Deterministic manifest

`artifacts/universe_preview_public_asset_manifest.json` records each path,
raw byte size, SHA-256, semantic JSON hash, record count, build timestamp, and
source commit. Its builder reads committed Git blobs rather than Windows
working-tree representations.

## Clean-clone verification

The first clean-clone run identified CRLF checkout drift in the builder script
and generated asset manifest. That defect was corrected with narrow LF rules.

The final clean clone at `37af530` passed:

- universe-output deterministic check;
- public-asset-manifest deterministic check;
- 14 focused Python integrity tests;
- Git attribute verification (`text: set`, `eol: lf`);
- clean working tree after verification.

Final packaging-integrity result: **PASS**.
