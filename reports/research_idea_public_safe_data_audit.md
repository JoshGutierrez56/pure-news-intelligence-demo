# Research Idea Public-Safe Data Audit

Status: **PASS**

## Included

The public directory contains exactly four JSON files:

- `manifest.json`
- `rh.json`
- `dvn.json`
- `efx_rejection.json`

The manifest also contains compact safe-failure metadata for CHE, DLTR, FCX, KHC, and TFC. No full rejected packet is copied.

## Integrity checks

- RH source packet file SHA-256: `e9004af7ed1ed1a536a94f0b3a73a658bd1736625c07fd9d055dcc5bb45f7921`
- DVN source packet file SHA-256: `34059b002a144130c44de18de850ed00f09a4fbf052160e134626403b1d7b06f`
- EFX source packet file SHA-256: `32056ef6523c5729fc1f98d1570e586a78dc43cd8a2648fc471599159679438a`
- Public manifest SHA-256: `1611006a6a85fa9702846b22af4a957d2a2d2d0597123f7615d65bf71077f2d7`

The deterministic builder was run twice and produced byte-identical output.

## EFX correction

The public-safe rejection preserves:

- `$125M` → conditional top-up → `PREVIOUSLY_DISCLOSED_IN_10K`
- `$346.7M` → remaining payment balance → not an exposure cap
- `~$345M` → cash deposit → current-period settlement update
- `INCOMPARABLE_QUANTITIES`
- reserve inadequacy, current liquidity stress, and bondholder impact shown only as rejected claims
- `NO_ACTIONABLE_TRADE_VIEW`

## Exclusion audit

Automated tests found none of the following:

- analyst notes or review timestamps
- local filesystem paths or `file://` URLs
- hidden reasoning or chain-of-thought fields
- future returns, realized P&L, or outcome keys
- licensed article bodies
- unpublished full packets for the five compact safe failures

The files contain direct SEC evidence, frozen packet fields, explicit presentation labels, and analyst questions clearly labeled as questions rather than facts.
