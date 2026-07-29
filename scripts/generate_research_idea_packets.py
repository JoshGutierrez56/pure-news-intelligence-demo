#!/usr/bin/env python3
"""Generate bounded stage-one Research Idea packets with local Ollama.

The public site never imports or calls this script. It is an explicit local
workflow that reads the eight-case formation-time bundle, verifies the pinned
local model digest, requests structured JSON, validates it, and caches valid
stage-one artifacts. It never reads the public record's ex-post outcome field.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from research_idea_common import (
    DEFAULT_DISCLAIMER,
    GENERATOR_PROMPT_PATH,
    INPUT_BUNDLE_PATH,
    MODEL_OPTIONS,
    PINNED_MODEL,
    PINNED_MODEL_DIGEST,
    ROOT,
    SCHEMA_PATH,
    SKEPTIC_PROMPT_PATH,
    audit_packet,
    canonical_json,
    compute_cache_key,
    compute_packet_hash,
    load_json,
    prohibited_language_findings,
    sha256_file,
    sha256_json,
    sha256_text,
    validate_schema,
    write_json,
)


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
STAGING_DIR = ROOT / "artifacts" / "research_idea_generation" / "v1"
CACHE_DIR = ROOT / "artifacts" / "research_idea_cache" / "v1" / "generator"
GENERATOR_INPUT_POLICY = "formation_time_allowlist_v1"
GENERATOR_RESPONSE_FIELDS = (
    "packet_status",
    "system_interpretation",
    "economic_mechanisms",
    "affected_entities",
    "research_hypotheses",
    "analyst_questions",
    "scenario_analysis",
    "illustrative_trade_hypothesis",
    "confidence",
)


def model_input_projection(source_input: dict[str, Any]) -> dict[str, Any]:
    """Return only fields expressly permitted by the V1 input contract."""

    evidence = source_input["evidence"]
    frozen = source_input["frozen_classification"]
    return {
        "input_version": source_input["input_version"],
        "change_id": source_input["change_id"],
        "issuer": source_input["issuer"],
        "ticker": source_input["ticker"],
        "filing_date": source_input["filing_date"],
        "formation_timestamp": source_input["formation_timestamp"],
        "section": source_input["section"],
        "source_url": source_input["source_url"],
        "identifiers": copy.deepcopy(source_input["identifiers"]),
        "prior_filing": copy.deepcopy(source_input["prior_filing"]),
        "evidence": {
            "evidence_ids": copy.deepcopy(evidence["evidence_ids"]),
            "prior_excerpt": evidence["prior_excerpt"],
            "current_excerpt": evidence["current_excerpt"],
            "added_text": evidence["added_text"],
            "removed_text": evidence["removed_text"],
            "offsets": copy.deepcopy(evidence["offsets"]),
            "related_prior_8k": copy.deepcopy(evidence["related_prior_8k"]),
            "related_prior_news": copy.deepcopy(evidence["related_prior_news"]),
        },
        "frozen_classification": {
            "category": frozen["category"],
            "direction": frozen["direction"],
            "materiality": frozen["materiality"],
            "confidence": frozen["confidence"],
        },
        "novelty": {
            "classification": source_input["novelty"]["classification"],
        },
        "reason_code": source_input["reason"]["code"],
    }


class GenerationError(RuntimeError):
    pass


def require_loopback_ollama_url(ollama_url: str) -> None:
    """Fail closed before any filing evidence can be sent off-machine."""

    parsed = urlparse(ollama_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise GenerationError(
            "Ollama URL must be a credential-free HTTP loopback endpoint "
            "(localhost, 127.0.0.1, or ::1)"
        )


def http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: int = 1800,
) -> dict[str, Any]:
    body = None if payload is None else canonical_json(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except OSError:
            detail = ""
        raise GenerationError(
            f"local Ollama request failed: {url}: HTTP {exc.code}: {detail}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GenerationError(f"local Ollama request failed: {url}: {exc}") from exc


def verify_local_model(ollama_url: str, model: str, expected_digest: str) -> None:
    require_loopback_ollama_url(ollama_url)
    payload = http_json("GET", f"{ollama_url.rstrip('/')}/api/tags", timeout=30)
    candidates = [
        item
        for item in payload.get("models", [])
        if item.get("name") == model or item.get("model") == model
    ]
    if len(candidates) != 1:
        raise GenerationError(
            f"expected one installed local model named {model}; found {len(candidates)}"
        )
    if candidates[0].get("remote_host"):
        raise GenerationError(f"model {model} is remote; cloud models are prohibited")
    observed = str(candidates[0].get("digest", "")).removeprefix("sha256:")
    if observed != expected_digest.removeprefix("sha256:"):
        raise GenerationError(
            f"model digest mismatch: expected {expected_digest}, observed {observed}"
        )


def parse_model_json(response: dict[str, Any]) -> dict[str, Any]:
    message = response.get("message")
    if not isinstance(message, dict):
        raise GenerationError("Ollama response is missing message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise GenerationError("Ollama response content is empty")
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        tail = text[-240:].replace("\r", "\\r").replace("\n", "\\n")
        raise GenerationError(
            "model did not return valid JSON: "
            f"{exc}; content_length={len(text)}; "
            f"done={response.get('done')!r}; "
            f"done_reason={response.get('done_reason')!r}; "
            f"error={response.get('error')!r}; keys={sorted(response)}; "
            f"tail={tail!r}"
        ) from exc
    if not isinstance(parsed, dict):
        raise GenerationError("model response must be a JSON object")
    return parsed


def ollama_format_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Adapt prefix regexes for Ollama's structured-output converter.

    Ollama 0.32.5 requires every regex to end with ``$``. Appending ``.*$``
    to an otherwise prefix-anchored pattern preserves the frozen Draft 2020-12
    schema's meaning without mutating the hash-frozen schema file.
    """

    adapted = copy.deepcopy(schema)

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            pattern = value.get("pattern")
            if (
                isinstance(pattern, str)
                and pattern.startswith("^")
                and not pattern.endswith("$")
            ):
                value["pattern"] = pattern + ".*$"
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(adapted)
    return adapted


