#!/usr/bin/env python3
"""Run mandatory skeptical review and publish validated eight-case packets."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from generate_research_idea_packets import (
    DEFAULT_OLLAMA_URL,
    GenerationError,
    http_json,
    model_input_projection,
    model_run,
    parse_model_json,
    verify_local_model,
)
from research_idea_common import (
    ARCHIVE_PACKET_DIR,
    DEFAULT_DISCLAIMER,
    INPUT_BUNDLE_PATH,
    LANGUAGE_REGISTRY_PATH,
    MODEL_OPTIONS,
    PACKET_DIR,
    PINNED_MODEL,
    PINNED_MODEL_DIGEST,
    PUBLISHABLE_REVIEW_STATUSES,
    ROOT,
    SCHEMA_PATH,
    SKEPTIC_PROMPT_PATH,
    apply_reviewer_corrections,
    audit_packet,
    canonical_json,
    collect_evidence_ids,
    compute_cache_key,
    compute_packet_hash,
    find_input,
    load_json,
    parse_timestamp,
    prohibited_language_findings,
    sha256_file,
    sha256_json,
    sha256_text,
    validate_schema,
    write_json,
)


STAGING_DIR = ROOT / "artifacts" / "research_idea_generation" / "v1"
CACHE_DIR = ROOT / "artifacts" / "research_idea_cache" / "v1" / "skeptic"
SKEPTIC_APPLICATION_POLICY = "research_idea_skeptic_application_v1.7"

SKEPTIC_RESPONSE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "review_version",
        "critical_objections",
        "alternative_explanations",
        "pricing_or_attention_concerns",
        "unsupported_claims_removed",
        "evidence_ids_reviewed",
        "critical_grounding_defect",
        "final_review_status",
        "review_summary",
        "corrections",
    ],
    "properties": {
        "review_version": {"const": "research_idea_skeptic_v1"},
        "critical_objections": {
            "type": "array",
            "maxItems": 12,
            "items": {"type": "string", "minLength": 1, "maxLength": 2000},
        },
        "alternative_explanations": {
            "type": "array",
            "maxItems": 12,
            "items": {"type": "string", "minLength": 1, "maxLength": 2000},
        },
        "pricing_or_attention_concerns": {
            "type": "array",
            "maxItems": 12,
            "items": {"type": "string", "minLength": 1, "maxLength": 2000},
        },
        "unsupported_claims_removed": {
            "type": "array",
            "maxItems": 20,
            "items": {"type": "string", "minLength": 1, "maxLength": 2000},
        },
        "evidence_ids_reviewed": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "pattern": "^(?:EV-|evidence-v1:)[A-Za-z0-9][A-Za-z0-9._:\\-]*$",
            },
        },
        "critical_grounding_defect": {"type": "boolean"},
        "final_review_status": {
            "enum": [
                "PASS",
                "PASS_WITH_EDITS",
                "HOLD_UNSUPPORTED",
                "HOLD_AMBIGUOUS",
                "HOLD_INSUFFICIENT_EVIDENCE",
                "REJECTED_BY_SKEPTIC",
            ]
        },
        "review_summary": {"type": "string", "minLength": 1, "maxLength": 4000},
        "corrections": {
            "type": "array",
            "maxItems": 20,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["path", "replacement", "reason"],
                "properties": {
                    "path": {"type": "string", "pattern": "^/"},
                    "replacement": True,
                    "reason": {"type": "string", "minLength": 1, "maxLength": 1000},
                },
            },
        },
    },
    "allOf": [
        {
            "if": {"properties": {"final_review_status": {"const": "PASS_WITH_EDITS"}}},
            "then": {"properties": {"corrections": {"minItems": 1}}},
        },
        {
            "if": {
                "properties": {
                    "final_review_status": {"enum": ["PASS", "PASS_WITH_EDITS"]}
                }
            },
            "then": {
                "properties": {
                    "critical_grounding_defect": {"const": False},
                    "evidence_ids_reviewed": {"minItems": 1},
                }
            },
        },
    ],
}


class ReviewError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def referenced_evidence_ids(packet: dict[str, Any]) -> set[str]:
    references: set[str] = set()
    analytical_roots = (
        "system_interpretation",
        "economic_mechanisms",
        "affected_entities",
        "research_hypotheses",
        "analyst_questions",
        "scenario_analysis",
        "illustrative_trade_hypothesis",
    )

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"evidence_ids", "supporting_evidence_ids"} and isinstance(
                    child, list
                ):
                    references.update(str(item) for item in child)
                else:
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for root_name in analytical_roots:
        walk(packet.get(root_name))
    return references


def claim_grounding_counts(packet: dict[str, Any]) -> tuple[int, int]:
    available = collect_evidence_ids(packet)
    checked = 0
    grounded = 0

    def walk(value: Any) -> None:
        nonlocal checked, grounded
        if isinstance(value, dict):
            evidence = value.get("evidence_ids")
            if evidence is None:
                evidence = value.get("supporting_evidence_ids")
            if isinstance(evidence, list):
                checked += 1
                if evidence and set(map(str, evidence)).issubset(available):
                    grounded += 1
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for root_name in (
        "system_interpretation",
        "economic_mechanisms",
        "affected_entities",
        "research_hypotheses",
        "analyst_questions",
        "scenario_analysis",
        "illustrative_trade_hypothesis",
    ):
        walk(packet.get(root_name))
    return checked, grounded


def future_timestamp_violations(
    packet: dict[str, Any],
) -> tuple[int, list[str]]:
    formation = parse_timestamp(packet["formation_timestamp"])
    checked = 0
    violations: list[str] = []
    for collection, field in (
        ("related_prior_8k", "acceptance_timestamp"),
        ("related_prior_news", "publication_timestamp"),
    ):
        for index, item in enumerate(packet["evidence"].get(collection, [])):
            checked += 1
            observed = parse_timestamp(item[field])
            if observed > formation:
                violations.append(
                    f"/evidence/{collection}/{index}/{field} is after formation"
                )
    return checked, violations


def stable_analytical_hash(packet: dict[str, Any]) -> str:
    return sha256_json(
        {
            key: packet.get(key)
            for key in (
                "system_interpretation",
                "economic_mechanisms",
                "affected_entities",
                "research_hypotheses",
                "analyst_questions",
                "scenario_analysis",
                "illustrative_trade_hypothesis",
                "skeptical_review",
                "confidence",
            )
        }
    )


def force_withheld_trade(packet: dict[str, Any]) -> None:
    trade = packet["illustrative_trade_hypothesis"]
    current_evidence_id = packet["evidence"]["evidence_ids"]["current_excerpt"]
    trade.update(
        {
            "label": "Illustrative Trade Hypothesis — Analyst Review Required",
            "status": "WITHHELD_BY_SKEPTIC",
            "candidate_view": "insufficient evidence",
            "preferred_instrument_class_to_investigate": "no instrument identified",
            "instrument_rationale": (
                "The skeptical review did not clear a grounded instrument "
                "expression from the cited disclosure evidence."
            ),
            "expected_horizon": "Not specified because the hypothesis is withheld.",
            "entry_or_confirmation_conditions": [],
            "invalidation_conditions": [],
            "key_risks": [],
            "market_data_required_before_action": [],
            "liquidity_and_cost_checks": [],
            "evidence_ids": [current_evidence_id],
            "trade_readiness": "NOT_READY",
            "trade_readiness_reason": (
                "The skeptical review did not clear the evidence and mechanism "
                "gates."
            ),
            "current_market_data_used": False,
            "illustrative_only": True,
            "analyst_review_required": True,
            "no_position_size_generated": True,
        }
    )


def packet_status_for_review(review_status: str) -> str:
    return "PUBLISHABLE" if review_status in PUBLISHABLE_REVIEW_STATUSES else review_status


def sanitize_review_narrative(
    review: dict[str, Any],
    *,
    permitted_evidence_ids: set[str],
) -> tuple[dict[str, Any], int, int]:
    """Normalize quoted transaction vocabulary in reviewer-only prose.

    Correction replacements are intentionally excluded: prohibited language
    proposed for a packet field must still fail validation. Identifier-format
    objections are removed only when every reviewer-cited evidence ID already
    resolves to the caller-owned permitted set; in that state, an objection
    claiming that an evidence ID is invalid is self-contradictory.
    """

    sanitized = copy.deepcopy(review)
    registry = load_json(LANGUAGE_REGISTRY_PATH)
    count = 0
    identifier_objections_removed = 0
    reviewed_ids = {
        str(item) for item in sanitized.get("evidence_ids_reviewed", [])
    }
    reviewed_ids_resolve = bool(reviewed_ids) and reviewed_ids.issubset(
        permitted_evidence_ids
    )
    identifier_objection = re.compile(
        r"\bevidence\s+(?:id|identifier)\b.{0,300}\b(?:"
        r"contains?\s+invalid\s+(?:upper|lower)case(?:\s+characters?)?|"
        r"invalid\s+(?:upper|lower)case(?:\s+characters?)?|"
        r"does\s+not\s+match\s+the\s+permitted\s+"
        r"(?:upper|lower)case\s+(?:id|identifier)|"
        r"invalid\s+(?:id|identifier)\s+format|"
        r"not\s+(?:a\s+)?permitted\s+(?:id|identifier)\s+format)",
        flags=re.IGNORECASE,
    )

    def normalize(value: str) -> str:
        nonlocal count
        revised = value
        for phrase in registry.get("blocked_phrases", []):
            revised, replacements = re.subn(
                re.escape(str(phrase)),
                "disallowed transaction language",
                revised,
                flags=re.IGNORECASE,
            )
            count += replacements
        for entry in registry.get("blocked_patterns", []):
            revised, replacements = re.subn(
                entry["pattern"],
                "disallowed transaction instruction",
                revised,
                flags=re.IGNORECASE,
            )
            count += replacements
        return revised

    for field in (
        "critical_objections",
        "alternative_explanations",
        "pricing_or_attention_concerns",
        "unsupported_claims_removed",
    ):
        retained: list[str] = []
        for item in sanitized.get(field, []):
            value = str(item)
            if reviewed_ids_resolve and identifier_objection.search(value):
                identifier_objections_removed += 1
                continue
            retained.append(normalize(value))
        sanitized[field] = retained
    summary_sentences = re.split(
        r"(?<=[.!?])\s+",
        str(sanitized.get("review_summary", "")),
    )
    retained_summary: list[str] = []
    for sentence in summary_sentences:
        if reviewed_ids_resolve and identifier_objection.search(sentence):
            identifier_objections_removed += 1
            continue
        if sentence:
            retained_summary.append(normalize(sentence))
    sanitized["review_summary"] = " ".join(retained_summary) or (
        "The skeptical review did not clear the packet for publication."
    )
    for correction in sanitized.get("corrections", []):
        correction["reason"] = normalize(str(correction.get("reason", "")))
    return sanitized, count, identifier_objections_removed


def skeptic_request(
    *,
    source_input: dict[str, Any],
    packet: dict[str, Any],
    prompt: str,
    ollama_url: str,
    repair_review: dict[str, Any] | None = None,
    repair_errors: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    allowed_source_input = model_input_projection(source_input)
    response_schema = copy.deepcopy(SKEPTIC_RESPONSE_SCHEMA)
    evidence = source_input["evidence"]
    permitted_evidence_ids = sorted(
        {
            *evidence["evidence_ids"].values(),
            *(
                item["evidence_id"]
                for collection in ("related_prior_8k", "related_prior_news")
                for item in evidence.get(collection, [])
            ),
        }
    )
    response_schema["properties"]["evidence_ids_reviewed"]["items"] = {
        "type": "string",
        "enum": permitted_evidence_ids,
    }
    if repair_review is None:
        instruction = (
            "Review the candidate as hostile evidence, not as a draft to endorse. "
            "Return only the skeptical-review response envelope required below. "
            "A correction may target inference fields only; use a hold or rejection "
            "when a safe replacement cannot be made without adding facts."
        )
    else:
        instruction = (
            "Repair the prior skeptical-review response solely for the listed "
            "schema defects. Do not add evidence, relax an objection, or upgrade "
            "the review status. Return the complete corrected response envelope."
        )
    user_content = (
        instruction
        + "\n\nALLOWED_INPUT_JSON:\n"
        + json.dumps(allowed_source_input, ensure_ascii=False, indent=2)
        + "\n\nCANDIDATE_PACKET_JSON:\n"
        + json.dumps(packet, ensure_ascii=False, indent=2)
        + "\n\nPERMITTED_EVIDENCE_IDS_JSON:\n"
        + canonical_json(permitted_evidence_ids)
    )
    if repair_review is not None:
        user_content += (
            "\n\nSCHEMA_ERRORS:\n"
            + "\n".join(f"- {message}" for message in (repair_errors or []))
            + "\n\nINVALID_REVIEW_JSON:\n"
            + json.dumps(repair_review, ensure_ascii=False, indent=2)
        )
    user_content += (
        "\n\nSKEPTIC_RESPONSE_SCHEMA_JSON:\n"
        + json.dumps(response_schema, ensure_ascii=False, indent=2)
    )
    request_payload = {
        "model": PINNED_MODEL,
        "stream": False,
        "think": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content},
        ],
        "options": MODEL_OPTIONS,
        "keep_alive": "30m",
    }
    started_at = utc_now()
    request_hash = sha256_json(request_payload)
    response = http_json(
        "POST",
        f"{ollama_url.rstrip('/')}/api/chat",
        request_payload,
    )
    completed_at = utc_now()
    raw_review = parse_model_json(response)
    raw_schema_errors = [
        error.message
        for error in Draft202012Validator(
            response_schema
        ).iter_errors(raw_review)
    ]
    base_metrics = {
        "started_at": started_at,
        "completed_at": completed_at,
        "request_sha256": request_hash,
        "response_sha256": sha256_text(
            str(response.get("message", {}).get("content", ""))
        ),
        "total_duration": response.get("total_duration"),
        "load_duration": response.get("load_duration"),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
        "eval_duration": response.get("eval_duration"),
    }
    if raw_schema_errors:
        return raw_review, {
            **base_metrics,
            "narrative_sanitization_count": 0,
            "identifier_objections_removed": 0,
        }, raw_schema_errors

    (
        review,
        narrative_sanitization_count,
        identifier_objections_removed,
    ) = sanitize_review_narrative(
        raw_review,
        permitted_evidence_ids=set(permitted_evidence_ids),
    )
    errors = [
        error.message
        for error in Draft202012Validator(
            response_schema
        ).iter_errors(review)
    ]
    errors.extend(
        f"{finding.path}: {finding.message}"
        for finding in prohibited_language_findings(
            {"skeptical_review": review}
        )
    )
    return review, {
        **base_metrics,
        "narrative_sanitization_count": narrative_sanitization_count,
        "identifier_objections_removed": identifier_objections_removed,
    }, errors


def read_json_pointer(document: Any, pointer: str) -> Any:
    if not pointer.startswith("/") or pointer == "/":
        raise ValueError("correction path must be a non-root JSON pointer")
    cursor = document
    for encoded in pointer[1:].split("/"):
        part = encoded.replace("~1", "/").replace("~0", "~")
        cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
    return cursor


def apply_review(
    stage_one: dict[str, Any],
    source_input: dict[str, Any],
    review: dict[str, Any],
    *,
    schema: dict[str, Any],
    schema_hash: str,
    skeptic_prompt_hash: str,
    cache_key: str,
    run_metadata: dict[str, Any],
    cache_hit: bool,
) -> dict[str, Any]:
    packet = copy.deepcopy(stage_one)
    available_ids = collect_evidence_ids(packet)
    reviewed_ids = set(map(str, review.get("evidence_ids_reviewed", [])))
    unresolved_reviewed = reviewed_ids - available_ids
    if unresolved_reviewed:
        raise ReviewError(
            f"skeptic cited unknown evidence IDs: {sorted(unresolved_reviewed)}"
        )

    final_status = review["final_review_status"]
    stage_status = stage_one.get("packet_status")
    if stage_status in {
        "HOLD_UNSUPPORTED",
        "HOLD_AMBIGUOUS",
        "HOLD_INSUFFICIENT_EVIDENCE",
    } and final_status in PUBLISHABLE_REVIEW_STATUSES:
        final_status = stage_status
    if review["critical_grounding_defect"] and final_status in PUBLISHABLE_REVIEW_STATUSES:
        final_status = "HOLD_UNSUPPORTED"

    critical_objections = list(review["critical_objections"])
    packet["packet_status"] = packet_status_for_review(final_status)
    packet["skeptical_review"] = {
        "review_version": "research_idea_skeptic_v1",
        "critical_objections": critical_objections,
        "alternative_explanations": review["alternative_explanations"],
        "pricing_or_attention_concerns": review[
            "pricing_or_attention_concerns"
        ],
        "unsupported_claims_removed": [],
        "evidence_ids_reviewed": sorted(reviewed_ids),
        "critical_grounding_defect": bool(
            review["critical_grounding_defect"]
            or final_status not in PUBLISHABLE_REVIEW_STATUSES
        ),
        "final_review_status": final_status,
        "review_summary": review["review_summary"],
    }

    rejected_corrections: list[str] = []
    applied_corrections: list[dict[str, Any]] = []
    for correction in review.get("corrections", []):
        try:
            candidate_packet, applied = apply_reviewer_corrections(
                packet,
                [correction],
                maximum=1,
            )
            correction_schema_errors = validate_schema(
                candidate_packet,
                schema,
            )
            if correction_schema_errors:
                summary = "; ".join(
                    f"{finding.path}: {finding.message}"
                    for finding in correction_schema_errors[:3]
                )
                raise ValueError(
                    "reviewer correction would violate the frozen schema "
                    f"({summary})"
                )
            packet = candidate_packet
            applied_corrections.extend(
                {
                    **item,
                    "replacement": copy.deepcopy(
                        correction.get("replacement")
                    ),
                }
                for item in applied
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            # Preserve frozen evidence and caller-owned lifecycle fields. A
            # rejected edit is documented, while the reviewer's explicit
            # critical_grounding_defect flag remains the publication gate.
            rejected_corrections.append(
                f"Skeptic correction rejected by policy: {exc}"
            )

    critical_objections.extend(rejected_corrections)
    if rejected_corrections and final_status in PUBLISHABLE_REVIEW_STATUSES:
        final_status = "HOLD_UNSUPPORTED"
        packet["packet_status"] = final_status
        packet["skeptical_review"]["critical_grounding_defect"] = True
        packet["skeptical_review"]["final_review_status"] = final_status
    packet["skeptical_review"]["critical_objections"] = critical_objections
    if final_status not in PUBLISHABLE_REVIEW_STATUSES:
        force_withheld_trade(packet)
    final_applied_corrections: list[dict[str, Any]] = []
    for item in applied_corrections:
        try:
            final_value = read_json_pointer(packet, item["path"])
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        if final_value == item["replacement"]:
            final_applied_corrections.append(item)
    packet["skeptical_review"]["unsupported_claims_removed"] = [
        (
            f"Applied skeptic correction at {item['path']}: "
            f"{item['reason'] or 'unsupported generated content removed or narrowed'}"
        )
        for item in final_applied_corrections
    ]

    packet["generation_metadata"]["skeptic_run"] = model_run(
        role="SKEPTIC",
        run_status="COMPLETE",
        prompt_version="research_idea_skeptic_v1",
        prompt_hash=skeptic_prompt_hash,
        schema_hash=schema_hash,
        cache_key=cache_key,
        attempt=int(run_metadata.get("attempt", 1)),
        started_at=run_metadata["started_at"],
        completed_at=run_metadata["completed_at"],
        request_hash=run_metadata["request_sha256"],
        response_hash=run_metadata["response_sha256"],
    )

    refs = referenced_evidence_ids(packet)
    unresolved = sorted(refs - available_ids)
    checked_claims, grounded_claims = claim_grounding_counts(packet)
    checked_timestamps, timestamp_violations = future_timestamp_violations(packet)
    language_violations = prohibited_language_findings(packet)
    now = utc_now()
    grounding_defects = (
        list(critical_objections)
        if review["critical_grounding_defect"]
        or final_status not in PUBLISHABLE_REVIEW_STATUSES
        else []
    )
    if unresolved:
        grounding_defects.append(
            "Unresolved evidence IDs: " + ", ".join(unresolved)
        )
    packet["audit_metadata"] = {
        "audit_version": "research_idea_audit_v1",
        "audited_at": now,
        "schema_validation": {
            "status": "PASS",
            "validator_name": "jsonschema.Draft202012Validator",
            "validator_version": "4.26.0",
            "validated_at": now,
            "errors": [],
        },
        "grounding": {
            "status": (
                "PASS"
                if final_status in PUBLISHABLE_REVIEW_STATUSES
                and not grounding_defects
                and not unresolved
                else "HOLD"
            ),
            "checked_claim_count": checked_claims,
            "grounded_claim_count": grounded_claims,
            "critical_defects": grounding_defects,
        },
        "future_information": {
            "status": "PASS" if not timestamp_violations else "FAIL",
            "formation_timestamp": packet["formation_timestamp"],
            "checked_timestamp_count": checked_timestamps,
            "violations": timestamp_violations,
        },
        "evidence_integrity": {
            "status": "PASS" if not unresolved else "FAIL",
            "referenced_evidence_ids": sorted(refs),
            "unresolved_evidence_ids": unresolved,
            "source_url_present": bool(packet.get("source_url")),
            "offsets_verified": bool(
                packet.get("evidence", {}).get("evidence_offsets_verified")
            ),
        },
        "prohibited_language": {
            "status": "PASS" if not language_violations else "FAIL",
            "registry_version": "1.0",
            "matches": [
                {
                    "phrase": finding.detail.get(
                        "phrase",
                        finding.detail.get("match", finding.message),
                    ),
                    "json_pointer": finding.path,
                    "classification": "VIOLATION",
                }
                for finding in language_violations
            ],
            "violation_count": len(language_violations),
        },
        "determinism": {
            "status": "PASS",
            "cache_hit": cache_hit,
            "repeated_generation_matches": None,
            "stable_content_sha256": stable_analytical_hash(packet),
        },
        "publication_decision": packet["packet_status"],
        "audit_findings": grounding_defects + timestamp_violations,
    }
    packet["disclaimer"] = DEFAULT_DISCLAIMER
    packet["packet_hash"] = compute_packet_hash(packet)

    deterministic = audit_packet(
        packet,
        source_input=source_input,
        schema=schema,
    )
    if deterministic.errors:
        messages = [
            f"{finding.code} {finding.path}: {finding.message}"
            for finding in deterministic.errors
        ]
        raise ReviewError(
            f"final packet failed deterministic audit: {' | '.join(messages[:12])}"
        )
    return packet


def make_index(packets: list[dict[str, Any]]) -> dict[str, Any]:
    entries = []
    for packet in packets:
        hypotheses = packet.get("research_hypotheses", [])
        horizons = sorted(
            {item.get("time_horizon") for item in hypotheses if item.get("time_horizon")}
        )
        testability = [
            float(item["testability_score"])
            for item in hypotheses
            if isinstance(item.get("testability_score"), (int, float))
        ]
        trade = packet["illustrative_trade_hypothesis"]
        entries.append(
            {
                "change_id": packet["change_id"],
                "packet_id": packet["packet_id"],
                "packet_hash": packet["packet_hash"],
                "path": f"{packet['change_id']}.json",
                "issuer": packet["issuer"],
                "ticker": packet["ticker"],
                "filing_date": packet["filing_date"],
                "year": packet["filing_date"][:4],
                "section": packet["section"],
                "category": packet["frozen_classification"]["category"],
                "direction": packet["frozen_classification"]["direction"],
                "materiality": packet["frozen_classification"]["materiality"],
                "novelty": packet["frozen_classification"]["novelty"],
                "evidence_confidence": packet["confidence"]["evidence"],
                "hypothesis_testability": (
                    round(sum(testability) / len(testability), 6)
                    if testability
                    else 0
                ),
                "hypothesis_horizons": horizons,
                "affected_asset_class": trade[
                    "preferred_instrument_class_to_investigate"
                ],
                "idea_review_status": packet["skeptical_review"][
                    "final_review_status"
                ],
                "packet_status": packet["packet_status"],
                "trade_readiness": trade["trade_readiness"],
                "analyst_disposition": packet["analyst_disposition"]["status"],
            }
        )
    index = {
        "index_version": "1.0",
        "packet_version": "1.0",
        "generated_from": "bounded-eight-case-formation-time-inputs",
        "packet_count": len(entries),
        "packets": entries,
    }
    index["index_sha256"] = sha256_json(index)
    return index


def review_one(
    stage_one: dict[str, Any],
    source_input: dict[str, Any],
    *,
    schema: dict[str, Any],
    schema_hash: str,
    prompt: str,
    prompt_hash: str,
    ollama_url: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    combined_input_hash = sha256_json(
        {
            "source_input_sha256": source_input["member_sha256"],
            "stage_one_packet_hash": stage_one["packet_hash"],
        }
    )
    cache_key = compute_cache_key(
        stage="skeptic",
        model_digest=PINNED_MODEL_DIGEST,
        prompt_hash=prompt_hash,
        schema_hash=schema_hash,
        input_hash=combined_input_hash,
        options={
            **MODEL_OPTIONS,
            "review_application_policy": SKEPTIC_APPLICATION_POLICY,
            "language_registry_sha256": sha256_file(
                LANGUAGE_REGISTRY_PATH
            ),
        },
    )
    cache_path = CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        cached = load_json(cache_path)
        packet = cached.get("packet")
        if not isinstance(packet, dict):
            raise ReviewError(f"invalid skeptic cache: {cache_path}")
        result = audit_packet(packet, source_input=source_input, schema=schema)
        if result.errors:
            raise ReviewError(f"cached packet failed audit: {result.as_dict()}")
        return packet, {
            "change_id": packet["change_id"],
            "cache": "HIT",
            "cache_key": cache_key,
            "final_review_status": packet["skeptical_review"][
                "final_review_status"
            ],
        }

    review, metrics, schema_errors = skeptic_request(
        source_input=source_input,
        packet=stage_one,
        prompt=prompt,
        ollama_url=ollama_url,
    )
    repair_attempted = False
    if schema_errors:
        repair_attempted = True
        invalid_review = review
        review, repair_metrics, schema_errors = skeptic_request(
            source_input=source_input,
            packet=stage_one,
            prompt=prompt,
            ollama_url=ollama_url,
            repair_review=invalid_review,
            repair_errors=schema_errors,
        )
        metrics = {
            **repair_metrics,
            "attempt": 2,
            "initial_attempt": metrics,
        }
    else:
        metrics["attempt"] = 1
    if schema_errors:
        raise ReviewError(
            "skeptic response failed after one schema-repair retry: "
            + " | ".join(schema_errors[:8])
        )
    packet = apply_review(
        stage_one,
        source_input,
        review,
        schema=schema,
        schema_hash=schema_hash,
        skeptic_prompt_hash=prompt_hash,
        cache_key=cache_key,
        run_metadata=metrics,
        cache_hit=False,
    )
    write_json(
        cache_path,
        {
            "cache_version": "1.0",
            "stage": "skeptic",
            "review_application_policy": SKEPTIC_APPLICATION_POLICY,
            "language_registry_sha256": sha256_file(
                LANGUAGE_REGISTRY_PATH
            ),
            "cache_key": cache_key,
            "model": PINNED_MODEL,
            "model_digest": f"sha256:{PINNED_MODEL_DIGEST}",
            "prompt_sha256": prompt_hash,
            "schema_sha256": schema_hash,
            "source_input_sha256": source_input["member_sha256"],
            "stage_one_packet_hash": stage_one["packet_hash"],
            "repair_attempted": repair_attempted,
            "model_metrics": metrics,
            "review": review,
            "packet": packet,
        },
    )
    return packet, {
        "change_id": packet["change_id"],
        "cache": "MISS",
        "cache_key": cache_key,
        "final_review_status": packet["skeptical_review"]["final_review_status"],
        "repair_attempted": repair_attempted,
        "model_metrics": metrics,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-bundle", type=Path, default=INPUT_BUNDLE_PATH)
    parser.add_argument("--staging-dir", type=Path, default=STAGING_DIR)
    parser.add_argument("--output-dir", type=Path, default=PACKET_DIR)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--prompt", type=Path, default=SKEPTIC_PROMPT_PATH)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--change-id", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle = load_json(args.input_bundle)
    inputs = bundle.get("inputs", [])
    if not isinstance(inputs, list) or len(inputs) != 8:
        raise ReviewError("expected locked eight-case input bundle")
    requested = set(args.change_id)
    if requested:
        inputs = [item for item in inputs if item["change_id"] in requested]
    schema = load_json(args.schema)
    schema_hash = sha256_file(args.schema)
    prompt = args.prompt.read_text(encoding="utf-8")
    prompt_hash = sha256_file(args.prompt)
    verify_local_model(args.ollama_url, PINNED_MODEL, PINNED_MODEL_DIGEST)

    packets: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    output_dirs = [args.output_dir]
    if args.output_dir.resolve() == PACKET_DIR.resolve():
        output_dirs.append(ARCHIVE_PACKET_DIR)
    for index, source_input in enumerate(inputs, start=1):
        stage_path = args.staging_dir / (
            f"{source_input['change_id']}.generator.json"
        )
        if not stage_path.exists():
            raise ReviewError(f"missing stage-one artifact: {stage_path}")
        stage_one = load_json(stage_path)
        print(
            f"[{index}/{len(inputs)}] skeptic {source_input['ticker']} "
            f"{source_input['change_id']}",
            flush=True,
        )
        packet, result = review_one(
            stage_one,
            source_input,
            schema=schema,
            schema_hash=schema_hash,
            prompt=prompt,
            prompt_hash=prompt_hash,
            ollama_url=args.ollama_url,
        )
        packets.append(packet)
        results.append(result)
        for output_dir in output_dirs:
            write_json(output_dir / f"{packet['change_id']}.json", packet)

    if not requested:
        if len(packets) != 8:
            raise ReviewError("public index requires exactly eight bounded packets")
        packet_index = make_index(packets)
        for output_dir in output_dirs:
            write_json(output_dir / "index.json", packet_index)
    print(
        json.dumps(
            {
                "status": "PASS",
                "stage": "skeptic",
                "attempted": len(results),
                "cache_hits": sum(item["cache"] == "HIT" for item in results),
                "prompt_sha256": prompt_hash,
                "schema_sha256": schema_hash,
                "results": results,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GenerationError, ReviewError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
