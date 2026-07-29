"""Gate I2 deterministic tests for the Research Idea Engine.

The suite is intentionally offline: no test starts or calls Ollama.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "research_idea"
for import_path in (SCRIPTS_DIR, FIXTURE_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import generate_research_idea_packets as generator  # noqa: E402
import review_research_idea_packets as reviewer  # noqa: E402
from fixture_packets import all_named_packets, records_by_ticker  # noqa: E402
from research_idea_common import (  # noqa: E402
    DEFAULT_DISCLAIMER,
    FUTURE_DATA_KEYS,
    INPUT_BUNDLE_PATH,
    MODEL_OPTIONS,
    PINNED_MODEL_DIGEST,
    SCHEMA_PATH,
    apply_reviewer_corrections,
    assert_unique_change_ids,
    audit_packet,
    canonical_json,
    collect_evidence_ids,
    compute_cache_key,
    compute_packet_hash,
    find_input,
    iter_json,
    load_json,
    parse_timestamp,
    prohibited_language_findings,
    sha256_file,
    sha256_text,
    validate_schema,
    write_json,
)


CLEAN_FIXTURES = (
    "strong_grounded_liquidity",
    "previously_disclosed_risk",
    "ambiguous_boilerplate",
    "unsupported_causal_claim",
    "instrument_mismatch",
    "no_actionable_view",
)


@pytest.fixture(scope="session")
def input_bundle() -> dict[str, Any]:
    return load_json(INPUT_BUNDLE_PATH)


@pytest.fixture(scope="session")
def input_records(input_bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return records_by_ticker(input_bundle)


@pytest.fixture()
def packets(
    input_records: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return all_named_packets(input_records)


def _source_for(
    input_bundle: dict[str, Any], packet: dict[str, Any]
) -> dict[str, Any]:
    source = find_input(input_bundle, packet["change_id"])
    assert source is not None
    return source


def _refresh_hash(packet: dict[str, Any]) -> dict[str, Any]:
    packet["packet_hash"] = compute_packet_hash(packet)
    return packet


def _as_stage_one(packet: dict[str, Any]) -> dict[str, Any]:
    stage_one = copy.deepcopy(packet)
    stage_one["packet_status"] = "DRAFT_PENDING_SKEPTIC"
    stage_one["skeptical_review"] = {
        "review_version": "research_idea_skeptic_v1",
        "critical_objections": [],
        "alternative_explanations": [],
        "pricing_or_attention_concerns": [],
        "unsupported_claims_removed": [],
        "evidence_ids_reviewed": [],
        "critical_grounding_defect": None,
        "final_review_status": "PENDING_REVIEW",
        "review_summary": "Stage-one artifact; skeptical review has not run.",
    }
    stage_one["audit_metadata"]["publication_decision"] = (
        "DRAFT_PENDING_SKEPTIC"
    )
    return _refresh_hash(stage_one)


def _review_envelope(
    packet: dict[str, Any],
    *,
    final_status: str,
    critical_grounding_defect: bool,
    corrections: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "review_version": "research_idea_skeptic_v1",
        "critical_objections": ["Fixture skeptical objection."],
        "alternative_explanations": ["Fixture alternative explanation."],
        "pricing_or_attention_concerns": ["Fixture pricing concern."],
        "unsupported_claims_removed": [
            "The fixture model proposed removal of unsupported content."
        ],
        "evidence_ids_reviewed": sorted(collect_evidence_ids(packet))[:2],
        "critical_grounding_defect": critical_grounding_defect,
        "final_review_status": final_status,
        "review_summary": "Fixture review summary.",
        "corrections": corrections,
    }


def _finding_codes(packet: dict[str, Any], **kwargs: Any) -> set[str]:
    return {
        finding.code
        for finding in audit_packet(packet, **kwargs).errors
    }


def test_fixture_inventory_is_exact_and_deterministic(
    input_records: dict[str, dict[str, Any]],
) -> None:
    first = all_named_packets(input_records)
    second = all_named_packets(input_records)
    assert tuple(first) == (
        "strong_grounded_liquidity",
        "previously_disclosed_risk",
        "ambiguous_boilerplate",
        "unsupported_causal_claim",
        "instrument_mismatch",
        "no_actionable_view",
        "future_data_leakage",
        "invalid_schema",
        "prohibited_recommendation_language",
    )
    assert canonical_json(first) == canonical_json(second)
    assert len(input_records) == 8


@pytest.mark.parametrize("fixture_name", CLEAN_FIXTURES)
def test_clean_fixtures_validate_and_match_frozen_inputs(
    fixture_name: str,
    packets: dict[str, dict[str, Any]],
    input_bundle: dict[str, Any],
) -> None:
    packet = packets[fixture_name]
    source = _source_for(input_bundle, packet)
    assert validate_schema(packet) == []
    result = audit_packet(packet, source_input=source)
    assert result.passed, result.as_dict()


def test_strong_grounded_liquidity_fixture_has_required_quality(
    packets: dict[str, dict[str, Any]],
) -> None:
    packet = packets["strong_grounded_liquidity"]
    assert packet["packet_status"] == "PUBLISHABLE"
    assert packet["skeptical_review"]["final_review_status"] == "PASS"
    assert packet["skeptical_review"]["critical_grounding_defect"] is False
    assert len(packet["economic_mechanisms"]) == 1
    assert len(packet["research_hypotheses"]) == 2
    assert len(packet["analyst_questions"]) == 5
    assert (
        packet["illustrative_trade_hypothesis"]["trade_readiness"]
        == "NOT_READY"
    )
    assert (
        packet["illustrative_trade_hypothesis"][
            "no_position_size_generated"
        ]
        is True
    )


def test_hold_and_rejection_fixtures_encode_skeptical_dispositions(
    packets: dict[str, dict[str, Any]],
) -> None:
    prior = packets["previously_disclosed_risk"]
    assert "previously disclosed" in prior["frozen_classification"][
        "novelty"
    ].casefold()
    assert prior["packet_status"] == "HOLD_INSUFFICIENT_EVIDENCE"
    assert prior["skeptical_review"]["pricing_or_attention_concerns"]

    boilerplate = packets["ambiguous_boilerplate"]
    assert boilerplate["packet_status"] == "HOLD_AMBIGUOUS"
    assert boilerplate["economic_mechanisms"] == []

    unsupported = packets["unsupported_causal_claim"]
    assert unsupported["packet_status"] == "REJECTED_BY_SKEPTIC"
    assert unsupported["skeptical_review"]["critical_grounding_defect"] is True
    assert unsupported["skeptical_review"]["unsupported_claims_removed"]

    mismatch = packets["instrument_mismatch"]
    assert mismatch["packet_status"] == "REJECTED_BY_SKEPTIC"
    assert (
        mismatch["illustrative_trade_hypothesis"][
            "preferred_instrument_class_to_investigate"
        ]
        == "listed options"
    )
    assert any(
        "instrument mismatch" in objection.casefold()
        for objection in mismatch["skeptical_review"]["critical_objections"]
    )

    no_view = packets["no_actionable_view"]
    assert (
        no_view["illustrative_trade_hypothesis"]["candidate_view"]
        == "no actionable view"
    )
    assert (
        no_view["illustrative_trade_hypothesis"][
            "preferred_instrument_class_to_investigate"
        ]
        == "no instrument identified"
    )


def test_invalid_schema_fixture_is_rejected(
    packets: dict[str, dict[str, Any]],
) -> None:
    packet = packets["invalid_schema"]
    findings = validate_schema(packet)
    assert findings
    assert any(
        finding.path == "/"
        and "formation_timestamp" in finding.message
        and "required" in finding.message
        for finding in findings
    )


def test_generator_validation_rejects_invalid_and_prohibited_outputs(
    packets: dict[str, dict[str, Any]],
) -> None:
    schema = load_json(SCHEMA_PATH)
    invalid_messages = generator.validation_messages(
        packets["invalid_schema"], schema
    )
    prohibited_messages = generator.validation_messages(
        packets["prohibited_recommendation_language"], schema
    )
    assert any("formation_timestamp" in message for message in invalid_messages)
    assert any("buy now" in message.casefold() for message in prohibited_messages)


def test_future_timestamp_is_schema_valid_but_fails_temporal_audit(
    packets: dict[str, dict[str, Any]],
) -> None:
    packet = packets["future_data_leakage"]
    assert validate_schema(packet) == []
    result = audit_packet(packet)
    leakage = [
        finding
        for finding in result.errors
        if finding.code == "FUTURE_DATA_LEAKAGE"
    ]
    assert len(leakage) == 1
    assert leakage[0].path.endswith("/publication_timestamp")
    assert set(finding.code for finding in result.errors) == {
        "FUTURE_DATA_LEAKAGE"
    }


def test_bounded_inputs_contain_only_pre_formation_timestamps(
    input_bundle: dict[str, Any],
) -> None:
    for record in input_bundle["inputs"]:
        formation = parse_timestamp(record["formation_timestamp"])
        for item in record["evidence"].get("related_prior_8k", []):
            assert parse_timestamp(item["acceptance_timestamp"]) <= formation
        for item in record["evidence"].get("related_prior_news", []):
            assert parse_timestamp(item["publication_timestamp"]) <= formation


def test_explicit_ex_post_field_is_detected(
    packets: dict[str, dict[str, Any]],
) -> None:
    packet = copy.deepcopy(packets["strong_grounded_liquidity"])
    packet["outcome"] = {"later_return": 1.0}
    _refresh_hash(packet)
    assert "EX_POST_FIELD_PRESENT" in _finding_codes(packet)


def test_clean_inputs_and_packets_exclude_registered_future_keys(
    input_bundle: dict[str, Any],
    packets: dict[str, dict[str, Any]],
) -> None:
    for value in [input_bundle] + [
        packets[name] for name in CLEAN_FIXTURES
    ]:
        observed = {
            path.rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~")
            for path, _item in iter_json(value)
        }
        assert not ({key.casefold() for key in FUTURE_DATA_KEYS} & {
            key.casefold() for key in observed
        })


def test_prohibited_language_allows_negation_and_source_quotation(
    packets: dict[str, dict[str, Any]],
) -> None:
    # The required disclaimer contains a prohibited noun phrase in an
    # explicitly negated context.
    assert prohibited_language_findings(
        {"disclaimer": DEFAULT_DISCLAIMER}
    ) == []

    quoted_evidence = copy.deepcopy(
        packets["strong_grounded_liquidity"]
    )
    quoted_evidence["evidence"]["added_text"] = (
        'The quoted source contains the words "buy now".'
    )
    assert prohibited_language_findings(quoted_evidence) == []

    removed_by_skeptic = copy.deepcopy(
        packets["strong_grounded_liquidity"]
    )
    removed_by_skeptic["skeptical_review"][
        "unsupported_claims_removed"
    ] = ["Buy now was removed as transaction language."]
    assert prohibited_language_findings(removed_by_skeptic) == []


def test_prohibited_generated_instruction_is_blocked(
    packets: dict[str, dict[str, Any]],
) -> None:
    packet = packets["prohibited_recommendation_language"]
    assert validate_schema(packet) == []
    findings = prohibited_language_findings(packet)
    assert len(findings) == 1
    assert findings[0].code == "PROHIBITED_PHRASE"
    assert findings[0].path == (
        "/illustrative_trade_hypothesis/instrument_rationale"
    )
    assert _finding_codes(packet) == {"PROHIBITED_PHRASE"}


@pytest.mark.parametrize(
    "text",
    (
        "This is not investment advice. Buy now.",
        "This is not a fact; sell the stock.",
        "This is not a recommendation, but buy now.",
        "This is not investment advice — buy now.",
        "This is not investment advice … buy now.",
        "This is not investment advice - buy now.",
        "This is not investment advice / buy now.",
        "This is not investment advice | buy now.",
        "This is not investment advice & buy now.",
        "This is not advice although buy now.",
        "This is not advice instead buy now.",
        "This is not necessarily advice buy now.",
        "This is not investment advice buy now.",
    ),
)
def test_unrelated_negation_does_not_hide_transaction_language(
    packets: dict[str, dict[str, Any]],
    text: str,
) -> None:
    packet = copy.deepcopy(packets["strong_grounded_liquidity"])
    packet["analyst_questions"][0] = text
    assert prohibited_language_findings(packet)


@pytest.mark.parametrize(
    "text",
    (
        "Do not buy the stock.",
        "The system cannot generate a target price.",
        "Position sizing is prohibited.",
        "Removed the price target from the draft.",
        "The price target was removed.",
    ),
)
def test_directly_negated_or_prohibited_language_is_allowed(
    packets: dict[str, dict[str, Any]],
    text: str,
) -> None:
    packet = copy.deepcopy(packets["strong_grounded_liquidity"])
    packet["analyst_questions"][0] = text
    assert prohibited_language_findings(packet) == []


def test_skeptic_response_rejects_prohibited_language_before_application(
    monkeypatch: pytest.MonkeyPatch,
    packets: dict[str, dict[str, Any]],
    input_records: dict[str, dict[str, Any]],
) -> None:
    stage_one = _as_stage_one(packets["strong_grounded_liquidity"])
    review = _review_envelope(
        stage_one,
        final_status="HOLD_UNSUPPORTED",
        critical_grounding_defect=True,
        corrections=[],
    )
    review["corrections"] = [
        {
            "path": "/system_interpretation/inferences/0/statement",
            "replacement": "Buy now.",
            "reason": "Remove a price target from the draft.",
        }
    ]
    review["review_summary"] = "The packet includes a price target."

    def response(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "message": {"content": json.dumps(review)},
            "total_duration": 1,
            "load_duration": 1,
            "prompt_eval_count": 1,
            "eval_count": 1,
            "eval_duration": 1,
        }

    monkeypatch.setattr(reviewer, "http_json", response)
    returned, metrics, errors = reviewer.skeptic_request(
        source_input=input_records["KHC"],
        packet=stage_one,
        prompt="Fixture skeptic prompt",
        ollama_url="http://127.0.0.1:11434",
    )
    assert returned["review_summary"] == (
        "The packet includes a disallowed transaction language."
    )
    assert returned["corrections"][0]["reason"] == (
        "Remove a disallowed transaction language from the draft."
    )
    assert metrics["narrative_sanitization_count"] == 2
    assert any("buy now" in error.casefold() for error in errors)


def test_malformed_skeptic_response_is_not_coerced_into_valid_pass(
    monkeypatch: pytest.MonkeyPatch,
    packets: dict[str, dict[str, Any]],
    input_records: dict[str, dict[str, Any]],
) -> None:
    stage_one = _as_stage_one(packets["strong_grounded_liquidity"])
    malformed = _review_envelope(
        stage_one,
        final_status="PASS",
        critical_grounding_defect=False,
        corrections=[],
    )
    malformed["critical_objections"] = {"claim": "unsupported"}
    malformed.pop("alternative_explanations")
    malformed["review_summary"] = {"claim": "unsupported"}

    def response(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "message": {"content": json.dumps(malformed)},
            "total_duration": 1,
            "load_duration": 1,
            "prompt_eval_count": 1,
            "eval_count": 1,
            "eval_duration": 1,
        }

    monkeypatch.setattr(reviewer, "http_json", response)
    returned, metrics, errors = reviewer.skeptic_request(
        source_input=input_records["KHC"],
        packet=stage_one,
        prompt="Fixture skeptic prompt",
        ollama_url="http://127.0.0.1:11434",
    )
    assert returned == malformed
    assert isinstance(returned["critical_objections"], dict)
    assert "alternative_explanations" not in returned
    assert isinstance(returned["review_summary"], dict)
    assert metrics["narrative_sanitization_count"] == 0
    assert metrics["identifier_objections_removed"] == 0
    assert len(errors) >= 3


def test_false_evidence_identifier_objection_is_removed_only_when_ids_resolve(
    packets: dict[str, dict[str, Any]],
) -> None:
    stage_one = _as_stage_one(packets["strong_grounded_liquidity"])
    review = _review_envelope(
        stage_one,
        final_status="HOLD_UNSUPPORTED",
        critical_grounding_defect=True,
        corrections=[],
    )
    false_objection = (
        "The evidence ID contains invalid uppercase characters and does not "
        "match the permitted lowercase identifier."
    )
    review["critical_objections"] = [
        false_objection,
        "The hypothesis relies on an unsupported causal premise.",
    ]
    review["review_summary"] = (
        f"{false_objection} The remaining grounding objection is material."
    )
    permitted = set(review["evidence_ids_reviewed"])

    sanitized, language_count, identifier_count = (
        reviewer.sanitize_review_narrative(
            review,
            permitted_evidence_ids=permitted,
        )
    )
    assert language_count == 0
    assert identifier_count == 2
    assert sanitized["critical_objections"] == [
        "The hypothesis relies on an unsupported causal premise."
    ]
    assert sanitized["review_summary"] == (
        "The remaining grounding objection is material."
    )

    unresolved_review = copy.deepcopy(review)
    unresolved_review["evidence_ids_reviewed"] = [
        "evidence-v1:fixture:unresolved"
    ]
    unresolved, _, unresolved_count = reviewer.sanitize_review_narrative(
        unresolved_review,
        permitted_evidence_ids=permitted,
    )
    assert unresolved_count == 0
    assert false_objection in unresolved["critical_objections"]
    assert false_objection in unresolved["review_summary"]

    semantic_review = copy.deepcopy(review)
    semantic_objection = (
        "The evidence ID does not match the hypothesis it is cited to support."
    )
    semantic_review["critical_objections"] = [semantic_objection]
    semantic_review["review_summary"] = semantic_objection
    semantic, _, semantic_count = reviewer.sanitize_review_narrative(
        semantic_review,
        permitted_evidence_ids=permitted,
    )
    assert semantic_count == 0
    assert semantic["critical_objections"] == [semantic_objection]
    assert semantic["review_summary"] == semantic_objection

    no_ids_review = copy.deepcopy(review)
    no_ids_review["evidence_ids_reviewed"] = []
    no_ids, _, no_ids_count = reviewer.sanitize_review_narrative(
        no_ids_review,
        permitted_evidence_ids=permitted,
    )
    assert no_ids_count == 0
    assert false_objection in no_ids["critical_objections"]


def test_evidence_links_and_source_offsets_resolve(
    packets: dict[str, dict[str, Any]],
    input_bundle: dict[str, Any],
) -> None:
    packet = packets["strong_grounded_liquidity"]
    source = _source_for(input_bundle, packet)
    known = collect_evidence_ids(packet)
    referenced = {
        evidence_id
        for mechanism in packet["economic_mechanisms"]
        for evidence_id in mechanism["supporting_evidence_ids"]
    } | {
        evidence_id
        for hypothesis in packet["research_hypotheses"]
        for evidence_id in hypothesis["evidence_ids"]
    }
    assert referenced <= known
    assert packet["source_url"] == source["source_url"]
    assert (
        packet["evidence"]["prior_source_url"]
        == source["prior_filing"]["source_url"]
    )
    assert (
        packet["evidence"]["evidence_offsets"]
        == source["evidence"]["offsets"]
    )
    assert audit_packet(packet, source_input=source).passed


def test_unknown_evidence_reference_fails_closed(
    packets: dict[str, dict[str, Any]],
) -> None:
    packet = copy.deepcopy(packets["strong_grounded_liquidity"])
    packet["economic_mechanisms"][0]["supporting_evidence_ids"] = [
        "evidence-v1:fixture:missing"
    ]
    _refresh_hash(packet)
    assert "UNKNOWN_EVIDENCE_ID" in _finding_codes(packet)


def test_source_mismatch_and_unverified_offsets_are_rejected(
    packets: dict[str, dict[str, Any]],
    input_bundle: dict[str, Any],
) -> None:
    packet = copy.deepcopy(packets["strong_grounded_liquidity"])
    source = _source_for(input_bundle, packet)
    packet["issuer"] = "DIFFERENT ISSUER"
    packet["evidence"]["evidence_offsets_verified"] = False
    _refresh_hash(packet)
    codes = _finding_codes(packet, source_input=source)
    assert "IMMUTABLE_INPUT_MISMATCH" in codes
    assert "SOURCE_OFFSET_INTEGRITY" in codes


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    (
        (("hypothesis", "required_data"), "REQUIRED_DATA"),
        (("hypothesis", "confirmation_conditions"), "CONFIRMATION_CONDITION"),
        (("hypothesis", "falsification_conditions"), "FALSIFICATION_CONDITION"),
        (("hypothesis", "confounders"), "CONFOUNDER"),
        (("scenario", "conditions"), "SCENARIO_COMPLETENESS"),
        (("mechanism", "counterargument"), "MECHANISM_COUNTERARGUMENT"),
    ),
)
def test_completeness_rules_fail_closed(
    mutation: tuple[str, str],
    expected_code: str,
    packets: dict[str, dict[str, Any]],
) -> None:
    packet = copy.deepcopy(packets["strong_grounded_liquidity"])
    group, field_name = mutation
    if group == "hypothesis":
        packet["research_hypotheses"][0][field_name] = []
    elif group == "scenario":
        packet["scenario_analysis"]["bull"][field_name] = []
    else:
        packet["economic_mechanisms"][0][field_name] = ""
    _refresh_hash(packet)
    assert expected_code in _finding_codes(packet)


def test_packet_hash_is_stable_and_content_sensitive(
    packets: dict[str, dict[str, Any]],
) -> None:
    packet = packets["strong_grounded_liquidity"]
    expected = packet["packet_hash"]
    assert expected == compute_packet_hash(packet)

    reordered = dict(reversed(list(copy.deepcopy(packet).items())))
    assert compute_packet_hash(reordered) == expected

    changed = copy.deepcopy(packet)
    changed["confidence"]["hypothesis"] = 0.54
    assert compute_packet_hash(changed) != expected


def test_stale_packet_hash_is_rejected(
    packets: dict[str, dict[str, Any]],
) -> None:
    packet = copy.deepcopy(packets["strong_grounded_liquidity"])
    packet["confidence"]["hypothesis"] = 0.54
    assert "PACKET_HASH" in _finding_codes(packet)


def test_duplicate_and_missing_change_ids_fail_closed(
    packets: dict[str, dict[str, Any]],
) -> None:
    packet_ids = [packet["packet_id"] for packet in packets.values()]
    assert len(packet_ids) == len(set(packet_ids))
    assert_unique_change_ids(
        [
            packets["strong_grounded_liquidity"],
            packets["no_actionable_view"],
        ]
    )
    with pytest.raises(ValueError, match="duplicate packet change_id"):
        assert_unique_change_ids(
            [
                packets["strong_grounded_liquidity"],
                copy.deepcopy(packets["strong_grounded_liquidity"]),
            ]
        )
    duplicate_packet_id = copy.deepcopy(packets["no_actionable_view"])
    duplicate_packet_id["packet_id"] = packets[
        "strong_grounded_liquidity"
    ]["packet_id"]
    with pytest.raises(ValueError, match="duplicate packet_id"):
        assert_unique_change_ids(
            [packets["strong_grounded_liquidity"], duplicate_packet_id]
        )
    with pytest.raises(ValueError, match="missing change_id"):
        assert_unique_change_ids([{"packet_id": "fixture"}])
    with pytest.raises(ValueError, match="missing packet_id"):
        assert_unique_change_ids([{"change_id": "fixture-change"}])


def test_cache_key_and_request_identity_are_deterministic(
    input_records: dict[str, dict[str, Any]],
) -> None:
    source = input_records["KHC"]
    prompt_hash = sha256_text("fixture prompt")
    schema_hash = sha256_file(SCHEMA_PATH)
    first = compute_cache_key(
        stage="generator",
        model_digest=PINNED_MODEL_DIGEST,
        prompt_hash=prompt_hash,
        schema_hash=schema_hash,
        input_hash=source["member_sha256"],
        options={
            **MODEL_OPTIONS,
            "input_policy": generator.GENERATOR_INPUT_POLICY,
        },
    )
    second = compute_cache_key(
        stage="generator",
        model_digest=PINNED_MODEL_DIGEST,
        prompt_hash=prompt_hash,
        schema_hash=schema_hash,
        input_hash=source["member_sha256"],
        options={
            **dict(reversed(list(MODEL_OPTIONS.items()))),
            "input_policy": generator.GENERATOR_INPUT_POLICY,
        },
    )
    different = compute_cache_key(
        stage="generator",
        model_digest=PINNED_MODEL_DIGEST,
        prompt_hash=prompt_hash,
        schema_hash=schema_hash,
        input_hash=source["member_sha256"],
        options={
            **MODEL_OPTIONS,
            "seed": MODEL_OPTIONS["seed"] + 1,
            "input_policy": generator.GENERATOR_INPUT_POLICY,
        },
    )
    assert first == second
    assert len(first) == 64
    assert different != first


def test_generator_builds_identical_offline_requests(
    monkeypatch: pytest.MonkeyPatch,
    input_records: dict[str, dict[str, Any]],
) -> None:
    captured: list[tuple[str, str, dict[str, Any]]] = []

    def fake_http_json(
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: int = 1800,
    ) -> dict[str, Any]:
        assert payload is not None
        captured.append((method, url, copy.deepcopy(payload)))
        return {"message": {"content": "{}"}}

    monkeypatch.setattr(generator, "http_json", fake_http_json)
    source = input_records["KHC"]
    schema = load_json(SCHEMA_PATH)
    kwargs = {
        "source_input": source,
        "schema": schema,
        "prompt": "Gate I2 deterministic prompt",
        "ollama_url": "http://127.0.0.1:11434",
    }
    first, _metrics_one = generator.model_request(**kwargs)
    second, _metrics_two = generator.model_request(**kwargs)
    assert first == second == {}
    assert len(captured) == 2
    assert canonical_json(captured[0]) == canonical_json(captured[1])
    method, url, payload = captured[0]
    assert method == "POST"
    assert url.startswith("http://127.0.0.1:11434/")
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"] == MODEL_OPTIONS
    assert source["member_sha256"] not in payload["messages"][1]["content"]


def test_model_input_projection_is_a_strict_formation_time_allowlist(
    input_records: dict[str, dict[str, Any]],
) -> None:
    projected = generator.model_input_projection(input_records["KHC"])
    serialized = canonical_json(projected)
    assert set(projected["evidence"]) == {
        "evidence_ids",
        "prior_excerpt",
        "current_excerpt",
        "added_text",
        "removed_text",
        "offsets",
        "related_prior_8k",
        "related_prior_news",
    }
    assert set(projected["frozen_classification"]) == {
        "category",
        "direction",
        "materiality",
        "confidence",
    }
    for prohibited in (
        "outcome",
        "changed_numbers",
        "new_entities",
        "selection",
        "provenance",
        "alignment_similarity",
        "why_it_matters",
    ):
        assert prohibited not in serialized


@pytest.mark.parametrize(
    "url",
    (
        "https://127.0.0.1:11434",
        "http://ollama.example.com:11434",
        "http://127.0.0.1@ollama.example.com:11434",
        "http://127.0.0.1:11434/api",
    ),
)
def test_remote_or_ambiguous_ollama_urls_are_rejected_before_network(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
) -> None:
    network_called = False

    def fail_if_called(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal network_called
        network_called = True
        raise AssertionError("network should not be called")

    monkeypatch.setattr(generator, "http_json", fail_if_called)
    with pytest.raises(generator.GenerationError, match="loopback"):
        generator.verify_local_model(url, "test-model", "sha256:0")
    assert network_called is False


@pytest.mark.parametrize(
    "url",
    (
        "http://127.0.0.1:11434",
        "http://localhost:11434/",
        "http://[::1]:11434",
    ),
)
def test_supported_loopback_ollama_urls_pass_endpoint_policy(url: str) -> None:
    generator.require_loopback_ollama_url(url)


def test_public_and_archival_packet_trees_are_byte_identical() -> None:
    public_dir = ROOT / "demo" / "data" / "research_idea_packets" / "v1"
    archive_dir = ROOT / "data" / "research_idea_packets" / "v1"
    public_files = sorted(path.name for path in public_dir.glob("*.json"))
    archive_files = sorted(path.name for path in archive_dir.glob("*.json"))
    assert public_files == archive_files
    assert public_files == [
        "279e7d4e407851a19548.json",
        "2f22dc2216c9df31d377.json",
        "339fae2941721ee094b0.json",
        "412b08746bb0ed5a7745.json",
        "4784f62ad001b2a12af4.json",
        "8d4598f4ea16f15c7048.json",
        "8f5336b55618ffe68e8a.json",
        "dbe75bc24f2888f4166a.json",
        "index.json",
    ]
    for filename in public_files:
        assert (public_dir / filename).read_bytes() == (
            archive_dir / filename
        ).read_bytes()


def test_accepted_cache_hit_never_regenerates_or_overwrites(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    packets: dict[str, dict[str, Any]],
    input_records: dict[str, dict[str, Any]],
) -> None:
    source = input_records["KHC"]
    packet = packets["strong_grounded_liquidity"]
    prompt = "Gate I2 cache fixture prompt"
    prompt_hash = sha256_text(prompt)
    schema_hash = sha256_file(SCHEMA_PATH)
    schema = load_json(SCHEMA_PATH)
    cache_dir = tmp_path / "cache"
    staging_dir = tmp_path / "staging"
    monkeypatch.setattr(generator, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(generator, "STAGING_DIR", staging_dir)

    cache_key = compute_cache_key(
        stage="generator",
        model_digest=PINNED_MODEL_DIGEST,
        prompt_hash=prompt_hash,
        schema_hash=schema_hash,
        input_hash=source["member_sha256"],
        options={
            **MODEL_OPTIONS,
            "input_policy": generator.GENERATOR_INPUT_POLICY,
        },
    )
    cache_path = cache_dir / f"{cache_key}.json"
    write_json(
        cache_path,
        {
            "cache_version": "1.0",
            "cache_key": cache_key,
            "repair_attempted": False,
            "model_metrics": {},
            "packet": packet,
        },
    )
    original_cache_bytes = cache_path.read_bytes()

    def fail_if_called(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("accepted cache hit attempted model generation")

    monkeypatch.setattr(generator, "model_request", fail_if_called)
    returned, result = generator.generate_one(
        source,
        schema=schema,
        prompt=prompt,
        prompt_hash=prompt_hash,
        schema_hash=schema_hash,
        ollama_url="http://127.0.0.1:11434",
    )
    assert returned == packet
    assert result["cache"] == "HIT"
    assert cache_path.read_bytes() == original_cache_bytes
    assert load_json(
        staging_dir / f"{source['change_id']}.generator.json"
    ) == packet
    assert (
        packet["generation_metadata"]["accepted_packet_regeneration_policy"]
        == "NEVER_SILENTLY_REGENERATE"
    )


def test_reviewer_corrections_are_deterministic_and_non_mutating(
    packets: dict[str, dict[str, Any]],
) -> None:
    packet = packets["strong_grounded_liquidity"]
    original = copy.deepcopy(packet)
    corrections = [
        {
            "path": "/system_interpretation/inferences/0/statement",
            "replacement": (
                "A future waiver need could constrain funding access; the "
                "evidence does not establish that this has occurred."
            ),
            "reason": "Reduce causal confidence.",
        },
        {
            "path": "/confidence/hypothesis",
            "replacement": 0.45,
            "reason": "Reflect the missing covenant headroom data.",
        },
    ]
    first, first_applied = apply_reviewer_corrections(packet, corrections)
    second, second_applied = apply_reviewer_corrections(packet, corrections)
    assert canonical_json(first) == canonical_json(second)
    assert first_applied == second_applied
    assert packet == original
    assert first["confidence"]["hypothesis"] == 0.45
    assert first_applied[0] == {
        "path": "/system_interpretation/inferences/0/statement",
        "reason": "Reduce causal confidence.",
    }


def test_reviewer_cannot_edit_frozen_evidence(
    packets: dict[str, dict[str, Any]],
) -> None:
    packet = packets["strong_grounded_liquidity"]
    with pytest.raises(ValueError, match="immutable field"):
        apply_reviewer_corrections(
            packet,
            [
                {
                    "path": "/evidence/current_excerpt",
                    "replacement": "Altered evidence",
                    "reason": "Invalid fixture edit",
                }
            ],
        )


def test_hold_review_can_delete_all_draft_hypotheses_without_false_claims(
    packets: dict[str, dict[str, Any]],
    input_records: dict[str, dict[str, Any]],
) -> None:
    stage_one = _as_stage_one(packets["strong_grounded_liquidity"])
    review = _review_envelope(
        stage_one,
        final_status="HOLD_UNSUPPORTED",
        critical_grounding_defect=True,
        corrections=[
            {
                "path": "/research_hypotheses",
                "replacement": [],
                "reason": "Remove unsupported hypotheses.",
            }
        ],
    )
    packet = reviewer.apply_review(
        stage_one,
        input_records["KHC"],
        review,
        schema=load_json(SCHEMA_PATH),
        schema_hash=sha256_file(SCHEMA_PATH),
        skeptic_prompt_hash="1" * 64,
        cache_key="2" * 64,
        run_metadata={
            "attempt": 1,
            "started_at": "2026-07-29T00:00:00Z",
            "completed_at": "2026-07-29T00:00:01Z",
            "request_sha256": "3" * 64,
            "response_sha256": "4" * 64,
        },
        cache_hit=False,
    )
    assert packet["packet_status"] == "HOLD_UNSUPPORTED"
    assert packet["research_hypotheses"] == []
    assert packet["skeptical_review"]["unsupported_claims_removed"] == [
        (
            "Applied skeptic correction at /research_hypotheses: "
            "Remove unsupported hypotheses."
        )
    ]
    assert not any(
        "correction rejected" in objection.casefold()
        for objection in packet["skeptical_review"]["critical_objections"]
    )


def test_correction_ledger_excludes_noops_and_withholding_overwrites(
    packets: dict[str, dict[str, Any]],
    input_records: dict[str, dict[str, Any]],
) -> None:
    stage_one = _as_stage_one(packets["strong_grounded_liquidity"])
    revised_inference = (
        "The disclosure supports a bounded funding-access question, not a "
        "claim that a constraint has already occurred."
    )
    review = _review_envelope(
        stage_one,
        final_status="HOLD_UNSUPPORTED",
        critical_grounding_defect=True,
        corrections=[
            {
                "path": "/confidence/hypothesis",
                "replacement": stage_one["confidence"]["hypothesis"],
                "reason": "No-op fixture correction.",
            },
            {
                "path": (
                    "/system_interpretation/inferences/0/statement"
                ),
                "replacement": revised_inference,
                "reason": "Narrow the inference to the cited evidence.",
            },
            {
                "path": (
                    "/illustrative_trade_hypothesis/candidate_view"
                ),
                "replacement": "no actionable view",
                "reason": "Remove the directional expression.",
            },
        ],
    )
    packet = reviewer.apply_review(
        stage_one,
        input_records["KHC"],
        review,
        schema=load_json(SCHEMA_PATH),
        schema_hash=sha256_file(SCHEMA_PATH),
        skeptic_prompt_hash="1" * 64,
        cache_key="2" * 64,
        run_metadata={
            "attempt": 1,
            "started_at": "2026-07-29T00:00:00Z",
            "completed_at": "2026-07-29T00:00:01Z",
            "request_sha256": "3" * 64,
            "response_sha256": "4" * 64,
        },
        cache_hit=False,
    )
    assert packet["system_interpretation"]["inferences"][0][
        "statement"
    ] == revised_inference
    assert packet["illustrative_trade_hypothesis"]["candidate_view"] == (
        "insufficient evidence"
    )
    assert packet["skeptical_review"]["unsupported_claims_removed"] == [
        (
            "Applied skeptic correction at "
            "/system_interpretation/inferences/0/statement: "
            "Narrow the inference to the cited evidence."
        )
    ]


def test_rejected_required_correction_forces_publishable_review_to_hold(
    packets: dict[str, dict[str, Any]],
    input_records: dict[str, dict[str, Any]],
) -> None:
    stage_one = _as_stage_one(packets["strong_grounded_liquidity"])
    review = _review_envelope(
        stage_one,
        final_status="PASS_WITH_EDITS",
        critical_grounding_defect=False,
        corrections=[
            {
                "path": "/frozen_classification/category",
                "replacement": "Altered frozen category",
                "reason": "Invalid required edit.",
            }
        ],
    )
    packet = reviewer.apply_review(
        stage_one,
        input_records["KHC"],
        review,
        schema=load_json(SCHEMA_PATH),
        schema_hash=sha256_file(SCHEMA_PATH),
        skeptic_prompt_hash="1" * 64,
        cache_key="2" * 64,
        run_metadata={
            "attempt": 1,
            "started_at": "2026-07-29T00:00:00Z",
            "completed_at": "2026-07-29T00:00:01Z",
            "request_sha256": "3" * 64,
            "response_sha256": "4" * 64,
        },
        cache_hit=False,
    )
    assert packet["packet_status"] == "HOLD_UNSUPPORTED"
    assert packet["skeptical_review"]["final_review_status"] == (
        "HOLD_UNSUPPORTED"
    )
    assert packet["skeptical_review"]["critical_grounding_defect"] is True
    assert packet["skeptical_review"]["unsupported_claims_removed"] == []
    assert any(
        "correction rejected" in objection.casefold()
        for objection in packet["skeptical_review"]["critical_objections"]
    )
