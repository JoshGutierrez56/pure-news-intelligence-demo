# Research Idea Generation Results

## Bounded result

**HOLD_GROUNDING — all eight packets are structurally valid, but none cleared the semantic grounding gate.**

This is a successful fail-closed validation run, not a successful research-idea result. It does not validate any hypothesis, trading signal, return, alpha, adoption, or commercial claim.

| Result | Count |
|---|---:|
| Packets attempted | 8 |
| Packets validated | 8 |
| Publishable packets | 0 |
| `HOLD_INSUFFICIENT_EVIDENCE` | 4 |
| `REJECTED_BY_SKEPTIC` | 4 |
| Trade hypotheses marked `NOT_READY` | 8 |
| Analyst-reviewed packets | 0 |

The four held packets are CHE, DLTR, EFX, and TFC. The four rejected packets are DVN, FCX, KHC, and RH. The 60-record stratified sample was **NOT RUN**, and no generation beyond the eight-case set was authorized.

## Frozen configuration

| Item | Frozen value |
|---|---|
| Model | `qwen3.6:35b-a3b` |
| Model manifest digest | `sha256:07d35212591fc27746f0a317c975a6d68754fb38e9053d82e25f06057af28522` |
| Runtime | Ollama `0.32.5`, local only |
| Generator prompt SHA-256 | `22de2d6bf245a0bbeb2e7fdf9ec618f2115d6236a3a5393f129db881b540ead7` |
| Skeptic prompt SHA-256 | `c308632c768a59ef6ef6bdb02f886ba53f4c7c2c3b74cec1f836def1f03235ab` |
| Schema SHA-256 | `4a1c2717a477770cbd5fd8dc5566146bf403c91d59c0b97584e837314c9b1ed4` |
| Prohibited-language registry SHA-256 | `6c77381ab6c79883b2d0cd740576216a967c656defb7553712554279c71ab59a` |
| Input membership SHA-256 | `b79e392fcf82ba13f7dfa9c6b7e539e8e702bea040d0f7bdbb6404dd4ae17322` |
| Input bundle file SHA-256 | `8088ed16c4a1d4aee13d9047c440f255f7a51233829f261a46bed7037b6abfcf` |
| Gallery-index stable SHA-256 | `04181d0adb27c3c827e505f18f186f5a36922fa57b037d1597c17f2d4d5be38c` |
| Deterministic options | temperature `0`; seed `20260728`; context `32768`; maximum output `8192`; thinking disabled |

All eight packets record `no_cloud_calls: true`, `no_chain_of_thought_stored: true`, and `future_information_excluded: true`. Five generator runs required the one permitted repair attempt (DLTR, DVN, FCX, KHC, and RH). One skeptic run required the one permitted repair attempt (KHC). No run exceeded the limit. A second bounded invocation returned 8/8 stage-one and 8/8 skeptic packets from valid immutable caches without model generation or silent regeneration.

## Runtime caveat and fail-closed control

Ollama `0.32.5` failed to compile the full frozen Draft 2020-12 packet schema into its grammar. The schema was not weakened or changed. The final local run used:

1. Ollama `format: json`;
2. a strict nine-field model-owned analytical projection;
3. an enumerated evidence-ID allowlist built separately for each case;
4. immediate validation against the frozen full packet schema; and
5. at most one schema-repair attempt.

The nine model-owned fields were `packet_status`, `system_interpretation`, `economic_mechanisms`, `affected_entities`, `research_hypotheses`, `analyst_questions`, `scenario_analysis`, `illustrative_trade_hypothesis`, and `confidence`. The deterministic wrapper supplied the source evidence, identity, lineage, hashes, audit metadata, disposition, and disclaimer. No content was sent to a cloud provider.

## Corrected skeptic contract

The corrected skeptic prompt requires one bounded response envelope, not a complete packet. The last stale placeholder suggesting a full-packet schema was removed. The prompt explicitly treats the stage-one `DRAFT_PENDING_SKEPTIC` / `PENDING_REVIEW` lifecycle as expected input. The final packet set contains zero objections, review summaries, or removal logs that misclassify those pending fields as defects.

Application policy `research_idea_skeptic_application_v1.7` validates the raw skeptic response envelope against its strict schema before any reviewer-narrative normalization. It then maps the skeptic's decision to the intended final lifecycle before validating corrections. This permits a held or rejected packet to end with fewer than two hypotheses without incorrectly validating it against the draft-stage minimum. Corrections are applied one at a time only to permitted inference fields; protected or schema-invalid edits are rejected and logged. Any rejected correction on a would-be `PASS` or `PASS_WITH_EDITS` packet forces `HOLD_UNSUPPORTED`.

The final `unsupported_claims_removed` ledger contains only applied corrections whose replacement remains at the target path in the serialized final packet. The bounded ledger has 20 entries: all 20 equal their final packet values, and none equals the corresponding stage-one value. Reviewer-only narrative is normalized when it quotes prohibited transaction vocabulary, while a prohibited replacement proposed for a packet field still fails validation. Negation is allowed only through an explicit direct-bridge allowlist, which prevents unrelated nearby words from suppressing a prohibited phrase. Only format-specific identifier contradictions may be removed, and only when the reviewer cited a nonempty set of IDs that all resolve to the caller-owned permitted set. The corrected packet set contains zero false pending-lifecycle or identifier-format objections.

