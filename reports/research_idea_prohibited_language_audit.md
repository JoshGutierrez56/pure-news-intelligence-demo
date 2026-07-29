# Research Idea Prohibited-Language Audit

## Result

**PASS — 8/8 final packets passed with 0 prohibited-language violations.**

This control passed even though the overall quality classification is `HOLD_GROUNDING`. All eight packets have `trade_readiness: NOT_READY`, `current_market_data_used: false`, and `no_position_size_generated: true`.

## Registry and scope

- Registry version: `1.0`
- Registry SHA-256: `6c77381ab6c79883b2d0cd740576216a967c656defb7553712554279c71ab59a`
- Blocked phrases: 18
- Blocked recommendation/action patterns: 5
- Prohibited trade-construction field names: 7
- Supplemental numeric action patterns: 4

The registry covers direct transaction instructions, guarantees, certain-profit language, buy/sell signals, trade recommendations, model portfolios, target prices, position sizing, personalized recommendations, leverage, stop-loss instructions, and portfolio allocations.

## Context-aware behavior

The scan is deliberately context aware:

- Exact source evidence is not treated as generated recommendation language.
- Removal logs are treated as reviewer documentation rather than active transaction instructions, and quoted prohibited vocabulary in reviewer prose is normalized before validation.
- Negated safeguards such as “No position size generated” and “It is not personalized investment advice” are allowed.
- Negation is phrase-local: sentence and clause boundaries reset the context, and conjunctions or unrelated wording prevent a distant negation from suppressing a later transaction instruction.
- Intervening words may connect a negation to a blocked phrase only when every token is in the registry's explicit 27-term direct-negation bridge allowlist.
- Numeric trade-construction language is checked separately for position size, target price, leverage, and allocation patterns.
- Prohibited field names are rejected even if their values appear innocuous.
- The raw skeptic response envelope must pass its strict schema before narrative normalization. Reviewer-only objections, alternatives, removal reasons, and summaries then normalize quoted prohibited vocabulary before the final language scan; correction replacement content is deliberately excluded from this normalization and still fails closed.

These exceptions prevent legitimate risk disclosure and safety language from being mistaken for an instruction to transact.

The adversarial controls explicitly reject `This is not investment advice. Buy now.`, `This is not a fact; sell the stock.`, and `This is not a recommendation, but buy now.` while continuing to permit directly negated safety statements.

## Packet results

| Ticker | Packet status | Language audit | Violations | Trade readiness | No position size |
|---|---|---|---:|---|---|
| CHE | `HOLD_INSUFFICIENT_EVIDENCE` | `PASS` | 0 | `NOT_READY` | Yes |
| DLTR | `HOLD_INSUFFICIENT_EVIDENCE` | `PASS` | 0 | `NOT_READY` | Yes |
| DVN | `REJECTED_BY_SKEPTIC` | `PASS` | 0 | `NOT_READY` | Yes |
| EFX | `HOLD_INSUFFICIENT_EVIDENCE` | `PASS` | 0 | `NOT_READY` | Yes |
| FCX | `REJECTED_BY_SKEPTIC` | `PASS` | 0 | `NOT_READY` | Yes |
| KHC | `REJECTED_BY_SKEPTIC` | `PASS` | 0 | `NOT_READY` | Yes |
| RH | `REJECTED_BY_SKEPTIC` | `PASS` | 0 | `NOT_READY` | Yes |
| TFC | `HOLD_INSUFFICIENT_EVIDENCE` | `PASS` | 0 | `NOT_READY` | Yes |

## Interpretation

Passing this audit means the final serialized packets contain none of the registered prohibited generated language or trade-construction fields in disallowed contexts. It does not make the packets advice, validate their hypotheses, or establish that every possible unsafe phrase is detectable. Human review remains required, and no packet is publishable.
