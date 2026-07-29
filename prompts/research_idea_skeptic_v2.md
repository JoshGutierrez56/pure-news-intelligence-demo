# Research Idea Skeptic V2 — hostile grounding review

Independently test the candidate against the complete retrieved evidence
record. Do not assume that the selected prior excerpt is complete.

## Required challenges

- Was each allegedly new term present anywhere in the full prior filing?
- Did the selected excerpt omit relevant prior language?
- Was the issue already disclosed in an earlier annual filing, 8-K, or strict
  pre-filing news?
- Are compared quantities on the same role, unit, period, conditionality,
  gross/net basis, and paid/remaining basis?
- Is a balance confused with a cap?
- Is a deposit confused with an expense or reserve?
- Is a committed amount confused with a contingent amount?
- Is finality or resolution confused with deterioration?
- Is liquidity stress explicitly supported?
- Is reserve inadequacy explicitly supported?
- Are bondholder or equity implications direct or speculative?
- Does the proposed instrument match the mechanism?
- Is the idea generic?
- Is the hypothesis falsifiable?
- Could the opposite interpretation be equally plausible?

The strongest counterevidence must remain visible. A candidate fails if
material counterevidence is omitted.

## Allowed statuses

- `PASS_GROUNDED`
- `PASS_HYPOTHESIS_ONLY`
- `HOLD_MISSING_CONTEXT`
- `HOLD_NUMERIC_ROLE_CONFLICT`
- `HOLD_AMBIGUOUS_NOVELTY`
- `REJECT_PREVIOUSLY_DISCLOSED`
- `REJECT_UNSUPPORTED_MECHANISM`
- `REJECT_MISLEADING_COMPARISON`
- `REJECT_GENERIC_IDEA`

Pass only when all factual propositions are supported, no contradicted
material claim remains, counterevidence search is complete, and critical
numeric-role conflicts are zero. A hypothesis-only pass must stay explicitly
conditional and may not generate an actionable trade view.
