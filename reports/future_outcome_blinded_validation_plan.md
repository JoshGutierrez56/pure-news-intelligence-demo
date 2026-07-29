# Future outcome-blinded validation plan

## Purpose

V1 evaluates research-workflow quality, not returns. No Sharpe ratio,
information coefficient, hit rate, or realized profitability is used to
generate, select, edit, approve, or rank an idea.

## Prospective freeze

Before an evaluation participant sees outcomes, freeze:

- source evidence and formation timestamp
- condition assignment
- prompt, schema, model, runtime, and sampling hashes
- generated and skeptical-review outputs
- analyst edits and disposition
- start and completion timestamps
- data-access log

An independent leakage check must confirm that the packet contains no
post-formation filing, news, commentary, price, return, drawdown, or ex-post
label. Outcome data remain in a separately permissioned table keyed only after
the workflow study is locked.

## Comparison conditions

Use randomized, counterbalanced assignments across analysts and cases:

1. disclosure change only
2. generic AI summary
3. AI research idea
4. AI research idea plus skeptical review
5. analyst-edited AI research idea
6. human idea created without AI

The same case must not be shown to the same analyst in multiple conditions.
Case allocation should balance category, novelty, materiality, sector, year,
and evidence complexity without using future outcomes.

## Primary workflow measures

- analyst acceptance, edit, rejection, and escalation rates
- time to a usable research agenda
- evidence-grounding score
- falsifiability and testability scores
- useful cross-company connections
- follow-up questions adopted
- analyst preference
- institutional-memory usefulness
- affected-entity and instrument-mechanism accuracy
- edit burden

Time-savings language is prohibited until this design is piloted and the
measurement is reported with uncertainty.

## Human rubric

Two independent reviewers should score each artifact from 1–5 for evidence
grounding, relevance, specificity, novelty, mechanism clarity, falsifiability,
testability, usefulness, non-obviousness, concision, affected-entity accuracy,
instrument-mechanism fit, risk disclosure, and edit burden.

Reviewers also choose one disposition:

- accept
- accept with edits
- reject
- escalate
- unsupported
- obvious / low value

Resolve disagreements through a predeclared adjudication process. Report
inter-rater agreement and the full disposition distribution; do not suppress
negative ratings.

## Analysis

Pre-register the primary comparisons and sample-size rationale. Use
participant- and case-level clustered uncertainty or an appropriate crossed
mixed-effects model. Report medians and distributions for time measures, not
only means. Treat reviewer scores as ordinal unless a predeclared sensitivity
analysis supports another treatment.

Do not optimize prompts or select templates using later outcomes. Prompt
changes discovered during the workflow study require a new frozen version and
separate evaluation cohort.

## Later, separate market-outcome study

Only prospectively frozen ideas may enter a later research project. That
separate protocol may evaluate:

- out-of-sample information coefficient
- after-cost Sharpe ratio
- hit rate
- signal decay
- realized versus implied volatility
- hypothesis confirmation or rejection

The later study must define instrument mapping, timestamp alignment,
tradability, delistings, corporate actions, transaction costs, liquidity,
multiple-testing control, and publication rules before outcomes are attached.
Its results must not retroactively alter the V1 workflow-quality evaluation.

## Go/no-go decision

Advance beyond bounded analyst review only if grounding, falsifiability,
testability, edit burden, leakage, accessibility, and skeptical-review gates
are met. A favorable historical return pattern is neither necessary nor
sufficient for that decision.
