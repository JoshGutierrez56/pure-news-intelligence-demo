# EFX outcome-blinded evidence review

## Decision

**REJECT_CURRENT_PACKET**

The EFX packet does not support publication, prompt tuning on the packet as a
positive example, or expansion to the 60-change sample. The decisive defect is
upstream evidence selection: the `$125 million` contingent top-up was already
disclosed in the prior 2020 Form 10-K, but the bounded prior excerpt omitted
that disclosure and exposed only the separate `$346.7 million` payment
balance.

This review is outcome-blinded: it did not use later returns, prices, analyst
estimates, or ex-post outcome labels. It is not recorded as a human rating.
The reviewer is an AI assistant performing an independent source-evidence
check, and the packet's human `analyst_disposition` remains `UNREVIEWED`.

## Materials reviewed

- Frozen EFX packet `279e7d4e407851a19548`
- Equifax 2021 Form 10-K filed February 24, 2022
- Equifax 2020 Form 10-K filed February 25, 2021
- The packet's cited current and prior excerpts
- The full filing passages governing the Consumer Settlement, settlement
  payments, and legal-contingency accounting

The review was not disposition-blinded: the existing packet status and
skeptical-review objections were already visible. The conclusions below were
therefore re-tested directly against the two SEC filings.

## Source reconciliation

### 1. The `$125 million` top-up was not new

The 2020 Form 10-K states that Equifax agreed to contribute `$380.5 million`
to the Consumer Restitution Fund and up to an **additional `$125.0 million`**
if the original fund was exhausted. The 2021 Form 10-K repeats the same
structure.

The frozen classification `genuinely new in the 10-K` is therefore not
supportable for the `$125 million` obligation. The apparent novelty arose
because the selected prior excerpt did not include the already-existing
settlement description elsewhere in the same prior filing.

### 2. `$346.7 million` and `$125 million` are not competing caps

The 2020 Form 10-K describes `$346.7 million` as the **remaining amount to be
paid** to the Consumer Restitution Fund after Equifax had made other legal
settlement payments. It is a payment balance tied to the already-accrued
settlement program.

The `$125 million` amount is a separate, conditional top-up available only if
the `$380.5 million` fund is exhausted. Asking whether `$125 million` is "in
addition to the `$346.7 million`" is arithmetically understandable, but the
packet incorrectly treats `$346.7 million` as a comparable prior exposure or
alternative cap. The full prior filing already explains the relationship.

### 3. The current filing's real update was settlement finality and payment

The 2021 Form 10-K says the Consumer Settlement became effective on
January 11, 2022, triggering an approximately `$345 million` deposit, and
states that Equifax deposited `$345.0 million` on January 24, 2022.

That finality-and-payment update is materially different from discovering a
new `$125 million` tail risk. The packet does not isolate this actual change.

### 4. Reserve inadequacy is unsupported

The filings state that Equifax recorded `$800.9 million` of expenses, net of
insurance recoveries, in 2019 as its best estimate of the liability for the
cybersecurity-related matters. They also state that losses above the accrual
were reasonably possible but not estimable.

Nothing in the reviewed evidence establishes that the `$125 million`
conditional amount was inadequately reserved. The packet's "Liability
Adequacy Test" turns a contingent contractual term into an accounting
conclusion without the necessary reserve roll-forward or claims-utilization
evidence.

### 5. Current liquidity and bondholder effects are unsupported

The statement that operating cash flow might be insufficient applied to the
2021 payment schedule in the prior filing. It cannot be carried forward as a
current liquidity fact. Likewise, a conditional settlement-fund top-up is not
an existing debt instrument and does not directly increase leverage or impair
bondholders.

## Claim-level verdict

- Evidence provenance and filing identity: **PASS**
- Formation-time discipline: **PASS**
- `$125 million` novelty claim: **FAIL**
- `$346.7 million` comparison framing: **FAIL**
- Reserve-inadequacy hypothesis: **FAIL**
- Current-liquidity mechanism: **FAIL**
- Bondholder/leverage mechanism: **FAIL**
- Trade hypothesis: **WITHHELD**, correctly
- Publication readiness: **REJECT**

## Gate effect

- EFX moves conceptually from `HOLD_INSUFFICIENT_EVIDENCE` to
  `REJECT_CURRENT_PACKET` for the independent review.
- The frozen V1 packet and its hashes are not mutated.
- No human score or analyst acceptance is fabricated.
- The 60-change sample remains blocked.
- No prompt, schema, classifier, or public deployment change is authorized by
  this review.

## Recommended next action

Repair the upstream evidence-window and novelty logic so a candidate claim is
checked against the full prior filing, not only the selected comparison
excerpt. Then freeze a new version and rerun the bounded eight cases before
considering the 60-change sample. The EFX packet should be retained as a
negative regression fixture.

## Sources

- 2021 Form 10-K:
  <https://www.sec.gov/Archives/edgar/data/33185/000003318522000014/efx-20211231.htm>
- 2020 Form 10-K:
  <https://www.sec.gov/Archives/edgar/data/33185/000003318521000025/efx-20201231.htm>

