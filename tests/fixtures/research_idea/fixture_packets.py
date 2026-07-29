"""Deterministic, offline Gate I2 packets for Research Idea Engine V1.

These fixtures are built from the locked eight-case formation-time bundle.
They do not invoke Ollama, store chain of thought, use ex-post outcomes, or
represent human analyst ratings.
"""

from __future__ import annotations

import copy
from typing import Any

from research_idea_common import (
    DEFAULT_DISCLAIMER,
    MODEL_OPTIONS,
    PINNED_MODEL,
    PINNED_MODEL_DIGEST,
    SCHEMA_PATH,
    compute_cache_key,
    compute_packet_hash,
    sha256_file,
    sha256_text,
)


TRADE_LABEL = "Illustrative Trade Hypothesis — Analyst Review Required"
GENERATOR_PROMPT_HASH = sha256_text("gate-i2-generator-fixture-v1")
SKEPTIC_PROMPT_HASH = sha256_text("gate-i2-skeptic-fixture-v1")


def records_by_ticker(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index the locked bounded inputs by ticker."""

    inputs = bundle.get("inputs")
    if not isinstance(inputs, list) or len(inputs) != 8:
        raise ValueError("Gate I2 fixtures require the locked eight-case bundle")
    records = {str(record["ticker"]): record for record in inputs}
    if len(records) != 8:
        raise ValueError("Gate I2 bundle must contain eight unique tickers")
    return records


def _evidence_id(change_id: str, suffix: str) -> str:
    return f"EV-{change_id}:{suffix}"


def _source_evidence_id(record: dict[str, Any], field_name: str) -> str:
    """Return the exact frozen evidence ID from the bounded input."""

    return str(record["evidence"]["evidence_ids"][field_name])


def _related_prior_8k(
    record: dict[str, Any], item: dict[str, Any]
) -> dict[str, Any]:
    return {
        "evidence_id": item["evidence_id"],
        "accession_number": str(item["accession_number"]),
        "url": item["url"],
        "acceptance_timestamp": item["acceptance_timestamp"],
        "information_date": item["information_date"],
        "item_codes": item["item_codes"],
        "match_score": item["match_score"],
        "matched_terms": list(item.get("matched_terms", [])),
        "primary_category": item["primary_category"],
        "similarity": item["similarity"],
    }


def _related_prior_news(
    record: dict[str, Any], item: dict[str, Any]
) -> dict[str, Any]:
    chain_id = str(item["story_chain_id"])
    return {
        "evidence_id": item["evidence_id"],
        "story_chain_id": chain_id,
        "provider_host": item["provider_host"],
        "publication_timestamp": item["publication_timestamp"],
        "headline": item["headline"],
        "match_score": item["match_score"],
        "matched_terms": list(item.get("matched_terms", [])),
        "similarity": item["similarity"],
    }


def _evidence(record: dict[str, Any]) -> dict[str, Any]:
    change_id = record["change_id"]
    source = record["evidence"]
    identifiers = record["identifiers"]
    prior_url = record["prior_filing"]["source_url"]
    current_url = record["source_url"]
    ids = {
        "prior_excerpt": _source_evidence_id(record, "prior_excerpt"),
        "current_excerpt": _source_evidence_id(record, "current_excerpt"),
        "added_text": _source_evidence_id(record, "added_text"),
        "removed_text": _source_evidence_id(record, "removed_text"),
    }
    return {
        "prior_filing_id": identifiers["prior_filing_id"],
        "current_filing_id": identifiers["current_filing_id"],
        "prior_source_url": prior_url,
        "current_source_url": current_url,
        "prior_excerpt": source["prior_excerpt"],
        "current_excerpt": source["current_excerpt"],
        "added_text": source["added_text"],
        "removed_text": source["removed_text"],
        "evidence_ids": ids,
        "evidence_offsets": {
            "prior": copy.deepcopy(source["offsets"]["prior"]),
            "current": copy.deepcopy(source["offsets"]["current"]),
        },
        "evidence_offsets_verified": True,
        "related_prior_8k": [
            _related_prior_8k(record, item)
            for item in source.get("related_prior_8k", [])
        ],
        "related_prior_news": [
            _related_prior_news(record, item)
            for item in source.get("related_prior_news", [])
        ],
    }


def _model_run(
    *,
    role: str,
    source_hash: str,
    prompt_hash: str,
) -> dict[str, Any]:
    schema_hash = sha256_file(SCHEMA_PATH)
    cache_key = compute_cache_key(
        stage=role.casefold(),
        model_digest=PINNED_MODEL_DIGEST,
        prompt_hash=prompt_hash,
        schema_hash=schema_hash,
        input_hash=source_hash,
        options=MODEL_OPTIONS,
    )
    return {
        "role": role,
        "run_status": "NOT_RUN",
        "model_name": PINNED_MODEL,
        "model_manifest_digest": f"sha256:{PINNED_MODEL_DIGEST}",
        "runtime_name": "Ollama",
        "runtime_version": "0.32.5",
        "prompt_version": (
            "research-idea-generator-v1"
            if role == "GENERATOR"
            else "research-idea-skeptic-v1"
        ),
        "prompt_sha256": prompt_hash,
        "schema_version": "1.0",
        "schema_sha256": schema_hash,
        "temperature": 0,
        "seed": MODEL_OPTIONS["seed"],
        "context_length": MODEL_OPTIONS["num_ctx"],
        "maximum_output_tokens": MODEL_OPTIONS["num_predict"],
        "think_enabled": False,
        "started_at": None,
        "completed_at": None,
        "request_sha256": None,
        "response_sha256": None,
        "cache_key_sha256": cache_key,
        "attempt": 0,
    }


def _generation_metadata(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "generation_policy_version": "research_idea_generation_policy_v1",
        "generator_run": _model_run(
            role="GENERATOR",
            source_hash=record["member_sha256"],
            prompt_hash=GENERATOR_PROMPT_HASH,
        ),
        "skeptic_run": _model_run(
            role="SKEPTIC",
            source_hash=record["member_sha256"],
            prompt_hash=SKEPTIC_PROMPT_HASH,
        ),
        "hardware": {
            "operating_system": "Fixture-only offline test environment",
            "cpu": "No model invoked",
            "system_memory_gib": 1,
            "gpu": "No model invoked",
            "gpu_memory_mib": 0,
        },
        "no_cloud_calls": True,
        "no_chain_of_thought_stored": True,
        "valid_outputs_cached": True,
        "maximum_schema_repair_retries": 1,
        "accepted_packet_regeneration_policy": "NEVER_SILENTLY_REGENERATE",
    }


def _audit_metadata(
    record: dict[str, Any],
    *,
    packet_status: str,
    referenced_ids: list[str],
) -> dict[str, Any]:
    return {
        "audit_version": "research_idea_audit_v1",
        "audited_at": None,
        "schema_validation": {
            "status": "NOT_RUN",
            "validator_name": "jsonschema Draft202012Validator",
            "validator_version": "fixture-not-run",
            "validated_at": None,
            "errors": [],
        },
        "grounding": {
            "status": "NOT_RUN",
            "checked_claim_count": 0,
            "grounded_claim_count": 0,
            "critical_defects": [],
        },
        "future_information": {
            "status": "NOT_RUN",
            "formation_timestamp": record["formation_timestamp"],
            "checked_timestamp_count": 0,
            "violations": [],
        },
        "evidence_integrity": {
            "status": "NOT_RUN",
            "referenced_evidence_ids": referenced_ids,
            "unresolved_evidence_ids": [],
            "source_url_present": True,
            "offsets_verified": True,
        },
        "prohibited_language": {
            "status": "NOT_RUN",
            "registry_version": "1.0",
            "matches": [],
            "violation_count": 0,
        },
        "determinism": {
            "status": "NOT_RUN",
            "cache_hit": False,
            "repeated_generation_matches": None,
            "stable_content_sha256": None,
        },
        "publication_decision": packet_status,
        "audit_findings": [],
    }


def _fact(record: dict[str, Any], statement: str) -> dict[str, Any]:
    return {
        "fact_id": f"FACT-{record['change_id']}:1",
        "statement": statement,
        "fact_type": "filing_text",
        "evidence_ids": [
            _source_evidence_id(record, "current_excerpt")
        ],
    }


def _inference(
    record: dict[str, Any],
    statement: str,
    *,
    inference_type: str = "economic_mechanism",
    confidence: float = 0.55,
    caveat: str = "The filing language alone does not establish the outcome.",
) -> dict[str, Any]:
    return {
        "inference_id": f"INF-{record['change_id']}:1",
        "statement": statement,
        "inference_type": inference_type,
        "evidence_ids": [
            _source_evidence_id(record, "current_excerpt")
        ],
        "confidence": confidence,
        "caveat": caveat,
    }


def _uncertainty(record: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "uncertainty_id": f"UNC-{record['change_id']}:1",
        "uncertainty": text,
        "why_it_matters": "The missing information can change the mechanism.",
        "data_needed": ["Issuer disclosures available after analyst review"],
    }


def _mechanism(
    record: dict[str, Any],
    *,
    mechanism: str,
    driver: str,
    counterargument: str,
) -> dict[str, Any]:
    return {
        "mechanism_id": f"MECH-{record['change_id']}:1",
        "mechanism": mechanism,
        "affected_financial_driver": driver,
        "causal_chain": [
            "The verified filing language identifies a bounded exposure.",
            "If the exposure becomes operative, the financial driver may change.",
        ],
        "supporting_evidence_ids": [
            _source_evidence_id(record, "current_excerpt")
        ],
        "counterargument": counterargument,
        "mechanism_confidence": 0.62,
    }


def _hypothesis(
    record: dict[str, Any],
    *,
    number: int,
    title: str,
    hypothesis: str,
    expected_direction: str,
    required_data: list[str],
    confirmation: str,
    falsification: str,
) -> dict[str, Any]:
    return {
        "hypothesis_id": f"HYP-{record['change_id']}:{number}",
        "title": title,
        "hypothesis": hypothesis,
        "expected_direction": expected_direction,
        "time_horizon": "Next four reported quarters",
        "unit_of_analysis": "Issuer-quarter",
        "required_data": required_data,
        "confirmation_conditions": [confirmation],
        "falsification_conditions": [falsification],
        "confounders": [
            "Broad changes in interest rates or operating performance"
        ],
        "evidence_ids": [
            _source_evidence_id(record, "current_excerpt")
        ],
        "novelty_assessment": (
            "The test is an inference; the filing evidence does not validate it."
        ),
        "testability_score": 0.82,
        "grounding_score": 0.84,
    }


def _questions(record: dict[str, Any]) -> list[dict[str, Any]]:
    prompts = [
        (
            "What covenant thresholds and headroom applied at formation?",
            "Headroom determines whether the disclosed default pathway is near.",
            "Debt agreements and covenant calculations",
        ),
        (
            "Which waivers had been requested before formation?",
            "Prior waivers distinguish a live constraint from generic language.",
            "Pre-filing waiver disclosures",
        ),
        (
            "How much committed facility capacity was available?",
            "Available capacity bounds liquidity consequences.",
            "Facility size, borrowings, and availability",
        ),
        (
            "When does the issuer's debt mature?",
            "The maturity schedule defines the relevant research horizon.",
            "Formation-time debt maturity schedule",
        ),
        (
            "What portion of interest expense is rate-sensitive?",
            "Rate sensitivity separates covenant risk from market-rate effects.",
            "Fixed and variable debt details",
        ),
    ]
    evidence_id = _source_evidence_id(record, "current_excerpt")
    return [
        {
            "question_id": f"Q-{record['change_id']}:{index}",
            "question": question,
            "why_it_matters": why,
            "required_data": [data],
            "evidence_ids": [evidence_id],
        }
        for index, (question, why, data) in enumerate(prompts, start=1)
    ]


def _scenarios(
    record: dict[str, Any],
    *,
    topic: str,
) -> dict[str, Any]:
    evidence_id = _source_evidence_id(record, "current_excerpt")
    return {
        "bull": {
            "scenario": f"{topic} remains contained.",
            "conditions": ["No evidence of the disclosed constraint emerging"],
            "implications": ["The proposed mechanism is not confirmed"],
            "evidence_ids": [evidence_id],
        },
        "base": {
            "scenario": f"{topic} requires monitoring but does not escalate.",
            "conditions": ["Mixed evidence in subsequent issuer disclosures"],
            "implications": ["Maintain the item as a research question"],
            "evidence_ids": [evidence_id],
        },
        "bear": {
            "scenario": f"{topic} becomes economically binding.",
            "conditions": ["Subsequent disclosed data confirm the mechanism"],
            "implications": ["The falsifiable hypothesis receives support"],
            "evidence_ids": [evidence_id],
        },
    }


def _trade(
    record: dict[str, Any],
    *,
    status: str = "NO_ACTIONABLE_VIEW",
    candidate_view: str = "no actionable view",
    instrument: str = "no instrument identified",
    rationale: str = "The evidence supports research, not transaction readiness.",
    readiness: str = "NOT_READY",
    guarded: bool = False,
) -> dict[str, Any]:
    guardrails = (
        {
            "entry_or_confirmation_conditions": [
                "Confirm the mechanism with current issuer and market data"
            ],
            "invalidation_conditions": [
                "Issuer data contradict the proposed mechanism"
            ],
            "key_risks": ["The disclosure may be precautionary"],
            "market_data_required_before_action": [
                "Current price, spread, volatility, and instrument availability"
            ],
            "liquidity_and_cost_checks": [
                "Current bid-ask spread, depth, and transaction costs"
            ],
        }
        if guarded
        else {
            "entry_or_confirmation_conditions": [],
            "invalidation_conditions": [],
            "key_risks": [],
            "market_data_required_before_action": [],
            "liquidity_and_cost_checks": [],
        }
    )
    return {
        "label": TRADE_LABEL,
        "status": status,
        "candidate_view": candidate_view,
        "preferred_instrument_class_to_investigate": instrument,
        "instrument_rationale": rationale,
        "expected_horizon": "Not determined without analyst research",
        **guardrails,
        "evidence_ids": [
            _source_evidence_id(record, "current_excerpt")
        ],
        "trade_readiness": readiness,
        "trade_readiness_reason": (
            "Current market, liquidity, cost, and portfolio context are absent."
        ),
        "current_market_data_used": False,
        "illustrative_only": True,
        "analyst_review_required": True,
        "no_position_size_generated": True,
    }


def _skeptic(
    record: dict[str, Any],
    *,
    status: str,
    critical_defect: bool,
    objections: list[str],
    alternatives: list[str] | None = None,
    pricing: list[str] | None = None,
    removed: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "review_version": "research_idea_skeptic_v1",
        "critical_objections": objections,
        "alternative_explanations": alternatives or [
            "The language may reflect routine drafting rather than a changed exposure."
        ],
        "pricing_or_attention_concerns": pricing or [
            "Formation-time inputs do not establish whether the issue was priced."
        ],
        "unsupported_claims_removed": removed or [],
        "evidence_ids_reviewed": [
            _source_evidence_id(record, "prior_excerpt"),
            _source_evidence_id(record, "current_excerpt"),
        ],
        "critical_grounding_defect": critical_defect,
        "final_review_status": status,
        "review_summary": (
            "The fixture records the skeptical disposition without a model call."
        ),
    }


def _base_packet(
    record: dict[str, Any],
    *,
    packet_status: str,
    plain_language_change: str,
    fact_statement: str,
    inference_statement: str | None,
    uncertainty: str,
    mechanisms: list[dict[str, Any]],
    hypotheses: list[dict[str, Any]],
    affected_entities: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    scenarios: dict[str, Any],
    trade: dict[str, Any],
    skeptic: dict[str, Any],
) -> dict[str, Any]:
    current_id = _source_evidence_id(record, "current_excerpt")
    packet = {
        "packet_version": "1.0",
        "packet_id": f"research-idea-v1:{record['change_id']}",
        "packet_status": packet_status,
        "change_id": record["change_id"],
        "issuer": record["issuer"],
        "ticker": record["ticker"],
        "filing_date": record["filing_date"],
        "formation_timestamp": record["formation_timestamp"],
        "section": record["section"],
        "source_url": record["source_url"],
        "input_lineage": {
            "input_contract_version": "research_idea_input_v1",
            "source_record_sha256": record["member_sha256"],
            "allowed_input_fields_used": [
                "issuer",
                "ticker",
                "filing_date",
                "formation_timestamp",
                "section",
                "prior_filing_excerpt",
                "current_filing_excerpt",
                "added_language",
                "removed_language",
                "frozen_classification",
                "related_prior_8k",
                "related_prior_news",
                "source_urls_and_identifiers",
                "current_product_reason_code",
                "evidence_offsets",
            ],
            "formation_time_enforced": True,
            "future_information_excluded": True,
            "post_filing_news_excluded": True,
            "ex_post_outcomes_excluded": True,
            "cloud_calls_made": False,
        },
        "evidence": _evidence(record),
        "frozen_classification": {
            "category": record["frozen_classification"]["category"],
            "direction": record["frozen_classification"]["direction"],
            "materiality": record["frozen_classification"]["materiality"],
            "novelty": record["novelty"]["classification"],
            "confidence": record["frozen_classification"]["confidence"],
            "classification_method": record["frozen_classification"][
                "classification_method"
            ],
            "novelty_method": record["novelty"]["method"],
            "novelty_is_causal_claim": False,
        },
        "system_interpretation": {
            "plain_language_change": plain_language_change,
            "evidence_facts": [_fact(record, fact_statement)],
            "inferences": (
                [] if inference_statement is None else [
                    _inference(record, inference_statement)
                ]
            ),
            "uncertainties": [_uncertainty(record, uncertainty)],
        },
        "economic_mechanisms": mechanisms,
        "affected_entities": affected_entities,
        "research_hypotheses": hypotheses,
        "analyst_questions": questions,
        "scenario_analysis": scenarios,
        "illustrative_trade_hypothesis": trade,
        "skeptical_review": skeptic,
        "confidence": {
            "evidence": 0.8,
            "novelty": 0.5,
            "mechanism": 0.55,
            "hypothesis": 0.55,
            "trade_readiness": 0.1,
        },
        "analyst_disposition": {
            "status": "UNREVIEWED",
            "analyst_notes": "",
            "edited_fields": [],
            "review_timestamp": None,
            "saved_locally_only": True,
        },
        "generation_metadata": _generation_metadata(record),
        "audit_metadata": _audit_metadata(
            record,
            packet_status=packet_status,
            referenced_ids=[current_id],
        ),
        "disclaimer": DEFAULT_DISCLAIMER,
    }
    packet["packet_hash"] = compute_packet_hash(packet)
    return packet


def strong_grounded_liquidity_packet(record: dict[str, Any]) -> dict[str, Any]:
    """Publishable, testable covenant/liquidity fixture."""

    mechanism = _mechanism(
        record,
        mechanism=(
            "If covenant non-compliance requires a waiver, access to the "
            "Senior Credit Facility could become constrained."
        ),
        driver="Funding access and interest expense",
        counterargument=(
            "The passage may be precautionary and does not show a current breach."
        ),
    )
    hypotheses = [
        _hypothesis(
            record,
            number=1,
            title="Covenant headroom and facility access",
            hypothesis=(
                "If the disclosed waiver pathway becomes operative, reported "
                "covenant headroom or undrawn facility availability will decline "
                "within the next four reported quarters."
            ),
            expected_direction="Lower headroom or availability",
            required_data=[
                "Quarterly covenant calculations",
                "Committed facility availability",
            ],
            confirmation=(
                "A subsequent issuer disclosure reports a waiver request, lower "
                "headroom, or reduced facility availability."
            ),
            falsification=(
                "No waiver is requested and covenant headroom and facility "
                "availability remain stable through four reported quarters."
            ),
        ),
        _hypothesis(
            record,
            number=2,
            title="Financing-cost sensitivity",
            hypothesis=(
                "Conditional on a waiver request or reduced facility access, "
                "issuer-reported interest expense will rise relative to the "
                "formation-date debt baseline over four reported quarters."
            ),
            expected_direction="Higher interest expense, conditional on trigger",
            required_data=[
                "Quarterly interest expense",
                "Debt balances and effective rates",
            ],
            confirmation=(
                "Interest expense rises after a disclosed waiver or access constraint."
            ),
            falsification=(
                "Interest expense does not rise after the disclosed trigger, after "
                "accounting for debt balances."
            ),
        ),
    ]
    affected = [
        {
            "entity_id": f"ENTITY-{record['change_id']}:1",
            "entity_or_group": record["issuer"],
            "relationship": "Issuer subject to the disclosed debt covenants",
            "possible_effect": "Potentially reduced funding flexibility",
            "reason": "The current excerpt describes default and waiver pathways.",
            "evidence_ids": [
                _source_evidence_id(record, "current_excerpt")
            ],
            "confidence": 0.82,
        }
    ]
    return _base_packet(
        record,
        packet_status="PUBLISHABLE",
        plain_language_change=(
            "The current filing adds specific language about covenant waivers, "
            "cross-default risk, and access to the Senior Credit Facility."
        ),
        fact_statement=(
            "The current excerpt states that a covenant breach without a waiver "
            "could leave the issuer in default and unable to access its Senior "
            "Credit Facility."
        ),
        inference_statement=(
            "A future waiver need could constrain funding access or raise financing costs."
        ),
        uncertainty=(
            "The excerpt does not provide current covenant headroom or show a breach."
        ),
        mechanisms=[mechanism],
        hypotheses=hypotheses,
        affected_entities=affected,
        questions=_questions(record),
        scenarios=_scenarios(record, topic="Covenant and facility risk"),
        trade=_trade(
            record,
            status="RESEARCH_ONLY",
            candidate_view="credit-negative",
            instrument="corporate bonds",
            rationale=(
                "Debt instruments match a covenant and funding-access mechanism, "
                "but current spread and liquidity data are absent."
            ),
            guarded=True,
        ),
        skeptic=_skeptic(
            record,
            status="PASS",
            critical_defect=False,
            objections=[
                "The excerpt does not show that a breach or waiver need is current."
            ],
            pricing=[
                "Related prior disclosure lowers novelty and may have drawn attention."
            ],
        ),
    )


def previously_disclosed_risk_packet(record: dict[str, Any]) -> dict[str, Any]:
    """Hold fixture where prior disclosure weakens novelty and usefulness."""

    return _base_packet(
        record,
        packet_status="HOLD_INSUFFICIENT_EVIDENCE",
        plain_language_change=(
            "The annual filing contains risk language related to an exposure "
            "already classified as previously disclosed in an 8-K."
        ),
        fact_statement=(
            "The frozen novelty classification is previously disclosed in 8-K."
        ),
        inference_statement=(
            "The annual filing may add little incremental information beyond the prior 8-K."
        ),
        uncertainty="The bounded match does not establish investor attention or pricing.",
        mechanisms=[],
        hypotheses=[],
        affected_entities=[],
        questions=[],
        scenarios=_scenarios(record, topic="Previously disclosed risk"),
        trade=_trade(record),
        skeptic=_skeptic(
            record,
            status="HOLD_INSUFFICIENT_EVIDENCE",
            critical_defect=True,
            objections=[
                "Prior 8-K evidence weakens the claim that this annual language is new."
            ],
            pricing=[
                "The available inputs cannot establish whether prior disclosure was priced."
            ],
        ),
    )


def ambiguous_boilerplate_packet(record: dict[str, Any]) -> dict[str, Any]:
    """Hold fixture for a heading-like, low-information alignment."""

    return _base_packet(
        record,
        packet_status="HOLD_AMBIGUOUS",
        plain_language_change=(
            "The aligned current text is a section heading and does not provide "
            "enough substantive content for a grounded mechanism."
        ),
        fact_statement=(
            "The current excerpt contains the Item 7 management discussion heading."
        ),
        inference_statement=None,
        uncertainty=(
            "The alignment may reflect document structure rather than an economic change."
        ),
        mechanisms=[],
        hypotheses=[],
        affected_entities=[],
        questions=[],
        scenarios=_scenarios(record, topic="Document-alignment ambiguity"),
        trade=_trade(record),
        skeptic=_skeptic(
            record,
            status="HOLD_AMBIGUOUS",
            critical_defect=True,
            objections=[
                "A section heading cannot support a causal mechanism or testable hypothesis."
            ],
        ),
    )


def unsupported_causal_claim_packet(record: dict[str, Any]) -> dict[str, Any]:
    """Rejected fixture where the skeptic removes an unsupported causal leap."""

    removed_claim = (
        "The impairment language by itself establishes that future operating "
        "losses will occur."
    )
    return _base_packet(
        record,
        packet_status="REJECTED_BY_SKEPTIC",
        plain_language_change=(
            "The filing reports an impairment-related disclosure change."
        ),
        fact_statement="The current excerpt reports an impairment charge.",
        inference_statement=None,
        uncertainty=(
            "The excerpt does not establish future operating performance."
        ),
        mechanisms=[],
        hypotheses=[],
        affected_entities=[],
        questions=[],
        scenarios=_scenarios(record, topic="Impairment interpretation"),
        trade=_trade(
            record,
            status="WITHHELD_BY_SKEPTIC",
            candidate_view="insufficient evidence",
        ),
        skeptic=_skeptic(
            record,
            status="REJECTED_BY_SKEPTIC",
            critical_defect=True,
            objections=[
                "The proposed causal claim is not supported by the filing excerpt."
            ],
            removed=[removed_claim],
        ),
    )


def instrument_mismatch_packet(record: dict[str, Any]) -> dict[str, Any]:
    """Rejected fixture where an option expression does not fit the mechanism."""

    return _base_packet(
        record,
        packet_status="REJECTED_BY_SKEPTIC",
        plain_language_change=(
            "The filing describes possible regulatory enforcement and funding exposure."
        ),
        fact_statement=(
            "The current excerpt describes possible enforcement action and an "
            "additional consumer-settlement funding obligation."
        ),
        inference_statement=(
            "A realized funding obligation could affect issuer cash requirements."
        ),
        uncertainty=(
            "The excerpt says the issuer did not expect the additional deposit."
        ),
        mechanisms=[
            _mechanism(
                record,
                mechanism=(
                    "An additional settlement-fund obligation could increase cash needs."
                ),
                driver="Cash requirements",
                counterargument=(
                    "The issuer states that it does not expect the obligation."
                ),
            )
        ],
        hypotheses=[],
        affected_entities=[],
        questions=[],
        scenarios=_scenarios(record, topic="Settlement-fund exposure"),
        trade=_trade(
            record,
            status="WITHHELD_BY_SKEPTIC",
            candidate_view="credit-negative",
            instrument="listed options",
            rationale=(
                "The candidate instrument does not directly match the cash-funding mechanism."
            ),
            guarded=True,
        ),
        skeptic=_skeptic(
            record,
            status="REJECTED_BY_SKEPTIC",
            critical_defect=True,
            objections=[
                "Listed options are an instrument mismatch for the proposed credit mechanism."
            ],
        ),
    )


def no_actionable_view_packet(record: dict[str, Any]) -> dict[str, Any]:
    """Valid hold fixture that intentionally returns no actionable view."""

    return _base_packet(
        record,
        packet_status="HOLD_INSUFFICIENT_EVIDENCE",
        plain_language_change=(
            "The aligned change does not support a sufficiently grounded economic view."
        ),
        fact_statement=(
            "The current and prior excerpts contain different risk-topic text."
        ),
        inference_statement=None,
        uncertainty=(
            "The alignment does not show whether the issuer's liquidity position changed."
        ),
        mechanisms=[],
        hypotheses=[],
        affected_entities=[],
        questions=[],
        scenarios=_scenarios(record, topic="Unresolved disclosure change"),
        trade=_trade(record),
        skeptic=_skeptic(
            record,
            status="HOLD_INSUFFICIENT_EVIDENCE",
            critical_defect=True,
            objections=[
                "The verified text does not support an actionable economic mechanism."
            ],
        ),
    )


def future_data_leakage_packet(record: dict[str, Any]) -> dict[str, Any]:
    """Schema-valid fixture contaminated by a post-formation headline."""

    packet = no_actionable_view_packet(record)
    packet["packet_id"] = f"research-idea-v1:{record['change_id']}:future-leak"
    packet["evidence"]["related_prior_news"].append(
        {
            "evidence_id": _evidence_id(
                record["change_id"], "prior-news:future-fixture"
            ),
            "story_chain_id": "future-fixture",
            "provider_host": "example.com",
            "publication_timestamp": "2099-01-01T00:00:00Z",
            "headline": "Post-formation fixture headline",
            "match_score": 1.0,
            "matched_terms": ["fixture"],
            "similarity": 0.1,
        }
    )
    packet["packet_hash"] = compute_packet_hash(packet)
    return packet


def invalid_schema_packet(record: dict[str, Any]) -> dict[str, Any]:
    """Fixture with a deliberately missing required formation timestamp."""

    packet = no_actionable_view_packet(record)
    packet["packet_id"] = f"research-idea-v1:{record['change_id']}:invalid-schema"
    packet.pop("formation_timestamp")
    packet["packet_hash"] = compute_packet_hash(packet)
    return packet


def prohibited_recommendation_packet(record: dict[str, Any]) -> dict[str, Any]:
    """Schema-valid fixture containing a generated transaction instruction."""

    packet = no_actionable_view_packet(record)
    packet["packet_id"] = f"research-idea-v1:{record['change_id']}:prohibited"
    packet["illustrative_trade_hypothesis"]["instrument_rationale"] = (
        "Buy now because the disclosure establishes the direction."
    )
    packet["packet_hash"] = compute_packet_hash(packet)
    return packet


def all_named_packets(
    records: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Return the nine required Gate I2 fixture scenarios."""

    packets = {
        "strong_grounded_liquidity": strong_grounded_liquidity_packet(
            records["KHC"]
        ),
        "previously_disclosed_risk": previously_disclosed_risk_packet(
            records["FCX"]
        ),
        "ambiguous_boilerplate": ambiguous_boilerplate_packet(records["CHE"]),
        "unsupported_causal_claim": unsupported_causal_claim_packet(
            records["DLTR"]
        ),
        "instrument_mismatch": instrument_mismatch_packet(records["EFX"]),
        "no_actionable_view": no_actionable_view_packet(records["TFC"]),
        "future_data_leakage": future_data_leakage_packet(records["RH"]),
        "invalid_schema": invalid_schema_packet(records["DVN"]),
        "prohibited_recommendation_language": prohibited_recommendation_packet(
            records["DLTR"]
        ),
    }
    return copy.deepcopy(packets)