def analytical_response_schema(
    packet_schema: dict[str, Any],
    source_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the strict model-owned projection from the frozen packet schema."""

    response_schema: dict[str, Any] = {
        "$schema": packet_schema["$schema"],
        "type": "object",
        "additionalProperties": False,
        "required": list(GENERATOR_RESPONSE_FIELDS),
        "properties": {
            field: copy.deepcopy(packet_schema["properties"][field])
            for field in GENERATOR_RESPONSE_FIELDS
        },
    }
    required_definitions: set[str] = set()

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                name = reference.rsplit("/", 1)[-1]
                if name not in required_definitions:
                    required_definitions.add(name)
                    collect(packet_schema["$defs"][name])
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(response_schema)
    response_schema["$defs"] = {
        name: copy.deepcopy(definition)
        for name, definition in packet_schema["$defs"].items()
        if name in required_definitions
    }
    if source_input is not None and "evidenceId" in response_schema["$defs"]:
        evidence = source_input["evidence"]
        permitted_ids = set(evidence["evidence_ids"].values())
        permitted_ids.update(
            item["evidence_id"]
            for collection in ("related_prior_8k", "related_prior_news")
            for item in evidence.get(collection, [])
        )
        response_schema["$defs"]["evidenceId"] = {
            "type": "string",
            "enum": sorted(permitted_ids),
        }
    return response_schema


def normalize_related_8k(
    source_input: dict[str, Any],
) -> list[dict[str, Any]]:
    method = source_input["novelty"]["method"]
    normalized = []
    for item in source_input["evidence"]["related_prior_8k"]:
        normalized.append(
            {
                "evidence_id": item["evidence_id"],
                "accession_number": item["accession_number"],
                "source_url": item["url"],
                "acceptance_timestamp": item["acceptance_timestamp"],
                "information_date": item["information_date"],
                "item_codes": str(item.get("item_codes", "")).split(),
                "excerpt": "",
                "offset": None,
                "matched_terms": item.get("matched_terms", []),
                "match_method": method,
                "content_sha256": None,
            }
        )
    return normalized


def normalize_related_news(
    source_input: dict[str, Any],
) -> list[dict[str, Any]]:
    method = source_input["novelty"]["method"]
    return [
        {
            "evidence_id": item["evidence_id"],
            "story_chain_id": item["story_chain_id"],
            "source_url": None,
            "provider_host": item["provider_host"],
            "publication_timestamp": item["publication_timestamp"],
            "headline": item["headline"],
            "matched_terms": item.get("matched_terms", []),
            "match_method": method,
            "headline_only": True,
        }
        for item in source_input["evidence"]["related_prior_news"]
    ]


def model_run(
    *,
    role: str,
    run_status: str,
    prompt_version: str,
    prompt_hash: str,
    schema_hash: str,
    cache_key: str,
    attempt: int,
    started_at: str | None = None,
    completed_at: str | None = None,
    request_hash: str | None = None,
    response_hash: str | None = None,
) -> dict[str, Any]:
    return {
        "role": role,
        "run_status": run_status,
        "model_name": PINNED_MODEL,
        "model_manifest_digest": f"sha256:{PINNED_MODEL_DIGEST}",
        "runtime_name": "Ollama",
        "runtime_version": "0.32.5",
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_hash,
        "schema_version": "1.0",
        "schema_sha256": schema_hash,
        "temperature": MODEL_OPTIONS["temperature"],
        "seed": MODEL_OPTIONS["seed"],
        "context_length": MODEL_OPTIONS["num_ctx"],
        "maximum_output_tokens": MODEL_OPTIONS["num_predict"],
        "think_enabled": False,
        "started_at": started_at,
        "completed_at": completed_at,
        "request_sha256": request_hash,
        "response_sha256": response_hash,
        "cache_key_sha256": cache_key,
        "attempt": attempt,
    }


def authoritative_packet(
    candidate: dict[str, Any],
    source_input: dict[str, Any],
    *,
    prompt_hash: str,
    skeptic_prompt_hash: str,
    schema_hash: str,
    generator_cache_key: str,
    skeptic_cache_key: str,
    run_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Overwrite every factual/provenance field with its frozen input value."""

    packet = {
        field: copy.deepcopy(candidate.get(field))
        for field in GENERATOR_RESPONSE_FIELDS
    }
    input_evidence = source_input["evidence"]
    frozen = source_input["frozen_classification"]
    change_id = source_input["change_id"]
    prior_id = source_input["identifiers"]["prior_filing_id"]
    current_id = source_input["identifiers"]["current_filing_id"]
    prior_url = source_input["prior_filing"]["source_url"]
    current_url = source_input["source_url"]
    stage_one_status = str(candidate.get("packet_status", ""))
    if stage_one_status not in {
        "DRAFT_PENDING_SKEPTIC",
        "HOLD_UNSUPPORTED",
        "HOLD_AMBIGUOUS",
        "HOLD_INSUFFICIENT_EVIDENCE",
    }:
        stage_one_status = "DRAFT_PENDING_SKEPTIC"
    packet.update(
        {
            "packet_version": "1.0",
            "packet_id": f"research-idea-v1:{change_id}",
            "packet_status": stage_one_status,
            "change_id": change_id,
            "issuer": source_input["issuer"],
            "ticker": source_input["ticker"],
            "filing_date": source_input["filing_date"],
            "formation_timestamp": source_input["formation_timestamp"],
            "section": source_input["section"],
            "source_url": source_input["source_url"],
            "input_lineage": {
                "input_contract_version": "research_idea_input_v1",
                "source_record_sha256": source_input["member_sha256"],
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
                    "frozen_company_metadata",
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
            "evidence": {
                "prior_filing_id": prior_id,
                "current_filing_id": current_id,
                "prior_source_url": prior_url,
                "current_source_url": current_url,
                "prior_excerpt": input_evidence["prior_excerpt"],
                "current_excerpt": input_evidence["current_excerpt"],
                "added_text": input_evidence["added_text"],
                "removed_text": input_evidence["removed_text"],
                "evidence_ids": copy.deepcopy(input_evidence["evidence_ids"]),
                "evidence_offsets": copy.deepcopy(input_evidence["offsets"]),
                "evidence_offsets_verified": True,
                "related_prior_8k": copy.deepcopy(
                    input_evidence["related_prior_8k"]
                ),
                "related_prior_news": copy.deepcopy(
                    input_evidence["related_prior_news"]
                ),
            },
            "frozen_classification": {
                "category": frozen["category"],
                "direction": frozen["direction"],
                "materiality": frozen["materiality"],
                "novelty": source_input["novelty"]["classification"],
                "confidence": frozen["confidence"],
                "classification_method": frozen["classification_method"],
                "novelty_method": source_input["novelty"]["method"],
                "novelty_is_causal_claim": False,
            },
            "generation_metadata": {
                "generation_policy_version": "research_idea_generation_policy_v1",
                "generator_run": model_run(
                    role="GENERATOR",
                    run_status="COMPLETE",
                    prompt_version="research_idea_generator_v1",
                    prompt_hash=prompt_hash,
                    schema_hash=schema_hash,
                    cache_key=generator_cache_key,
                    attempt=run_metadata["attempt"],
                    started_at=run_metadata["started_at"],
                    completed_at=run_metadata["completed_at"],
                    request_hash=run_metadata["request_sha256"],
                    response_hash=run_metadata["response_sha256"],
                ),
                "skeptic_run": model_run(
                    role="SKEPTIC",
                    run_status="NOT_RUN",
                    prompt_version="research_idea_skeptic_v1",
                    prompt_hash=skeptic_prompt_hash,
                    schema_hash=schema_hash,
                    cache_key=skeptic_cache_key,
                    attempt=0,
                ),
                "hardware": {
                    "operating_system": "Windows 11 Home 10.0.26200",
                    "cpu": "AMD Ryzen 9 5900XT (16 cores / 32 threads)",
                    "system_memory_gib": 127.91,
                    "gpu": "NVIDIA GeForce RTX 5090",
                    "gpu_memory_mib": 32607,
                },
                "no_cloud_calls": True,
                "no_chain_of_thought_stored": True,
                "valid_outputs_cached": True,
                "maximum_schema_repair_retries": 1,
                "accepted_packet_regeneration_policy": "NEVER_SILENTLY_REGENERATE",
            },
            "skeptical_review": {
                "review_version": "research_idea_skeptic_v1",
                "critical_objections": [],
                "alternative_explanations": [],
                "pricing_or_attention_concerns": [],
                "unsupported_claims_removed": [],
                "evidence_ids_reviewed": [],
                "critical_grounding_defect": None,
                "final_review_status": "PENDING_REVIEW",
                "review_summary": (
                    "Stage-one artifact; skeptical review has not run."
                ),
            },
            "analyst_disposition": {
                "status": "UNREVIEWED",
                "analyst_notes": "",
                "edited_fields": [],
                "review_timestamp": None,
                "saved_locally_only": True,
            },
            "audit_metadata": {
                "audit_version": "research_idea_audit_v1",
                "audited_at": None,
                "schema_validation": {
                    "status": "NOT_RUN",
                    "validator_name": "jsonschema.Draft202012Validator",
                    "validator_version": "4.26.0",
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
                    "formation_timestamp": source_input["formation_timestamp"],
                    "checked_timestamp_count": 0,
                    "violations": [],
                },
                "evidence_integrity": {
                    "status": "NOT_RUN",
                    "referenced_evidence_ids": [],
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
                "publication_decision": stage_one_status,
                "audit_findings": [],
            },
            "disclaimer": DEFAULT_DISCLAIMER,
        }
    )
    packet["packet_hash"] = compute_packet_hash(packet)
    return packet


def validation_messages(
    packet: dict[str, Any],
    schema: dict[str, Any],
    source_input: dict[str, Any] | None = None,
) -> list[str]:
    messages = [
        f"{finding.path}: {finding.message}"
        for finding in validate_schema(packet, schema)
    ]
    messages.extend(
        f"{finding.path}: {finding.message}"
        for finding in prohibited_language_findings(packet)
    )
    if source_input is not None:
        messages.extend(
            f"{finding.path}: {finding.message}"
            for finding in audit_packet(
                packet,
                source_input=source_input,
                schema=schema,
            ).errors
            if finding.code != "SKEPTIC_STATUS"
        )
    return messages


def model_request(
    *,
    source_input: dict[str, Any],
    schema: dict[str, Any],
    prompt: str,
    ollama_url: str,
    repair_candidate: dict[str, Any] | None = None,
    repair_errors: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    response_schema = analytical_response_schema(schema, source_input)
    input_payload = model_input_projection(source_input)
    if repair_candidate is None:
        user_content = (
            "Create the model-owned analytical projection of the stage-one "
            "Research Idea packet from this allowed, formation-time-only input. "
            "Return exactly the nine fields in GENERATOR_RESPONSE_SCHEMA_JSON. "
            "The deterministic wrapper—not you—adds identity, source evidence, "
            "lineage, hashes, model metadata, audit metadata, skeptic status, "
            "analyst disposition, and disclaimer. Return JSON only.\n\n"
            "Use only evidence IDs listed in the response schema enum. Frozen "
            "classification metadata has no separate evidence ID; do not invent "
            "one or turn that metadata into an evidence_facts item.\n\n"
            "ALLOWED_INPUT_JSON:\n"
            + canonical_json(input_payload)
        )
    else:
        user_content = (
            "Repair the candidate solely for the listed schema/safety defects. "
            "Do not add facts, change source evidence, or broaden the claim. "
            "Return the complete corrected JSON object only.\n\n"
            "ALLOWED_INPUT_JSON:\n"
            + canonical_json(input_payload)
            + "\n\nVALIDATION_ERRORS:\n"
            + "\n".join(f"- {message}" for message in (repair_errors or []))
            + "\n\nCANDIDATE_JSON:\n"
            + canonical_json(repair_candidate)
        )
    permitted_evidence_ids = sorted(
        {
            *input_payload["evidence"]["evidence_ids"].values(),
            *(
                item["evidence_id"]
                for collection in ("related_prior_8k", "related_prior_news")
                for item in input_payload["evidence"].get(collection, [])
            ),
        }
    )
    user_content += (
        "\n\nPERMITTED_EVIDENCE_IDS_JSON:\n"
        + canonical_json(permitted_evidence_ids)
        + "\n\nGENERATOR_RESPONSE_SCHEMA_JSON:\n"
        + canonical_json(response_schema)
    )
    request_payload = {
        "model": PINNED_MODEL,
        "stream": False,
        "think": False,
        # Ollama 0.32.5 cannot compile this strict Draft 2020-12 schema into
        # its grammar ("failed to parse grammar"). JSON mode plus immediate
        # frozen-schema validation and one bounded repair preserves fail-closed
        # behavior without changing the frozen schema.
        "format": "json",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content},
        ],
        "options": MODEL_OPTIONS,
        "keep_alive": "30m",
    }
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    request_sha256 = sha256_json(request_payload)
    response = http_json(
        "POST",
        f"{ollama_url.rstrip('/')}/api/chat",
        request_payload,
    )
    completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    candidate = parse_model_json(response)
    response_sha256 = sha256_text(
        str(response.get("message", {}).get("content", ""))
    )
    return candidate, {
        "started_at": started_at,
        "completed_at": completed_at,
        "request_sha256": request_sha256,
        "response_sha256": response_sha256,
        "total_duration": response.get("total_duration"),
        "load_duration": response.get("load_duration"),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
        "eval_duration": response.get("eval_duration"),
    }


def generate_one(
    source_input: dict[str, Any],
    *,
    schema: dict[str, Any],
    prompt: str,
    prompt_hash: str,
    schema_hash: str,
    ollama_url: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    input_hash = source_input["member_sha256"]
    cache_key = compute_cache_key(
        stage="generator",
        model_digest=PINNED_MODEL_DIGEST,
        prompt_hash=prompt_hash,
        schema_hash=schema_hash,
        input_hash=input_hash,
        options={
            **MODEL_OPTIONS,
            "input_policy": GENERATOR_INPUT_POLICY,
        },
    )
    cache_path = CACHE_DIR / f"{cache_key}.json"
    staging_path = STAGING_DIR / f"{source_input['change_id']}.generator.json"
    if cache_path.exists():
        cached = load_json(cache_path)
        packet = cached.get("packet")
        if not isinstance(packet, dict):
            raise GenerationError(f"invalid generator cache: {cache_path}")
        errors = validation_messages(packet, schema, source_input)
        if errors:
            raise GenerationError(
                f"cached generator packet is invalid: {cache_path}: {errors[:3]}"
            )
        write_json(staging_path, packet)
        return packet, {
            "change_id": source_input["change_id"],
            "cache": "HIT",
            "cache_key": cache_key,
            "repair_attempted": bool(cached.get("repair_attempted")),
            "model_metrics": cached.get("model_metrics", {}),
        }

    skeptic_prompt_hash = sha256_file(SKEPTIC_PROMPT_PATH)
    skeptic_cache_key = compute_cache_key(
        stage="skeptic",
        model_digest=PINNED_MODEL_DIGEST,
        prompt_hash=skeptic_prompt_hash,
        schema_hash=schema_hash,
        input_hash=input_hash,
        options=MODEL_OPTIONS,
    )
    candidate, metrics = model_request(
        source_input=source_input,
        schema=schema,
        prompt=prompt,
        ollama_url=ollama_url,
    )
    packet = authoritative_packet(
        candidate,
        source_input,
        prompt_hash=prompt_hash,
        skeptic_prompt_hash=skeptic_prompt_hash,
        schema_hash=schema_hash,
        generator_cache_key=cache_key,
        skeptic_cache_key=skeptic_cache_key,
        run_metadata={**metrics, "attempt": 1},
    )
    errors = validation_messages(packet, schema, source_input)
    repair_attempted = False
    if errors:
        repair_attempted = True
        candidate, repair_metrics = model_request(
            source_input=source_input,
            schema=schema,
            prompt=prompt,
            ollama_url=ollama_url,
            repair_candidate={
                field: copy.deepcopy(packet.get(field))
                for field in GENERATOR_RESPONSE_FIELDS
            },
            repair_errors=errors,
        )
        metrics["repair"] = repair_metrics
        packet = authoritative_packet(
            candidate,
            source_input,
            prompt_hash=prompt_hash,
            skeptic_prompt_hash=skeptic_prompt_hash,
            schema_hash=schema_hash,
            generator_cache_key=cache_key,
            skeptic_cache_key=skeptic_cache_key,
            run_metadata={**repair_metrics, "attempt": 2},
        )
        errors = validation_messages(packet, schema, source_input)
    if errors:
        raise GenerationError(
            f"{source_input['change_id']} failed after one repair: "
            + " | ".join(errors[:8])
        )

    cache_record = {
        "cache_version": "1.0",
        "cache_key": cache_key,
        "stage": "generator",
        "model": PINNED_MODEL,
        "model_digest": f"sha256:{PINNED_MODEL_DIGEST}",
        "prompt_sha256": prompt_hash,
        "schema_sha256": schema_hash,
        "input_sha256": input_hash,
        "options": MODEL_OPTIONS,
        "repair_attempted": repair_attempted,
        "model_metrics": metrics,
        "packet": packet,
    }
    write_json(cache_path, cache_record)
    write_json(staging_path, packet)
    return packet, {
        "change_id": source_input["change_id"],
        "cache": "MISS",
        "cache_key": cache_key,
        "repair_attempted": repair_attempted,
        "model_metrics": metrics,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-bundle", type=Path, default=INPUT_BUNDLE_PATH)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument("--prompt", type=Path, default=GENERATOR_PROMPT_PATH)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument(
        "--change-id",
        action="append",
        default=[],
        help="Generate only this locked change ID; repeat to select several.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle = load_json(args.input_bundle)
    inputs = bundle.get("inputs")
    if not isinstance(inputs, list) or len(inputs) != 8:
        raise GenerationError("expected the locked eight-case input bundle")
    requested = set(args.change_id)
    if requested:
        known = {item["change_id"] for item in inputs}
        unknown = requested - known
        if unknown:
            raise GenerationError(f"unknown change IDs: {sorted(unknown)}")
        inputs = [item for item in inputs if item["change_id"] in requested]

    schema = load_json(args.schema)
    prompt = args.prompt.read_text(encoding="utf-8")
    schema_hash = sha256_file(args.schema)
    prompt_hash = sha256_file(args.prompt)
    verify_local_model(args.ollama_url, PINNED_MODEL, PINNED_MODEL_DIGEST)

    results: list[dict[str, Any]] = []
    for index, source_input in enumerate(inputs, start=1):
        print(
            f"[{index}/{len(inputs)}] generator {source_input['ticker']} "
            f"{source_input['change_id']}",
            flush=True,
        )
        _packet, result = generate_one(
            source_input,
            schema=schema,
            prompt=prompt,
            prompt_hash=prompt_hash,
            schema_hash=schema_hash,
            ollama_url=args.ollama_url,
        )
        results.append(result)
    print(
        json.dumps(
            {
                "status": "PASS",
                "stage": "generator",
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
    except GenerationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
