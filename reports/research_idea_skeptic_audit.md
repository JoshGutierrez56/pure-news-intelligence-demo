# Research Idea Skeptic Audit

## Result

**HOLD_GROUNDING — the skeptic reviewed all eight packets and cleared none for publication.**

The corrected final distribution was four `HOLD_INSUFFICIENT_EVIDENCE` and four `REJECTED_BY_SKEPTIC`. All eight trade sections are `NOT_READY`, use no current market data, generate no position size, and require analyst review.

## Review distribution

| Skeptic result | Count | Final packet treatment |
|---|---:|---|
| `PASS` or `PASS_WITH_EDITS` | 0 | 0 publishable |
| `HOLD_INSUFFICIENT_EVIDENCE` | 4 | CHE, DLTR, EFX, TFC |
| `REJECTED_BY_SKEPTIC` | 4 | DVN, FCX, KHC, RH |

## Packet-level review

The counts below are literal array-entry counts in the final packets. Some objection entries document wrapper-policy rejections of proposed edits, so they are not counts of unique substantive defects.

| Ticker | Final review | Critical grounding defect | Objection entries | Alternative explanations | Pricing concerns | Final-state correction entries |
|---|---|---:|---:|---:|---:|---:|
| CHE | `HOLD_INSUFFICIENT_EVIDENCE` | Yes | 5 | 4 | 2 | 0 |
| DLTR | `HOLD_INSUFFICIENT_EVIDENCE` | Yes | 9 | 3 | 2 | 2 |
| DVN | `REJECTED_BY_SKEPTIC` | Yes | 5 | 4 | 3 | 4 |
| EFX | `HOLD_INSUFFICIENT_EVIDENCE` | Yes | 4 | 3 | 2 | 3 |
| FCX | `REJECTED_BY_SKEPTIC` | Yes | 6 | 3 | 2 | 1 |
| KHC | `REJECTED_BY_SKEPTIC` | Yes | 8 | 3 | 2 | 6 |
| RH | `REJECTED_BY_SKEPTIC` | Yes | 6 | 3 | 2 | 2 |
| TFC | `HOLD_INSUFFICIENT_EVIDENCE` | Yes | 6 | 3 | 2 | 2 |

Across the bounded set, the final packet records contain 49 objection entries, 26 alternative explanations, 17 pricing/attention concerns, and 20 final-state correction entries. All 20 correction entries match their serialized final values; none equals the corresponding stage-one value. Fifteen proposed corrections were rejected by policy because they targeted protected fields or would not validate against the frozen schema; those rejections are included in the objection count. All affected packets were already held or rejected. No packet passed.

## Corrected prompt and application policy

The frozen skeptic prompt SHA-256 is `c308632c768a59ef6ef6bdb02f886ba53f4c7c2c3b74cec1f836def1f03235ab`. It requires one skeptical-review response envelope rather than a complete packet; the last stale full-packet-schema placeholder was removed. It states that the stage-one `DRAFT_PENDING_SKEPTIC` / `PENDING_REVIEW` lifecycle is expected. A scan of the final skeptical-review fields found zero false pending-lifecycle objections.

Application policy `research_idea_skeptic_application_v1.7` first validates the raw skeptic response envelope against the strict response schema. Narrative normalization cannot rescue a structurally invalid response. The wrapper then maps the review decision to the intended final lifecycle and applies corrections one by one to permitted inference fields. Protected or schema-invalid edits are rejected and logged, while a rejected edit on any would-be publishable result forces `HOLD_UNSUPPORTED`.

Reviewer-only narrative is normalized when it quotes prohibited transaction vocabulary, while prohibited replacement content still fails validation. Direct negation is recognized only when intervening words belong to an explicit bridge allowlist. The identifier filter is restricted to format-specific contradictions and runs only when the reviewer cited a nonempty set of evidence IDs that all resolve to the permitted caller-owned set. The corrected final packets contain zero false identifier-format objections. `unsupported_claims_removed` records only applied, non-no-op corrections whose replacement is still present at that path after all final-state withholding rules run. This corrected the prompt/runtime, correction-ledger, broad-negation, and overbroad identifier-filter mismatches without changing the frozen packet schema.

## What the skeptic caught

- Risk-factor language treated as evidence that the adverse event was imminent.
- Frozen classification mismatches, including taxonomy-versus-liquidity and capex-versus-impairment errors.
- Unsupported causal chains, reserve claims, and false quantitative precision.
- Previously disclosed or generic material presented as novel.
- Issuer evidence extrapolated to peers or an entire sector.
- Instrument choices unsupported by the formation-time input.
- Market-price, spread, return, or estimate-revision claims requiring unavailable data.
- Empty or generic research agendas that were not sufficiently falsifiable.
- Internal inconsistencies between the evidence, mechanisms, scenarios, and trade view.

## Held example

No packet passed the skeptic. EFX was held rather than published. Its exact review summary includes:

> The packet is held because the research hypotheses are not sufficiently grounded in the current filing's facts to support a directional view, and the trade hypothesis is correctly identified as not ready but the reasoning is flawed.

Its final candidate view is `insufficient evidence`, its instrument is `no instrument identified`, and its readiness is `NOT_READY`.

## Rejected / no-action example

FCX is `REJECTED_BY_SKEPTIC`. The final packet contains no research hypotheses and no instrument. Its exact trade rationale and readiness reason are:

> The skeptical review did not clear a grounded instrument expression from the cited disclosure evidence.

> The skeptical review did not clear the evidence and mechanism gates.

RH was also rejected after relying on unsupported options, credit-spread, and peer-impact mechanisms; its final packet contains no research hypotheses.

## Boundary

The skeptic is a second pass by the same pinned local model under a stricter prompt, not an independent human reviewer. It can expose grounding failures but cannot certify truth, novelty, market pricing, suitability, or investment merit. All eight analyst dispositions remain `UNREVIEWED`; the final quality classification is `HOLD_GROUNDING`.
