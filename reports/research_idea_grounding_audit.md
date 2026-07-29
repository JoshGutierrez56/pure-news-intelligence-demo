# Research Idea Grounding Audit

## Result

**HOLD_GROUNDING — the audit executed successfully, but 0/8 packets cleared semantic grounding.**

All eight packets passed structural, evidence-linkage, temporal, prohibited-language, and deterministic checks. Four were held for insufficient evidence and four were rejected by the skeptic. This is the intended fail-closed outcome, not a validated research result.

## Audit basis

| Artifact | SHA-256 |
|---|---|
| Packet schema | `4a1c2717a477770cbd5fd8dc5566146bf403c91d59c0b97584e837314c9b1ed4` |
| Formation-time input membership | `b79e392fcf82ba13f7dfa9c6b7e539e8e702bea040d0f7bdbb6404dd4ae17322` |
| Formation-time input bundle | `8088ed16c4a1d4aee13d9047c440f255f7a51233829f261a46bed7037b6abfcf` |
| Prohibited-language registry | `6c77381ab6c79883b2d0cd740576216a967c656defb7553712554279c71ab59a` |

The validator reconciled every packet to its exact change ID, source URL, filing identifiers, excerpts, offsets, frozen classifications, formation timestamp, and allowed prior 8-K/news evidence. The generation input was an explicit formation-time allowlist, and each case received its own enumerated set of permitted evidence IDs.

## Control results

| Control | Result |
|---|---|
| Schema validation | 8/8 PASS |
| Source URL present | 8/8 PASS |
| Evidence offsets verified | 8/8 PASS |
| Evidence linkage | 8/8 PASS; 0 unresolved IDs |
| Formation timestamp present | 8/8 PASS |
| Future-information scan | 8/8 PASS; 0 violations |
| Ex-post lineage exclusion | 8/8 recorded `true` |
| Prohibited-language scan | 8/8 PASS; 0 violations |
| Semantic grounding | 0 PASS; 8 HOLD |

## Packet-level findings

“Defect entries” are the literal entries recorded in each packet's grounding audit. They include substantive skeptical defects and wrapper-policy rejection messages; they are not counts of unique economic errors.

| Ticker | Packet status | Evidence references | Unresolved IDs | Timestamps checked | Future violations | Claims checked | Grounding | Defect entries |
|---|---|---:|---:|---:|---:|---:|---|---:|
| CHE | `HOLD_INSUFFICIENT_EVIDENCE` | 2 | 0 | 1 | 0 | 9 | `HOLD` | 5 |
| DLTR | `HOLD_INSUFFICIENT_EVIDENCE` | 3 | 0 | 0 | 0 | 30 | `HOLD` | 9 |
| DVN | `REJECTED_BY_SKEPTIC` | 2 | 0 | 0 | 0 | 24 | `HOLD` | 5 |
| EFX | `HOLD_INSUFFICIENT_EVIDENCE` | 2 | 0 | 0 | 0 | 23 | `HOLD` | 4 |
| FCX | `REJECTED_BY_SKEPTIC` | 2 | 0 | 5 | 0 | 8 | `HOLD` | 6 |
| KHC | `REJECTED_BY_SKEPTIC` | 3 | 0 | 2 | 0 | 31 | `HOLD` | 8 |
| RH | `REJECTED_BY_SKEPTIC` | 6 | 0 | 3 | 0 | 22 | `HOLD` | 6 |
| TFC | `HOLD_INSUFFICIENT_EVIDENCE` | 4 | 0 | 0 | 0 | 17 | `HOLD` | 6 |

The `grounded_claim_count` equals `checked_claim_count` in all eight packets because that field records evidence-reference traceability. It does not override semantic objections; the final grounding status does.

## Why packets were gated

- TFC: the “Liquidity deterioration” label was driven by a disclosure-taxonomy change while the underlying liquidity definition remained unchanged. The generated fine and technology-spend hypotheses were unsupported.
- KHC: conditional covenant language was turned into predictions of breach, waiver dependency, and liquidity stress without evidence of current distress; the packet was rejected.
- DVN: the frozen capex label did not match impairment evidence, and the packet introduced unsupported impairment-reversal, capital-return, credit-spread, and price-threshold claims; the packet was rejected.
- CHE: the current evidence was only a section header and the packet produced no research hypotheses.
- DLTR: hypotheses relied on unsupported impairment-to-performance, debt-covenant, and market-reaction mechanisms; the packet was held with those objections unresolved.
- RH: options and bond expressions were introduced without formation-time evidence that those instruments existed or were liquid; the packet was rejected after its hypotheses were removed.
- FCX: the packet produced no research hypotheses or mechanisms from already-disclosed pandemic-risk language and was rejected.
- EFX: the packet asserted reserve inadequacy, ongoing cash-flow insufficiency, bondholder effects, and market pricing without support in the allowed excerpts and was held for insufficient evidence.

## Held candidate example

There is no publishable example. This exact EFX hypothesis is shown only to make the held research agenda inspectable:

> The $125 million contingent liability cap represents a specific, quantified tail risk that may differ from the previously disclosed $346.7M exposure, requiring verification of the total maximum exposure in the settlement agreement.

The skeptic held the packet because the wider agenda still relied on unsupported current-liquidity and accounting-treatment inferences. The candidate remains AI-generated, unvalidated, and not publishable.

## Boundary

This audit measures evidence linkage, temporal hygiene, and whether the output supports a specific, falsifiable research agenda. It does not use later returns and does not establish causality, alpha, profitability, analyst usefulness, or suitability. The final quality classification is `HOLD_GROUNDING`.