## Packet results

| Ticker | Change ID | Packet status | Skeptic status | Trade readiness | Canonical packet hash |
|---|---|---|---|---|---|
| EFX | `279e7d4e407851a19548` | `HOLD_INSUFFICIENT_EVIDENCE` | `HOLD_INSUFFICIENT_EVIDENCE` | `NOT_READY` | `f0795be953c1f9b946579ad3d4d4d4aaaee7d237c269a137e4227d1a7b2d9a7b` |
| CHE | `2f22dc2216c9df31d377` | `HOLD_INSUFFICIENT_EVIDENCE` | `HOLD_INSUFFICIENT_EVIDENCE` | `NOT_READY` | `7d43ba00b7075744ed599f6cd77b578d58d5eda732ef9affb811f41612f779c1` |
| DLTR | `339fae2941721ee094b0` | `HOLD_INSUFFICIENT_EVIDENCE` | `HOLD_INSUFFICIENT_EVIDENCE` | `NOT_READY` | `1715d50142121af012e1185c4881a37b344c13933b0f86506c0662f65c78ef46` |
| RH | `412b08746bb0ed5a7745` | `REJECTED_BY_SKEPTIC` | `REJECTED_BY_SKEPTIC` | `NOT_READY` | `66ff9ef61252eec8ac618e9e1e3469e542547d5450e5a3295ed22f0555171907` |
| DVN | `4784f62ad001b2a12af4` | `REJECTED_BY_SKEPTIC` | `REJECTED_BY_SKEPTIC` | `NOT_READY` | `45853fb155b00b55e8eb0d24bc3315ed604898e1a861b87325ec7f88d8a604a0` |
| FCX | `8d4598f4ea16f15c7048` | `REJECTED_BY_SKEPTIC` | `REJECTED_BY_SKEPTIC` | `NOT_READY` | `23d1795168dc1242096c3eeda951f2146cdee6eb268c7a4cad73947afde524a1` |
| KHC | `8f5336b55618ffe68e8a` | `REJECTED_BY_SKEPTIC` | `REJECTED_BY_SKEPTIC` | `NOT_READY` | `a35baf991764badb752529ed1ad25ed12983f608213663156630449b18d40660` |
| TFC | `dbe75bc24f2888f4166a` | `HOLD_INSUFFICIENT_EVIDENCE` | `HOLD_INSUFFICIENT_EVIDENCE` | `NOT_READY` | `653c331dfdf2b30b2936cb51e715cc71be8d09c7adcb3b9db0db1fbdfd119b80` |

## Automated audits

The final validator returned **PASS** with 8 passed packets, 0 failed packets, 0 errors, and 0 warnings. The validation and audit JSON artifacts are byte-identical at SHA-256 `b45b9be6505c7c46be875a172010d90c1fe2982b2ab96268b2de452c90240cec`. That result means the held and rejected lifecycle states are internally valid; it does not mean any packet cleared publication.

| Audit | Result |
|---|---|
| JSON Schema | 8/8 PASS |
| Evidence integrity and source linkage | 8/8 PASS; 0 unresolved evidence IDs |
| Formation-time / future-information check | 8/8 PASS; 0 violations |
| Prohibited-language check | 8/8 PASS; 0 violations |
| Canonical determinism check | 8/8 PASS |
| Semantic grounding clearance | 0 PASS; 8 HOLD |
| Deterministic engine tests | 67/67 PASS |
| Focused permanent browser suite | 15/15 PASS |
| Complete browser-suite target | 32/32 |

## AI-generated examples

There is no publishable packet, so a publishable example cannot be supplied. The following exact EFX hypothesis remains in a held packet and is shown only for inspection:

> The $125 million contingent liability cap represents a specific, quantified tail risk that may differ from the previously disclosed $346.7M exposure, requiring verification of the total maximum exposure in the settlement agreement.

The skeptic assigned `HOLD_INSUFFICIENT_EVIDENCE` because the packet's wider research agenda still relied on unsupported cash-flow and accounting inferences. The quoted hypothesis remains AI-generated, unvalidated, and non-publishable.

Every final trade section is withheld:

- candidate view: `insufficient evidence`
- instrument: `no instrument identified`
- readiness: `NOT_READY`
- exact rationale: “The skeptical review did not clear a grounded instrument expression from the cited disclosure evidence.”
- exact readiness reason: “The skeptical review did not clear the evidence and mechanism gates.”

FCX demonstrates rejection and no action. It contains no research hypotheses, identifies no instrument, generates no position size, and is `REJECTED_BY_SKEPTIC`.

## Interpretation

The bounded run demonstrates strict temporal input controls, schema enforcement, and skeptical rejection. It did not produce a packet suitable for publication. No human ratings were created, and scaling is blocked pending a grounding-focused revision.

Authoritative machine-readable results: `artifacts/research_idea_engine_validation.json` and `artifacts/research_idea_audit_results.json`.
