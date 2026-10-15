# Does this workflow help an analyst?

**The evaluation machinery is implemented; analyst effectiveness is not yet established.** No human ratings, time savings, adoption or usefulness gains have been collected or invented. The existing eight-case idea gate and blocked 60-case expansion remain unchanged.

## The question and fair comparisons

Given the same allowed disclosure evidence, does the workflow improve supported change identification and decision-relevant research questions without increasing unsupported claims?

Four frozen conditions:

1. **Filing diff:** deterministic sentence-level diff plus the original source excerpts.
2. **Source search:** the same original excerpts with case-insensitive text search.
3. **Extractive summary:** the first two sentences of each excerpt plus the complete excerpts. This is a reproducible simple summarizer, **not an LLM baseline**. It does not establish superiority over a generic ChatGPT or other LLM workflow.
4. **Pure News:** the existing evidence-linked research interpretation, uncertainty and falsification/counterargument material, with the same excerpts.

No new model inference is required for calibration. Do not strengthen one condition with additional documents unavailable to the others. A future LLM-summary comparison requires a separately frozen model/version, prompt, input budget and analysis amendment before observing that comparison's outcomes.

## Ready now: a calibration package, not a study result

`research_ops.study` prepares **three already-public cases** (RH, DVN and EFX), **eight pseudonymous reviewer slots**, and **24 assigned tasks**. Each case receives two assignments per condition. Each reviewer sees a case only once, avoiding within-person case repetition. The assignments are seeded, orders randomized and packet hashes frozen. The reviewers are slots, **not eight recruited people**.

Use calibration to test instructions, answer collection and adjudication. The packet generator never labels these familiar public excerpts as unseen evaluation data. They are selected public examples, not a random filing-pair sample, and EFX uses curated earlier evidence rather than a freshly acquired adjacent annual-filing pair. No effectiveness conclusion should be drawn from this package.

```sh
python -m research_ops.study prepare-calibration --output ../private-analyst-calibration
```

Open one assigned `REVIEWER-*.html` file in a browser. It has accessible local forms, pause/resume timing, source links, search when assigned, preserved drafts on case navigation and JSON export. No data leaves the page. Visible-tab active time excludes pauses/hidden tabs; external reading time is separately reported and added. This is not passive proof of total analyst work time. Export before closing; local in-page state is not a server-backed record.

Keep `PRIVATE_ASSIGNMENT_KEY.json` and the adjudication file away from participants. Distribute only each reviewer's assigned HTML. All repository labels and method IDs are removed from participant payloads, but differences in format can reveal a method. This is **brand/method-label blinding, not guaranteed full blinding**. Existing project contributors or reviewers who know a case cannot supply unseen-case evidence.

## Prospective study to execute with real reviewers

- Before collection, freeze at least **12 genuinely unexposed cases** sampled from a defined eligible filing-pair universe, with documented stratification for substantive changes, wording-only changes and numeric-comparison traps. Record issuer/date exclusions and the full sampling denominator. Do not pick cases because the engine did well.
- Freeze all four condition outputs and the shared source corpus before randomization. Record acquisition timestamps/versions. Current-vintage filing dates alone do not certify a historical information set.
- Recruit eight eligible human reviewers independently of system development. Record experience, case familiarity, consent and availability privately. Do not pretend placeholder reviewer IDs are enrolled people. Recruitment/outreach has not been performed.
- Twelve cases × eight reviewers yields **96 tasks**, two ratings per case/condition and three tasks per condition per reviewer. This is a feasible pilot design, **not a power justification**. Determine sample-size needs before a confirmatory study using an explicit minimum meaningful effect and plausible variance, not a post-hoc favorable effect.
- Two source-grounded adjudicators, blinded to condition and system disposition, define the salient-change inventory before rating participant answers. Resolve disagreements with a recorded rationale, never simply adopt the engine's published PASS/REJECT label as truth. Use a separate adjudicator to score each answer against that inventory. Retain disagreement records.
- Log no-shows, unusable sessions, prior familiarity, withdrawals and timeouts. The scorer refuses silent deletion or partial-case comparisons. Resolve replacements under a predeclared protocol; if complete collection is not possible, publish missingness and descriptive partial observations separately without the comparative claim.

The preparation API rejects public calibration cases in prospective mode. That is an implementation gate, not independent proof that a case has never been seen. Exposure declarations and sampling records require actual review.

## Measurements and analysis

The reviewer records findings, evidence references, uncertainty/next step, abstention, usefulness (1–5), familiarity and measured/reported task time. Separately adjudicated fields are:

- **Factual support:** supported factual claims / factual claims made. Zero claims is **undefined**, not perfect precision.
- **Salient-change recall:** identified inventory changes / inventory changes. Zero gold changes is undefined recall; assess abstention separately.
- **Missed changes:** gold changes minus identified gold changes. Publish counts as well as recall so a quiet answer cannot hide omissions.
- **Abstention accuracy:** whether abstention matches the adjudicated absence of a substantive supported change. A good research question is not the same as an actionable trade.
- **Usefulness:** anchored 1 = no help/misleading; 2 = limited help with major edits; 3 = usable after material checking; 4 = useful with minor edits; 5 = directly useful for the stated task. It is an ordinal subjective rating, not investment value.
- **Time:** visible active seconds plus declared external reading seconds. Compare time only alongside factual support/recall; fast unsupported answers are not successful.
- **Reviewer disagreement:** pairwise absolute usefulness differences within case/condition, plus retained adjudication records. Agreement is not validity.

The scorer reports all condition summaries and Pure-News-minus-baseline differences using paired **case means**. It provides 2,000 seeded case-bootstrap intervals, treating the participating reviewers as fixed. These are descriptive intervals, not reviewer-population inference, a multiplicity-adjusted significance claim or proof of superiority. Defined-denominator counts remain visible. No primary/secondary metric is chosen after observing favorable results; support and recall are the primary quality outcomes, usefulness/time are secondary descriptive outcomes.

```sh
python -m research_ops.study score --key ../private-analyst-calibration/PRIVATE_ASSIGNMENT_KEY.json --ratings ../private-analyst-calibration/adjudicated_ratings.csv --mode human --output ../private-analyst-calibration/analysis.json
```

The blank prepared ratings file correctly fails scoring. Every assigned task, reviewer identity, separate adjudicator, denominator and time must be supplied. `synthetic_qa` mode exists only for explicitly labeled software fixtures; it always reports zero human ratings. A text value `human` is not proof of real human participation. Verify actual signed-off collection records before publishing any human-evidence claim.

## Current release boundary

Implemented: counterbalanced preparation, public-case calibration, participant interface, local response export, validated adjudication schema, comparison calculations, uncertainty/disagreement reporting and failure tests. Pending external evidence: eligible reviewers, an independently adjudicated unseen sample, actual collection and reviewed conclusions. Live SEC ingestion also remains blocked by the observed 403; the acquisition tool records that failure rather than inventing fresh evidence.
