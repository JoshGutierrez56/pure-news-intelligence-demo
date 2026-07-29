# Research Idea Engine V1 — scope and design contract

## Decision

V1 extends the evidence workflow from **what changed?** to **what should an
analyst investigate next?** It remains a decision-support demonstration. It
does not select securities autonomously and does not produce a trade
recommendation.

The user-visible feature name is **AI Research Idea**. Its optional market
expression is always labeled **Illustrative Trade Hypothesis — Analyst Review
Required**.

## Bounded scope

- Gate set: I0 through I4, followed by public integration only if the bounded
  packet gates pass.
- Generation set: the eight frozen, outcome-independent case studies.
- Stratified 60-change sample: `NOT RUN`.
- Full 995-record generation: `NOT AUTHORIZED`.
- Public mode: precomputed, frozen, validated JSON only.
- Local mode: an explicitly invoked Python CLI against a localhost Ollama
  service. The public pages never call a model.
- Analyst state: local browser storage only.

## Protected research surfaces

The following inputs and conclusions are frozen. The implementation may read
them but must not rewrite their data, classifications, excerpts, novelty
labels, case membership, or empirical results.

- `demo/data/changes.json`, `demo/data/catalog.json`, and all `.pni.bin`
  partitions
- `demo/evidence_packets/`
- the eight upstream `case_studies.csv` rows
- `demo/research_results.html`
- existing case-selection content and ex-post outcome labels

Generation receives a whitelist-only derivative of the upstream case table.
The source table's ex-post columns—beginning with `maximum_drawdown_12m`—are
never copied into the model input. Local provenance paths are removed.

## Claim boundary

The original studies did not establish reliable incremental alpha. Raw 10-K
features did not improve the locked multisource model. Expected-disclosure
models did not beat prior-10-K persistence. The bounded disclosure-change
risk analysis was inconclusive.

The operational demo therefore supports no alpha, causal, trading,
customer-adoption, willingness-to-pay, analyst-time-savings, commercial
validity, or institutional-endorsement claim. Generated ideas are unvalidated
research hypotheses.

Every rendered packet must show:

> AI-generated research hypothesis based on the cited evidence. It is not a
> fact, personalized investment advice, or a validated trading signal. Analyst
> review is required.

## Architecture

1. Build a deterministic, formation-time-only input bundle.
2. Validate the bundle and evidence identifiers.
3. Run the pinned local generator with structured JSON output.
4. Cache by model, prompt, schema, options, and input hashes.
5. Run a separate skeptical-review stage that returns only the frozen response
   envelope; the stage-one pending lifecycle is expected input, not a defect.
6. Apply only schema-safe reviewer corrections to inference fields under
   `research_idea_skeptic_application_v1.7`. Validate the raw response envelope
   before narrative normalization, map the intended final lifecycle before
   correction validation, and force a hold if a required correction is
   rejected from an otherwise publishable review. Retain only non-no-op
   correction records that match the final serialized value.
7. Run deterministic grounding, leakage, language, and integrity audits.
8. Publish only validated artifacts; retain held or rejected artifacts for
   transparent review.
9. Render static pages from the frozen packet index.
10. Save analyst disposition only in local storage.

No hidden reasoning is persisted. No cloud endpoint, credential, paid API,
current price, return, drawdown, later commentary, or post-filing source is
used.

## Model freeze

- Runtime: Ollama `0.32.5`, localhost only
- Model: `qwen3.6:35b-a3b`
- Manifest digest:
  `sha256:07d35212591fc27746f0a317c975a6d68754fb38e9053d82e25f06057af28522`
- Temperature: `0`
- Seed: `20260728`
- Context: `32768`
- Maximum output: `8192`
- Thinking storage: disabled
- Generator prompt SHA-256:
  `22de2d6bf245a0bbeb2e7fdf9ec618f2115d6236a3a5393f129db881b540ead7`
- Skeptic prompt SHA-256:
  `c308632c768a59ef6ef6bdb02f886ba53f4c7c2c3b74cec1f836def1f03235ab`
- Structured output: local `format: json` constrained to a strict nine-field
  analytical projection with per-case evidence-ID enums, followed immediately
  by validation against the frozen full JSON Schema. Ollama `0.32.5` rejected
  the full Draft 2020-12 schema grammar, so that failed request path was not
  used for the bounded run.
- Retries: at most one schema-repair retry

Accepted packets are immutable cache entries and are never regenerated
silently.

## Product hierarchy

The detail page follows this evidence-first order:

1. Source evidence
2. What changed
3. Novelty and materiality
4. Economic mechanisms
5. Research hypotheses
6. Analyst questions
7. Affected entities
8. Bull, base, and bear scenarios
9. Illustrative trade hypothesis
10. Skeptical review
11. Analyst disposition
12. Save or export

Evidence, system interpretation, AI-generated hypotheses, analyst review, and
ex-post outcomes use distinct labels and containers. Ex-post outcomes are not
loaded into the research-idea packet.

## Design-system contract

The feature reuses the existing navy, teal, amber, red, green, blue, gray,
focus, line, surface, radius, shadow, spacing, and type tokens in
`demo/assets/style.css`. New styles must remain restrained and evidence-led:

- minimum 44 px interactive targets
- visible 3 px focus ring
- WCAG 2.2 AA contrast
- semantic headings and landmarks
- dense but readable evidence blocks
- status conveyed by text and iconography, never color alone
- tables with an explicit mobile fallback
- reduced-motion support
- no gradients, decorative charts, glass effects, or unexplained scores

## Component inventory

- packet-status banner and disclaimer
- provenance/evidence ledger
- immutable classification badges
- fact/inference split
- mechanism cards with evidence references and counterarguments
- falsifiable hypothesis cards
- analyst-question checklist
- affected-entity list
- three-scenario grid
- guarded illustrative-trade panel
- skeptical-review objections and alternatives
- local-only analyst disposition editor
- deterministic packet export
- gallery filter/sort/result-count/empty state
- methodology trust checklist
- guided professor example

## Gate decisions

| Gate | Requirement | Final bounded status |
| --- | --- | --- |
| I0 | Inspect, preserve, branch, receipt | PASS |
| I1 | Freeze schema and prompts | PASS |
| I2 | Deterministic adverse fixtures | PASS |
| I3 | Generate and audit eight cases | PASS — 0 publishable, 4 held, 4 rejected |
| I4 | Human-ready exports; no invented ratings | PASS |
| I5 | Deterministic 60-change sample | NOT RUN |
| I6 | Scale decision | HOLD_GROUNDING |
| I7 | Public integration | HOLD — feature-branch review surfaces only |
| I8 | Deploy and verify | NOT RUN |

The 60-change sample and full corpus remain outside this implementation unless
a later, explicit authorization is provided.
