#!/usr/bin/env python3
"""Validate V2 packets, preservation controls, and scale/publication gates."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = ROOT / "data" / "research_idea_packets" / "v2"
PUBLIC_PACKET_DIR = ROOT / "demo" / "data" / "research_idea_packets" / "v2"
INDEX_DIR = ROOT / "data" / "research_idea_evidence_index" / "v2"
START_RECEIPT = ROOT / "artifacts" / "research_idea_engine_v2_start_receipt.json"
INDEX_RECEIPT = ROOT / "artifacts" / "research_idea_evidence_index_v2_receipt.json"
OUTPUT_PATH = ROOT / "artifacts" / "research_idea_engine_v2_validation.json"
REPORT_PATH = ROOT / "reports" / "research_idea_v2_grounding_audit.md"
PACKET_SCHEMA = ROOT / "schemas" / "research_idea_packet_v2.schema.json"
ATOMIC_SCHEMA = ROOT / "schemas" / "atomic_evidence_claim_v2.schema.json"

FUTURE_KEYS = {
    "outcome",
    "later_return",
    "abnormal_return_6m",
    "abnormal_return_12m",
    "maximum_drawdown_12m",
    "realized_volatility_12m",
    "future_filing",
    "post_filing_news",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def packet_hash(packet: dict[str, Any]) -> str:
    copy_packet = copy.deepcopy(packet)
    copy_packet["packet_hash"] = "0" * 64
    return hashlib.sha256(canonical_json(copy_packet).encode("utf-8")).hexdigest()


def iter_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from iter_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_keys(child)


def validator() -> Draft202012Validator:
    packet_schema = json.loads(PACKET_SCHEMA.read_text(encoding="utf-8"))
    packet_schema["properties"]["atomic_claims"]["items"] = json.loads(
        ATOMIC_SCHEMA.read_text(encoding="utf-8")
    )
    return Draft202012Validator(packet_schema, format_checker=FormatChecker())


def validate_efx(packet: dict[str, Any], diagnostic: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    top_up_claims = [
        item for item in packet["atomic_claims"] if "$125 million" in item["exact_wording"]
    ]
    if not top_up_claims:
        errors.append("EFX missing $125 million atomic claim")
    else:
        claim = top_up_claims[0]
        if claim["novelty_status"] != "PREVIOUSLY_DISCLOSED_IN_10K":
            errors.append("EFX $125 million novelty is not PREVIOUSLY_DISCLOSED_IN_10K")
        if (
            claim["novelty_review"].get("display_excerpt_status")
            != "DISPLAY_EXCERPT_OMITTED_PRIOR_EVIDENCE"
        ):
            errors.append("EFX omitted-display defect is not recorded")
    role_by_amount = {
        item.get("normalized_amount"): item["financial_role"]
        for item in packet["financial_quantities"]
    }
    if role_by_amount.get(346700000.0) != "remaining balance":
        errors.append("EFX $346.7 million is not a remaining balance")
    if "cash deposit" not in {
        item["financial_role"]
        for item in packet["financial_quantities"]
        if item.get("normalized_amount") == 345000000.0
    }:
        errors.append("EFX approximately $345 million cash deposit is missing")
    if role_by_amount.get(125000000.0) != "conditional top-up":
        errors.append("EFX $125 million is not a conditional top-up")
    quantity_by_id = {
        item["quantity_id"]: item for item in packet["financial_quantities"]
    }
    incompatible_346_125 = False
    for comparison in packet["quantity_comparisons"]:
        left = quantity_by_id.get(comparison["left_quantity_id"], {})
        right = quantity_by_id.get(comparison["right_quantity_id"], {})
        amounts = {left.get("normalized_amount"), right.get("normalized_amount")}
        if {346700000.0, 125000000.0}.issubset(amounts):
            incompatible_346_125 = (
                comparison["status"] == "INCOMPARABLE_QUANTITIES"
            )
            break
    if not incompatible_346_125:
        errors.append("EFX $346.7 million / $125 million comparison is not blocked")
    if packet["packet_status"] != "REJECT_MISLEADING_COMPARISON":
        errors.append("EFX packet did not reject the misleading comparison")
    if (
        packet["novelty_review"]["final_novelty"]
        != "RESOLVED_OR_FINALIZED_PRIOR_UNCERTAINTY"
    ):
        errors.append("EFX defensible finality update is missing")
    if packet["illustrative_trade_hypothesis"]["candidate_view"] != "no actionable view":
        errors.append("EFX generated an actionable view")
    removed_text = " ".join(
        item["claim"]
        for item in diagnostic["atomic_claim_reviews"]
        if item["final_disposition"].startswith("REMOVE")
    ).lower()
    for marker in ("liquidity", "bondholder"):
        if marker not in removed_text:
            errors.append(f"EFX unsupported {marker} claim was not removed")
    return errors


def validate() -> dict[str, Any]:
    start = json.loads(START_RECEIPT.read_text(encoding="utf-8"))
    index_receipt = json.loads(INDEX_RECEIPT.read_text(encoding="utf-8"))
    schema_validator = validator()
    errors: list[str] = []
    warnings: list[str] = []
    v1_preservation: dict[str, bool] = {}
    for change_id, expected in start["v1_packet_hashes"].items():
        path = ROOT / "data" / "research_idea_packets" / "v1" / f"{change_id}.json"
        v1_preservation[change_id] = sha256_file(path) == expected
    if not all(v1_preservation.values()):
        errors.append("One or more V1 packets changed")
    protected_files = {
        **start["efx_review_hashes"],
        **{
            path: expected
            for path, expected in start["frozen_source_data_hashes"].items()
            if "/" in path
        },
    }
    protected_results: dict[str, bool] = {}
    for relative, expected in protected_files.items():
        path = ROOT / relative
        protected_results[relative] = path.exists() and sha256_file(path) == expected
    if not all(protected_results.values()):
        errors.append("A protected EFX or frozen-source artifact changed")
    if index_receipt["failed_extraction_count"]:
        errors.append("Evidence index contains failed extractions")
    if index_receipt["timing_violation_count"]:
        errors.append("Evidence index contains timing violations")
    packet_paths = sorted(
        path for path in PACKET_DIR.glob("*.json") if path.name != "index.json"
    )
    if len(packet_paths) != 8:
        errors.append(f"Expected eight V2 packets, found {len(packet_paths)}")
    packets: list[dict[str, Any]] = []
    packet_results: list[dict[str, Any]] = []
    for path in packet_paths:
        packet = json.loads(path.read_text(encoding="utf-8"))
        schema_errors = [
            f"{'/'.join(map(str, error.absolute_path))}: {error.message}"
            for error in schema_validator.iter_errors(packet)
        ]
        if schema_errors:
            errors.extend(f"{packet.get('ticker', path.stem)} {item}" for item in schema_errors)
        if packet_hash(packet) != packet["packet_hash"]:
            errors.append(f"{packet['ticker']} packet hash mismatch")
        public_path = PUBLIC_PACKET_DIR / path.name
        if not public_path.exists() or path.read_bytes() != public_path.read_bytes():
            errors.append(f"{packet['ticker']} archive/public packet mismatch")
        future = sorted(set(iter_keys(packet)) & FUTURE_KEYS)
        if future:
            errors.append(f"{packet['ticker']} future keys present: {future}")
        if not packet["retrieval_metadata"]["full_prior_filing_search_completed"]:
            errors.append(f"{packet['ticker']} lacks full-prior search")
        factual = [
            item for item in packet["atomic_claims"] if item["claim_type"] == "fact"
        ]
        expected_ratio = (
            sum(item["support_status"] == "SUPPORTED" for item in factual) / len(factual)
            if factual
            else 1.0
        )
        if abs(expected_ratio - packet["evidence_coverage"]["evidence_coverage_ratio"]) > 1e-6:
            errors.append(f"{packet['ticker']} evidence coverage ratio is inconsistent")
        if packet["packet_status"] == "PUBLISHABLE":
            coverage = packet["evidence_coverage"]
            if (
                coverage["evidence_coverage_ratio"] != 1.0
                or coverage["contradicted_factual_claims"]
                or coverage["unresolved_critical_numeric_role_conflicts"]
                or coverage["missing_counterevidence_searches"]
                or packet["skeptic_review"]["status"]
                not in {"PASS_GROUNDED", "PASS_HYPOTHESIS_ONLY"}
            ):
                errors.append(f"{packet['ticker']} violates publication gates")
        packets.append(packet)
        packet_results.append(
            {
                "change_id": packet["change_id"],
                "ticker": packet["ticker"],
                "packet_status": packet["packet_status"],
                "skeptic_status": packet["skeptic_review"]["status"],
                "evidence_coverage_ratio": packet["evidence_coverage"][
                    "evidence_coverage_ratio"
                ],
                "packet_hash": packet["packet_hash"],
            }
        )
    if len({packet["change_id"] for packet in packets}) != len(packets):
        errors.append("Duplicate V2 change IDs")
    efx = next((packet for packet in packets if packet["ticker"] == "EFX"), None)
    if efx:
        diagnostic = json.loads(
            (
                ROOT
                / "reports"
                / "v2_case_retrieval_diagnostics"
                / f"{efx['change_id']}.json"
            ).read_text(encoding="utf-8")
        )
        errors.extend(validate_efx(efx, diagnostic))
    else:
        errors.append("EFX packet missing")
    publishable = [packet for packet in packets if packet["packet_status"] == "PUBLISHABLE"]
    grounded_hypotheses = sum(len(packet["research_hypotheses"]) for packet in publishable)
    no_action_views = sum(
        packet["illustrative_trade_hypothesis"]["candidate_view"] == "no actionable view"
        for packet in packets
    )
    critical_published_defects = sum(
        not packet["evidence_coverage"]["publication_gate_passed"]
        for packet in publishable
    )
    eight_case_gate = (
        "READY_FOR_PUBLIC_DEMO"
        if (
            publishable
            and grounded_hypotheses >= 1
            and no_action_views >= 1
            and critical_published_defects == 0
            and not errors
        )
        else "HOLD_GROUNDING"
    )
    sixty_case_gate = (
        "READY_FOR_BOUNDED_60_CASE_REVIEW"
        if len(publishable) >= 6 and critical_published_defects == 0 and not errors
        else "BLOCKED"
    )
    result = {
        "validation_version": "2.0",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "packet_count": len(packets),
        "publishable_packet_count": len(publishable),
        "publishable_tickers": [packet["ticker"] for packet in publishable],
        "grounded_hypothesis_count": grounded_hypotheses,
        "no_action_view_count": no_action_views,
        "critical_published_defects": critical_published_defects,
        "eight_case_gate": eight_case_gate,
        "sixty_case_gate": sixty_case_gate,
        "deployment_authorized": False,
        "v1_preservation": v1_preservation,
        "protected_artifact_preservation": protected_results,
        "packets": packet_results,
    }
    OUTPUT_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    REPORT_PATH.write_text(
        "# Research Idea Engine V2 grounding audit\n\n"
        f"**Result: {result['status']} · {eight_case_gate} · 60-case phase {sixty_case_gate}.**\n\n"
        f"- V2 packets: {len(packets)}\n"
        f"- Publishable hypothesis-only packets: {len(publishable)} "
        f"({', '.join(result['publishable_tickers']) or 'none'})\n"
        f"- Grounded research hypotheses: {grounded_hypotheses}\n"
        f"- No-action views: {no_action_views}\n"
        f"- Critical defects in published packets: {critical_published_defects}\n"
        f"- Evidence-index extraction failures: {index_receipt['failed_extraction_count']}\n"
        f"- Evidence-index timing violations: {index_receipt['timing_violation_count']}\n"
        f"- V1 preservation: {'PASS' if all(v1_preservation.values()) else 'FAIL'}\n\n"
        "The public GitHub Pages deployment remains unchanged and is not authorized "
        "by this validation. Human ratings remain blank.\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    result = validate()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
