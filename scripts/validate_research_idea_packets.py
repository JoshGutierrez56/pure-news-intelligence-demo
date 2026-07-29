#!/usr/bin/env python3
"""Deterministically validate bounded Research Idea Engine V1 packets.

The validator is deliberately offline. It checks packets against the frozen
schema, prohibited-language registry, and formation-time input bundle. It can
audit either stage-one ``*.generator.json`` artifacts or final public packets.
No packet is changed by this script.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from research_idea_common import (
    FUTURE_DATA_KEYS,
    INPUT_BUNDLE_PATH,
    LANGUAGE_REGISTRY_PATH,
    PACKET_DIR,
    SCHEMA_PATH,
    AuditFinding,
    audit_packet,
    canonical_json,
    compute_packet_hash,
    is_negated_context,
    iter_json,
    load_json,
    sha256_file,
    sha256_json,
    sha256_text,
)


STAGING_DIR = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "research_idea_generation"
    / "v1"
)
FINAL_REVIEW_STATUSES = {
    "PASS",
    "PASS_WITH_EDITS",
    "HOLD_UNSUPPORTED",
    "HOLD_AMBIGUOUS",
    "HOLD_INSUFFICIENT_EVIDENCE",
    "REJECTED_BY_SKEPTIC",
}
PUBLISHABLE_REVIEW_STATUSES = {"PASS", "PASS_WITH_EDITS"}
EXPECTED_FINAL_AUDIT_STATUSES = {
    "schema_validation": "PASS",
    "future_information": "PASS",
    "evidence_integrity": "PASS",
    "prohibited_language": "PASS",
    "determinism": "PASS",
}
SKIPPED_LANGUAGE_PREFIXES = (
    "/evidence/",
    "/skeptical_review/unsupported_claims_removed",
)
PROHIBITED_FIELD_NAMES = {
    "allocation",
    "leverage",
    "personalized_allocation",
    "position_size",
    "price_target",
    "stop_loss",
    "target_price",
}
NUMERIC_ACTION_PATTERNS = (
    (
        "NUMERIC_POSITION_SIZE",
        re.compile(
            r"\b(?:position\s+size|size\s+the\s+position)\b"
            r".{0,40}\b\d+(?:\.\d+)?\s*(?:%|shares?|units?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "NUMERIC_PRICE_TARGET",
        re.compile(
            r"\b(?:price\s+target|target\s+price)\b"
            r".{0,32}(?:[$€£]\s*)?\d+(?:\.\d+)?",
            re.IGNORECASE,
        ),
    ),
    (
        "NUMERIC_LEVERAGE",
        re.compile(
            r"\b\d+(?:\.\d+)?\s*[x×]\s*(?:gross\s+|net\s+)?"
            r"(?:leverage|exposure)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "NUMERIC_ALLOCATION",
        re.compile(
            r"(?:\b(?:allocate|allocation)\b.{0,32}\b\d+(?:\.\d+)?\s*%"
            r"|\b\d+(?:\.\d+)?\s*%.{0,24}\ballocation\b)",
            re.IGNORECASE,
        ),
    ),
)


class ValidationSetupError(RuntimeError):
    """Raised when validator inputs cannot be loaded deterministically."""


def _finding(
    code: str,
    severity: str,
    message: str,
    path: str = "/",
    **detail: Any,
) -> AuditFinding:
    return AuditFinding(
        code=code,
        severity=severity,
        message=message,
        path=path,
        detail=detail,
    )


def _finding_key(finding: AuditFinding) -> tuple[str, str, str, str, str]:
    severity_order = {"ERROR": "0", "WARNING": "1", "INFO": "2"}
    return (
        severity_order.get(finding.severity, "9"),
        finding.code,
        finding.path,
        finding.message,
        canonical_json(finding.detail),
    )


def _dedupe_findings(findings: Iterable[AuditFinding]) -> list[AuditFinding]:
    unique: dict[tuple[str, str, str, str, str], AuditFinding] = {}
    for finding in findings:
        unique[_finding_key(finding)] = finding
    return sorted(unique.values(), key=_finding_key)


def _input_records(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    records = bundle.get("inputs")
    if not isinstance(records, list):
        raise ValidationSetupError("input bundle must contain an inputs array")
    return records


def validate_input_bundle(bundle: dict[str, Any]) -> list[AuditFinding]:
    """Verify the bundle/member hashes and basic bounded-set invariants."""

    findings: list[AuditFinding] = []
    try:
        records = _input_records(bundle)
    except ValidationSetupError as exc:
        return [_finding("INPUT_BUNDLE", "ERROR", str(exc))]

    declared_count = bundle.get("case_count")
    if declared_count != len(records):
        findings.append(
            _finding(
                "INPUT_BUNDLE_COUNT",
                "ERROR",
                "Declared case_count does not match the inputs array.",
                "/case_count",
                declared=declared_count,
                observed=len(records),
            )
        )

    seen_inputs: set[str] = set()
    seen_changes: set[str] = set()
    manifest_rows: list[str] = []
    for index, record in enumerate(records):
        path = f"/inputs/{index}"
        if not isinstance(record, dict):
            findings.append(
                _finding(
                    "INPUT_RECORD",
                    "ERROR",
                    "Input member is not an object.",
                    path,
                )
            )
            continue
        input_id = str(record.get("input_id", ""))
        change_id = str(record.get("change_id", ""))
        member_hash = str(record.get("member_sha256", ""))
        if not input_id or input_id in seen_inputs:
            findings.append(
                _finding(
                    "INPUT_ID",
                    "ERROR",
                    "Input ID is missing or duplicated.",
                    f"{path}/input_id",
                    input_id=input_id,
                )
            )
        if not change_id or change_id in seen_changes:
            findings.append(
                _finding(
                    "INPUT_CHANGE_ID",
                    "ERROR",
                    "Input change ID is missing or duplicated.",
                    f"{path}/change_id",
                    change_id=change_id,
                )
            )
        seen_inputs.add(input_id)
        seen_changes.add(change_id)
        member_preimage = {
            key: value for key, value in record.items() if key != "member_sha256"
        }
        computed_member_hash = sha256_json(member_preimage)
        if member_hash != computed_member_hash:
            findings.append(
                _finding(
                    "INPUT_MEMBER_HASH",
                    "ERROR",
                    "Input member hash does not match canonical content.",
                    f"{path}/member_sha256",
                    stored=member_hash,
                    computed=computed_member_hash,
                )
            )
        manifest_rows.append(f"{input_id}\t{member_hash}\n")

        for json_path, _value in iter_json(record):
            key = (
                json_path.rsplit("/", 1)[-1]
                .replace("~1", "/")
                .replace("~0", "~")
                .casefold()
            )
            if key in FUTURE_DATA_KEYS:
                findings.append(
                    _finding(
                        "INPUT_EX_POST_FIELD",
                        "ERROR",
                        f"Formation-time input contains prohibited key: {key}",
                        f"{path}{json_path if json_path != '/' else ''}",
                    )
                )

    computed_bundle_hash = sha256_text("".join(manifest_rows))
    if bundle.get("bundle_sha256") != computed_bundle_hash:
        findings.append(
            _finding(
                "INPUT_BUNDLE_HASH",
                "ERROR",
                "Input bundle membership hash does not match.",
                "/bundle_sha256",
                stored=bundle.get("bundle_sha256"),
                computed=computed_bundle_hash,
            )
        )
    formation_policy = bundle.get("formation_policy", {})
    for field_name in (
        "future_information_excluded",
        "local_provenance_paths_excluded",
        "selection_is_outcome_independent",
    ):
        if formation_policy.get(field_name) is not True:
            findings.append(
                _finding(
                    "INPUT_FORMATION_POLICY",
                    "ERROR",
                    f"Formation policy does not affirm {field_name}.",
                    f"/formation_policy/{field_name}",
                )
            )
    return _dedupe_findings(findings)


def _available_evidence_ids(packet: dict[str, Any]) -> set[str]:
    evidence = packet.get("evidence", {})
    identifiers = {
        str(value)
        for value in (evidence.get("evidence_ids") or {}).values()
        if value
    }
    for collection in ("related_prior_8k", "related_prior_news"):
        for item in evidence.get(collection, []) or []:
            if isinstance(item, dict) and item.get("evidence_id"):
                identifiers.add(str(item["evidence_id"]))
    return identifiers


def _referenced_evidence_ids(
    packet: dict[str, Any],
) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    roots = (
        "system_interpretation",
        "economic_mechanisms",
        "affected_entities",
        "research_hypotheses",
        "analyst_questions",
        "scenario_analysis",
        "illustrative_trade_hypothesis",
        "skeptical_review",
    )

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}/{key}"
                if key in (
                    "evidence_ids",
                    "supporting_evidence_ids",
                    "evidence_ids_reviewed",
                ) and isinstance(child, list):
                    references.extend(
                        (f"{child_path}/{index}", str(identifier))
                        for index, identifier in enumerate(child)
                    )
                else:
                    walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}/{index}")

    for root in roots:
        walk(packet.get(root), f"/{root}")
    return references


def _supplemental_language_findings(
    packet: dict[str, Any], registry: dict[str, Any]
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for path, value in iter_json(packet):
        key = (
            path.rsplit("/", 1)[-1]
            .replace("~1", "/")
            .replace("~0", "~")
            .casefold()
        )
        if key in PROHIBITED_FIELD_NAMES:
            findings.append(
                _finding(
                    "PROHIBITED_FIELD",
                    "ERROR",
                    f"Prohibited trade-construction field present: {key}",
                    path,
                )
            )
        if not isinstance(value, str) or any(
            path.startswith(prefix) for prefix in SKIPPED_LANGUAGE_PREFIXES
        ):
            continue
        for code, pattern in NUMERIC_ACTION_PATTERNS:
            for match in pattern.finditer(value):
                if not is_negated_context(
                    value,
                    match.start(),
                    match.end(),
                    registry,
                ):
                    findings.append(
                        _finding(
                            code,
                            "ERROR",
                            "Generated text contains a prohibited numeric "
                            "trade-construction instruction.",
                            path,
                            match=match.group(0),
                        )
                    )
    return findings


def _linkage_findings(
    packet: dict[str, Any], source_input: dict[str, Any]
) -> list[AuditFinding]:
    evidence = packet.get("evidence", {})
    identifiers = source_input.get("identifiers", {})
    prior_filing = source_input.get("prior_filing", {})
    expected = {
        "/source_url": source_input.get("source_url"),
        "/evidence/current_source_url": source_input.get("source_url"),
        "/evidence/prior_source_url": prior_filing.get("source_url"),
        "/evidence/current_filing_id": identifiers.get("current_filing_id"),
        "/evidence/prior_filing_id": identifiers.get("prior_filing_id"),
    }
    actual = {
        "/source_url": packet.get("source_url"),
        "/evidence/current_source_url": evidence.get("current_source_url"),
        "/evidence/prior_source_url": evidence.get("prior_source_url"),
        "/evidence/current_filing_id": evidence.get("current_filing_id"),
        "/evidence/prior_filing_id": evidence.get("prior_filing_id"),
    }
    findings: list[AuditFinding] = []
    for path, expected_value in expected.items():
        if actual[path] != expected_value:
            findings.append(
                _finding(
                    "EVIDENCE_LINK_INTEGRITY",
                    "ERROR",
                    "Packet source link or filing identifier does not match "
                    "the frozen input.",
                    path,
                    expected=expected_value,
                    observed=actual[path],
                )
            )
    lineage = packet.get("input_lineage", {})
    if lineage.get("source_record_sha256") != source_input.get("member_sha256"):
        findings.append(
            _finding(
                "INPUT_LINEAGE",
                "ERROR",
                "Packet source-record hash does not match the frozen input.",
                "/input_lineage/source_record_sha256",
            )
        )
    return findings


def _lifecycle_findings(
    packet: dict[str, Any], stage: str
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    review = packet.get("skeptical_review", {})
    review_status = review.get("final_review_status")
    packet_status = packet.get("packet_status")
    audit = packet.get("audit_metadata", {})
    skeptic_run = packet.get("generation_metadata", {}).get("skeptic_run", {})

    if stage == "staging":
        if review_status != "PENDING_REVIEW":
            findings.append(
                _finding(
                    "STAGING_LIFECYCLE",
                    "ERROR",
                    "A staging packet must have PENDING_REVIEW skeptic status.",
                    "/skeptical_review/final_review_status",
                )
            )
        if skeptic_run.get("run_status") != "NOT_RUN":
            findings.append(
                _finding(
                    "STAGING_LIFECYCLE",
                    "ERROR",
                    "A staging packet must record the skeptic as NOT_RUN.",
                    "/generation_metadata/skeptic_run/run_status",
                )
            )
        if review.get("critical_grounding_defect") is not None:
            findings.append(
                _finding(
                    "STAGING_LIFECYCLE",
                    "ERROR",
                    "A staging packet cannot pre-judge a grounding defect.",
                    "/skeptical_review/critical_grounding_defect",
                )
            )
        findings.append(
            _finding(
                "SKEPTIC_NOT_RUN",
                "WARNING",
                "Stage-one packet is valid for staging but is not publishable "
                "until skeptical review completes.",
                "/skeptical_review/final_review_status",
            )
        )
        return findings

    if review_status not in FINAL_REVIEW_STATUSES:
        findings.append(
            _finding(
                "FINAL_SKEPTIC_STATUS",
                "ERROR",
                "Final packet lacks a terminal skeptical-review status.",
                "/skeptical_review/final_review_status",
            )
        )
    if skeptic_run.get("run_status") != "COMPLETE":
        findings.append(
            _finding(
                "FINAL_SKEPTIC_RUN",
                "ERROR",
                "Final packet does not record a completed skeptical review.",
                "/generation_metadata/skeptic_run/run_status",
            )
        )
    expected_packet_status = (
        "PUBLISHABLE"
        if review_status in PUBLISHABLE_REVIEW_STATUSES
        else review_status
    )
    if packet_status != expected_packet_status:
        findings.append(
            _finding(
                "PUBLICATION_STATUS",
                "ERROR",
                "Packet status is inconsistent with skeptical-review status.",
                "/packet_status",
                expected=expected_packet_status,
                observed=packet_status,
            )
        )
    if audit.get("publication_decision") != packet_status:
        findings.append(
            _finding(
                "AUDIT_PUBLICATION_STATUS",
                "ERROR",
                "Audit publication decision does not match packet status.",
                "/audit_metadata/publication_decision",
            )
        )
    for field_name, expected_status in EXPECTED_FINAL_AUDIT_STATUSES.items():
        observed = (audit.get(field_name) or {}).get("status")
        if observed != expected_status:
            findings.append(
                _finding(
                    "FINAL_AUDIT_STATUS",
                    "ERROR",
                    f"Final {field_name.replace('_', ' ')} audit is not PASS.",
                    f"/audit_metadata/{field_name}/status",
                    expected=expected_status,
                    observed=observed,
                )
            )
    grounding_status = (audit.get("grounding") or {}).get("status")
    expected_grounding = (
        "PASS" if review_status in PUBLISHABLE_REVIEW_STATUSES else "HOLD"
    )
    if grounding_status != expected_grounding:
        findings.append(
            _finding(
                "GROUNDING_AUDIT_STATUS",
                "ERROR",
                "Grounding audit status is inconsistent with the skeptical "
                "review.",
                "/audit_metadata/grounding/status",
                expected=expected_grounding,
                observed=grounding_status,
            )
        )
    if not audit.get("audited_at"):
        findings.append(
            _finding(
                "FINAL_AUDIT_TIMESTAMP",
                "ERROR",
                "Final packet is missing its audit timestamp.",
                "/audit_metadata/audited_at",
            )
        )
    return findings


def infer_stage(packet: dict[str, Any], path: Path, requested: str) -> str:
    if requested in {"staging", "final"}:
        return requested
    review_status = packet.get("skeptical_review", {}).get("final_review_status")
    skeptic_run = (
        packet.get("generation_metadata", {})
        .get("skeptic_run", {})
        .get("run_status")
    )
    if (
        path.name.endswith(".generator.json")
        or review_status == "PENDING_REVIEW"
        or skeptic_run == "NOT_RUN"
    ):
        return "staging"
    return "final"


def audit_one(
    packet: dict[str, Any],
    *,
    source_input: dict[str, Any],
    schema: dict[str, Any],
    registry: dict[str, Any],
    stage: str,
) -> list[AuditFinding]:
    base = audit_packet(
        packet,
        source_input=source_input,
        schema=schema,
        registry=registry,
    ).findings
    available_ids = _available_evidence_ids(packet)
    # The shared V1 audit intentionally knows the four primary excerpt IDs.
    # Related prior 8-K/news IDs are also valid under the frozen schema.
    findings = [
        finding
        for finding in base
        if not (
            finding.code == "UNKNOWN_EVIDENCE_ID"
            and finding.message.removeprefix("Unknown evidence ID: ")
            in available_ids
        )
    ]
    if stage == "staging":
        findings = [
            finding
            for finding in findings
            if finding.code != "SKEPTIC_STATUS"
        ]

    for path, evidence_id in _referenced_evidence_ids(packet):
        if evidence_id not in available_ids:
            findings.append(
                _finding(
                    "UNKNOWN_EVIDENCE_ID",
                    "ERROR",
                    f"Unknown evidence ID: {evidence_id}",
                    path,
                )
            )
    findings.extend(_linkage_findings(packet, source_input))
    findings.extend(_supplemental_language_findings(packet, registry))
    findings.extend(_lifecycle_findings(packet, stage))

    stored_hash = packet.get("packet_hash")
    if isinstance(stored_hash, str) and len(stored_hash) == 64:
        first = compute_packet_hash(packet)
        second = compute_packet_hash(json.loads(canonical_json(packet)))
        if first != second:
            findings.append(
                _finding(
                    "UNSTABLE_PACKET_HASH",
                    "ERROR",
                    "Canonical packet hashing is not stable.",
                    "/packet_hash",
                )
            )
    return _dedupe_findings(findings)


def _packet_paths(source: Path, mode: str = "auto") -> list[Path]:
    if source.is_file():
        return [source]
    if not source.is_dir():
        return []
    candidates = (
        path
        for path in source.glob("*.json")
        if path.name != "index.json" and not path.name.startswith(".")
    )
    if mode == "staging":
        candidates = (
            path for path in candidates if path.name.endswith(".generator.json")
        )
    elif mode == "final":
        candidates = (
            path for path in candidates if not path.name.endswith(".generator.json")
        )
    return sorted(
        candidates,
        key=lambda path: path.name,
    )


def _relative_name(path: Path, source: Path) -> str:
    return path.name if source.is_dir() else source.name


def _index_findings(
    source: Path, packets: list[dict[str, Any]]
) -> list[AuditFinding]:
    if not source.is_dir():
        return []
    index_path = source / "index.json"
    if not index_path.exists():
        return [
            _finding(
                "PUBLIC_INDEX_MISSING",
                "ERROR",
                "Final packet directory is missing index.json.",
                "/index.json",
            )
        ]
    try:
        index = load_json(index_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [
            _finding(
                "PUBLIC_INDEX_JSON",
                "ERROR",
                f"Could not parse index.json: {exc}",
                "/index.json",
            )
        ]
    findings: list[AuditFinding] = []
    entries = index.get("packets")
    if not isinstance(entries, list):
        return [
            _finding(
                "PUBLIC_INDEX_SCHEMA",
                "ERROR",
                "index.json must contain a packets array.",
                "/index.json/packets",
            )
        ]
    if index.get("packet_count") != len(entries):
        findings.append(
            _finding(
                "PUBLIC_INDEX_COUNT",
                "ERROR",
                "Index packet_count does not match its entries.",
                "/index.json/packet_count",
            )
        )
    by_change = {str(packet.get("change_id")): packet for packet in packets}
    seen_changes: set[str] = set()
    seen_packets: set[str] = set()
    for position, entry in enumerate(entries):
        entry_path = f"/index.json/packets/{position}"
        if not isinstance(entry, dict):
            findings.append(
                _finding(
                    "PUBLIC_INDEX_ENTRY",
                    "ERROR",
                    "Index entry is not an object.",
                    entry_path,
                )
            )
            continue
        change_id = str(entry.get("change_id", ""))
        packet_id = str(entry.get("packet_id", ""))
        if change_id in seen_changes or packet_id in seen_packets:
            findings.append(
                _finding(
                    "PUBLIC_INDEX_DUPLICATE",
                    "ERROR",
                    "Index contains a duplicate change or packet ID.",
                    entry_path,
                )
            )
        seen_changes.add(change_id)
        seen_packets.add(packet_id)
        packet = by_change.get(change_id)
        if packet is None:
            findings.append(
                _finding(
                    "PUBLIC_INDEX_LINK",
                    "ERROR",
                    "Index entry does not link to a loaded disclosure change.",
                    f"{entry_path}/change_id",
                )
            )
            continue
        expected_path = f"{change_id}.json"
        checks = {
            "path": expected_path,
            "packet_id": packet.get("packet_id"),
            "packet_hash": packet.get("packet_hash"),
        }
        for field_name, expected in checks.items():
            if entry.get(field_name) != expected:
                findings.append(
                    _finding(
                        "PUBLIC_INDEX_LINK",
                        "ERROR",
                        f"Index {field_name} does not match the packet.",
                        f"{entry_path}/{field_name}",
                        expected=expected,
                        observed=entry.get(field_name),
                    )
                )
    if seen_changes != set(by_change):
        findings.append(
            _finding(
                "PUBLIC_INDEX_MEMBERSHIP",
                "ERROR",
                "Index membership does not match loaded final packets.",
                "/index.json/packets",
                missing=sorted(set(by_change) - seen_changes),
                unexpected=sorted(seen_changes - set(by_change)),
            )
        )
    stored_index_hash = index.get("index_sha256")
    index_preimage = {
        key: value for key, value in index.items() if key != "index_sha256"
    }
    computed_index_hash = sha256_json(index_preimage)
    if stored_index_hash != computed_index_hash:
        findings.append(
            _finding(
                "PUBLIC_INDEX_HASH",
                "ERROR",
                "Index hash does not match canonical index content.",
                "/index.json/index_sha256",
                stored=stored_index_hash,
                computed=computed_index_hash,
            )
        )
    return _dedupe_findings(findings)


def _packet_summary(
    *,
    packet: dict[str, Any],
    source_name: str,
    stage: str,
    findings: list[AuditFinding],
) -> dict[str, Any]:
    errors = sum(item.severity == "ERROR" for item in findings)
    warnings = sum(item.severity == "WARNING" for item in findings)
    return {
        "source_file": source_name,
        "stage": stage,
        "change_id": str(packet.get("change_id", "")),
        "packet_id": str(packet.get("packet_id", "")),
        "packet_hash": str(packet.get("packet_hash", "")),
        "packet_status": str(packet.get("packet_status", "")),
        "skeptic_status": str(
            packet.get("skeptical_review", {}).get(
                "final_review_status", ""
            )
        ),
        "status": "PASS" if errors == 0 else "FAIL",
        "error_count": errors,
        "warning_count": warnings,
        "findings": [finding.as_dict() for finding in findings],
    }


def validate_packet_set(
    packet_source: Path,
    *,
    input_bundle_path: Path = INPUT_BUNDLE_PATH,
    schema_path: Path = SCHEMA_PATH,
    registry_path: Path = LANGUAGE_REGISTRY_PATH,
    mode: str = "auto",
    change_ids: Iterable[str] = (),
    require_complete: bool | None = None,
) -> dict[str, Any]:
    """Return a stable machine-readable audit summary for a packet set."""

    if mode not in {"auto", "staging", "final"}:
        raise ValidationSetupError(f"unsupported mode: {mode}")
    for required in (input_bundle_path, schema_path, registry_path):
        if not required.is_file():
            raise ValidationSetupError(f"required file not found: {required}")

    bundle = load_json(input_bundle_path)
    schema = load_json(schema_path)
    registry = load_json(registry_path)
    records = _input_records(bundle)
    inputs_by_change = {
        str(record.get("change_id")): record for record in records
    }
    requested = {str(value) for value in change_ids if str(value)}
    paths = _packet_paths(packet_source, mode)
    collection_findings = validate_input_bundle(bundle)
    if not paths:
        collection_findings.append(
            _finding(
                "PACKET_SOURCE_EMPTY",
                "ERROR",
                "No packet JSON files were found at the requested source.",
                "/packets",
            )
        )
    packets: list[dict[str, Any]] = []
    packet_results: list[dict[str, Any]] = []

    for path in paths:
        try:
            packet = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            finding = _finding(
                "PACKET_JSON",
                "ERROR",
                f"Could not parse packet JSON: {exc}",
                f"/{path.name}",
            )
            packet_results.append(
                {
                    "source_file": _relative_name(path, packet_source),
                    "stage": mode,
                    "change_id": "",
                    "packet_id": "",
                    "packet_hash": "",
                    "packet_status": "",
                    "skeptic_status": "",
                    "status": "FAIL",
                    "error_count": 1,
                    "warning_count": 0,
                    "findings": [finding.as_dict()],
                }
            )
            continue
        if not isinstance(packet, dict):
            finding = _finding(
                "PACKET_JSON",
                "ERROR",
                "Packet JSON root is not an object.",
                f"/{path.name}",
            )
            packet_results.append(
                {
                    "source_file": _relative_name(path, packet_source),
                    "stage": mode,
                    "change_id": "",
                    "packet_id": "",
                    "packet_hash": "",
                    "packet_status": "",
                    "skeptic_status": "",
                    "status": "FAIL",
                    "error_count": 1,
                    "warning_count": 0,
                    "findings": [finding.as_dict()],
                }
            )
            continue
        change_id = str(packet.get("change_id", ""))
        if requested and change_id not in requested:
            continue
        packets.append(packet)
        source_input = inputs_by_change.get(change_id)
        stage = infer_stage(packet, path, mode)
        if source_input is None:
            findings = [
                _finding(
                    "INPUT_LINK",
                    "ERROR",
                    "Packet change ID is not present in the frozen input bundle.",
                    "/change_id",
                )
            ]
        else:
            findings = audit_one(
                packet,
                source_input=source_input,
                schema=schema,
                registry=registry,
                stage=stage,
            )
        packet_results.append(
            _packet_summary(
                packet=packet,
                source_name=_relative_name(path, packet_source),
                stage=stage,
                findings=findings,
            )
        )

    if requested:
        observed_requested = {
            str(packet.get("change_id")) for packet in packets
        }
        missing_requested = sorted(requested - observed_requested)
        if missing_requested:
            collection_findings.append(
                _finding(
                    "REQUESTED_PACKET_MISSING",
                    "ERROR",
                    "One or more requested packets were not found.",
                    "/packets",
                    missing=missing_requested,
                )
            )

    if require_complete is None:
        require_complete = packet_source.is_dir() and not requested
    observed_changes = [str(packet.get("change_id", "")) for packet in packets]
    observed_packet_ids = [str(packet.get("packet_id", "")) for packet in packets]
    for label, values in (
        ("change_id", observed_changes),
        ("packet_id", observed_packet_ids),
    ):
        duplicates = sorted(
            value for value, count in Counter(values).items() if value and count > 1
        )
        if duplicates:
            collection_findings.append(
                _finding(
                    "DUPLICATE_PACKET_ID",
                    "ERROR",
                    f"Duplicate packet {label} values found.",
                    "/packets",
                    field=label,
                    duplicates=duplicates,
                )
            )

    expected_changes = requested or set(inputs_by_change)
    if require_complete and set(observed_changes) != expected_changes:
        collection_findings.append(
            _finding(
                "PACKET_MEMBERSHIP",
                "ERROR",
                "Packet membership does not match the required frozen set.",
                "/packets",
                missing=sorted(expected_changes - set(observed_changes)),
                unexpected=sorted(set(observed_changes) - expected_changes),
            )
        )

    observed_stages = {
        result["stage"] for result in packet_results if result["stage"]
    }
    effective_mode = (
        next(iter(observed_stages))
        if len(observed_stages) == 1
        else ("mixed" if observed_stages else mode)
    )
    if effective_mode == "final" and not requested:
        collection_findings.extend(_index_findings(packet_source, packets))
    collection_findings = _dedupe_findings(collection_findings)

    packet_results.sort(
        key=lambda item: (
            item.get("change_id", ""),
            item.get("source_file", ""),
        )
    )
    error_count = sum(
        result["error_count"] for result in packet_results
    ) + sum(item.severity == "ERROR" for item in collection_findings)
    warning_count = sum(
        result["warning_count"] for result in packet_results
    ) + sum(item.severity == "WARNING" for item in collection_findings)
    status_counts = Counter(
        str(packet.get("packet_status", "")) for packet in packets
    )
    skeptic_counts = Counter(
        str(
            packet.get("skeptical_review", {}).get(
                "final_review_status", ""
            )
        )
        for packet in packets
    )
    code_counts = Counter(
        finding["code"]
        for result in packet_results
        for finding in result["findings"]
    )
    code_counts.update(finding.code for finding in collection_findings)
    return {
        "audit_version": "research_idea_packet_validator_v1",
        "status": "PASS" if error_count == 0 else "FAIL",
        "mode": effective_mode,
        "packet_count": len(packets),
        "passed_packet_count": sum(
            result["status"] == "PASS" for result in packet_results
        ),
        "failed_packet_count": sum(
            result["status"] == "FAIL" for result in packet_results
        ),
        "error_count": error_count,
        "warning_count": warning_count,
        "schema_sha256": sha256_file(schema_path),
        "registry_sha256": sha256_file(registry_path),
        "input_bundle_file_sha256": sha256_file(input_bundle_path),
        "input_membership_sha256": bundle.get("bundle_sha256"),
        "packet_status_counts": dict(sorted(status_counts.items())),
        "skeptic_status_counts": dict(sorted(skeptic_counts.items())),
        "finding_code_counts": dict(sorted(code_counts.items())),
        "collection_findings": [
            finding.as_dict() for finding in collection_findings
        ],
        "packets": packet_results,
    }


def summary_markdown(summary: dict[str, Any]) -> str:
    """Render the same audit summary as deterministic Markdown."""

    lines = [
        "# Research Idea Packet Validation",
        "",
        f"- Status: **{summary['status']}**",
        f"- Mode: `{summary['mode']}`",
        f"- Packets: {summary['packet_count']}",
        f"- Passed packets: {summary['passed_packet_count']}",
        f"- Failed packets: {summary['failed_packet_count']}",
        f"- Errors: {summary['error_count']}",
        f"- Warnings: {summary['warning_count']}",
        f"- Schema SHA-256: `{summary['schema_sha256']}`",
        f"- Input membership SHA-256: "
        f"`{summary['input_membership_sha256']}`",
        "",
        "## Packet results",
        "",
        "| Change ID | Stage | Packet status | Skeptic status | Result | Errors | Warnings |",
        "|---|---|---|---|---|---:|---:|",
    ]
    for packet in summary["packets"]:
        lines.append(
            "| {change_id} | {stage} | {packet_status} | {skeptic_status} "
            "| {status} | {error_count} | {warning_count} |".format(**packet)
        )
    all_findings = list(summary["collection_findings"])
    for packet in summary["packets"]:
        all_findings.extend(
            {
                **finding,
                "change_id": packet["change_id"],
            }
            for finding in packet["findings"]
        )
    lines.extend(["", "## Findings", ""])
    if not all_findings:
        lines.append("No findings.")
    else:
        for finding in all_findings:
            scope = finding.get("change_id") or "collection"
            lines.append(
                f"- **{finding['severity']} — {finding['code']}** "
                f"(`{scope}` `{finding['path']}`): {finding['message']}"
            )
    return "\n".join(lines) + "\n"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--packet-dir",
        type=Path,
        default=PACKET_DIR,
        help="Final packet directory or a single packet file",
    )
    source_group.add_argument(
        "--staging-dir",
        type=Path,
        help="Stage-one generator artifact directory (sets staging mode)",
    )
    parser.add_argument("--input-bundle", type=Path, default=INPUT_BUNDLE_PATH)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument(
        "--registry", type=Path, default=LANGUAGE_REGISTRY_PATH
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "staging", "final"),
        default="auto",
    )
    parser.add_argument("--change-id", action="append", default=[])
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Do not require full frozen-bundle membership",
    )
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-markdown", type=Path)
    parser.add_argument(
        "--stdout-format",
        choices=("json", "markdown"),
        default="json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    packet_source = args.staging_dir or args.packet_dir
    mode = "staging" if args.staging_dir else args.mode
    try:
        summary = validate_packet_set(
            packet_source,
            input_bundle_path=args.input_bundle,
            schema_path=args.schema,
            registry_path=args.registry,
            mode=mode,
            change_ids=args.change_id,
            require_complete=False if args.allow_partial else None,
        )
    except (OSError, json.JSONDecodeError, ValidationSetupError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    json_text = json.dumps(
        summary,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    markdown_text = summary_markdown(summary)
    if args.output_json:
        _write_text(args.output_json, json_text)
    if args.output_markdown:
        _write_text(args.output_markdown, markdown_text)
    print(
        markdown_text if args.stdout_format == "markdown" else json_text,
        end="",
    )
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
