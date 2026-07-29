#!/usr/bin/env python3
"""Build allowlisted public views from immutable Research Idea Engine V2 packets.

This script does not generate or modify research packets. It extracts a small,
public-safe presentation contract from three frozen packets and compact status
metadata from the other five bounded cases.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "research_idea_packets" / "v2"
V1_SOURCE_DIR = ROOT / "data" / "research_idea_packets" / "v1"
OUTPUT_DIR = ROOT / "demo" / "data" / "research_ideas" / "v2"
DISCLAIMER = (
    "Experimental feature: These are AI-generated research hypotheses grounded "
    "in cited filing evidence. They are not facts, personalized investment "
    "advice, or validated trading signals. Analyst review is required."
)
SOURCE_IDS = {
    "RH": "412b08746bb0ed5a7745",
    "DVN": "4784f62ad001b2a12af4",
    "EFX": "279e7d4e407851a19548",
}
SAFE_FAILURE_ORDER = ["EFX", "CHE", "DLTR", "FCX", "KHC", "TFC"]
PUBLIC_ROUTES = {
    "RH": "research_idea_rh.html",
    "DVN": "research_idea_dvn.html",
    "EFX": "research_idea_efx.html",
}
EDITORIAL_TITLES = {
    "RH": "Does the expanded data-risk language reflect issuer-specific control changes?",
    "DVN": "How durable is the disclosed reduction in near-term impairment risk?",
}
POSSIBLE_DRIVERS = {
    "RH": "Data-security controls, compliance activity, and related operating costs",
    "DVN": "Commodity-price assumptions and oil-and-gas asset recoverability",
}


def load_packet(change_id: str) -> dict[str, Any]:
    return json.loads(
        (SOURCE_DIR / f"{change_id}.json").read_text(encoding="utf-8")
    )


def load_v1_evidence(change_id: str) -> dict[str, Any]:
    packet = json.loads(
        (V1_SOURCE_DIR / f"{change_id}.json").read_text(encoding="utf-8")
    )
    return packet["evidence"]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def compact_evidence(span: Any) -> Any:
    if not isinstance(span, dict):
        return span
    allowed = (
        "evidence_id",
        "source_type",
        "document_id",
        "filing_date",
        "acceptance_timestamp",
        "section",
        "paragraph_number",
        "start_offset",
        "end_offset",
        "outside_display_excerpt",
        "point_in_time_eligible",
        "text",
        "text_sha256",
    )
    return {key: span.get(key) for key in allowed if key in span}


def public_claim(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "proposition_id": claim["proposition_id"],
        "wording": claim["exact_wording"],
        "claim_type": claim["claim_type"],
        "support_status": claim["support_status"],
        "confidence": claim["confidence"],
        "novelty_status": claim["novelty_status"],
        "final_disposition": claim["final_disposition"],
        "evidence_ids": claim["source_evidence_ids"],
    }


def public_quantity(quantity: dict[str, Any]) -> dict[str, Any]:
    return {
        "raw_text": quantity["raw_text"],
        "currency": quantity["currency"],
        "scale": quantity["scale"],
        "role": quantity["financial_role"],
        "date": quantity["date"],
        "conditionality": quantity["conditionality"],
        "payment_status": quantity["payment_status"],
        "gross_net_basis": quantity["gross_net_basis"],
        "historical_current": quantity["historical_current"],
        "evidence_id": quantity["evidence_id"],
    }


def public_hypothesis(packet: dict[str, Any]) -> dict[str, Any]:
    source = packet["research_hypotheses"][0]
    ticker = packet["ticker"]
    return {
        "hypothesis_id": source["hypothesis_id"],
        "title": EDITORIAL_TITLES[ticker],
        "label": "AI-GENERATED RESEARCH HYPOTHESIS",
        "hypothesis": source["hypothesis"],
        "testable_prediction": source["testable_prediction"],
        "expected_direction": "Not specified in the frozen packet",
        "time_horizon": "Not specified in the frozen packet",
        "unit_of_analysis": "Not separately specified in the frozen packet",
        "required_data": source["required_data"],
        "confirmation_conditions": source["confirmation_conditions"],
        "falsification_conditions": source["falsification_conditions"],
        "confounders": [
            packet["skeptic_review"]["opposite_interpretation"],
            "Peer boilerplate or a presentation-only wording change",
        ],
        "grounding_score": "Not separately scored",
        "testability_score": "Not separately scored",
        "support_status": source["support_status"],
        "evidence_ids": source["evidence_ids"],
        "future_outcome_validation": "NOT_PERFORMED",
    }


def public_publishable_packet(packet: dict[str, Any]) -> dict[str, Any]:
    ticker = packet["ticker"]
    evidence = packet["source_evidence"]
    display_evidence = load_v1_evidence(packet["change_id"])
    claims = [public_claim(claim) for claim in packet["atomic_claims"]]
    facts = [claim for claim in claims if claim["claim_type"] == "fact"]
    inferences = [
        claim
        for claim in claims
        if claim["claim_type"] in {"interpretation", "hypothesis"}
    ]
    earliest = compact_evidence(evidence["earliest_occurrence"])
    related_prior = [
        compact_evidence(span)
        for span in evidence["additional_prior_evidence"]
        if span.get("source_type") in {"SEC_8_K", "NEWS_HEADLINE"}
    ]
    return {
        "public_schema_version": "1.0",
        "public_safe": True,
        "kind": "publishable_hypothesis",
        "feature_name": "Experimental Research Idea Engine",
        "experimental_disclaimer": DISCLAIMER,
        "human_review_status": (
            "Independent evidence review and automated grounding checks completed. "
            "Formal blinded human ratings remain pending."
        ),
        "identity": {
            "issuer": packet["issuer"],
            "ticker": ticker,
            "change_id": packet["change_id"],
            "filing_date": packet["filing_date"],
            "section": packet["section"],
            "category": packet["provisional_classification"]["category"],
            "direction": packet["provisional_classification"]["direction"],
            "sec_url": packet["source_url"],
        },
        "source_packet": {
            "packet_id": packet["packet_id"],
            "packet_version": packet["packet_version"],
            "packet_hash": packet["packet_hash"],
            "file_sha256": file_sha256(
                SOURCE_DIR / f"{packet['change_id']}.json"
            ),
            "status": packet["packet_status"],
            "immutable": True,
        },
        "publication": {
            "evidence_coverage_ratio": packet["evidence_coverage"][
                "evidence_coverage_ratio"
            ],
            "skeptic_status": packet["skeptic_review"]["status"],
            "hypothesis_count": len(packet["research_hypotheses"]),
            "trade_readiness": packet["illustrative_trade_hypothesis"]["status"],
            "analyst_review_required": True,
        },
        "source_evidence": {
            "prior_excerpt": evidence["prior_excerpt"],
            "current_excerpt": evidence["current_excerpt"],
            "added_text": display_evidence["added_text"],
            "removed_text": display_evidence["removed_text"],
            "display_evidence_ids": display_evidence["evidence_ids"],
            "display_evidence_offsets": display_evidence["evidence_offsets"],
            "display_evidence_offsets_verified": display_evidence[
                "evidence_offsets_verified"
            ],
            "prior_sec_url": display_evidence["prior_source_url"],
            "earliest_occurrence": earliest,
            "related_prior_8k": display_evidence["related_prior_8k"],
            "related_prior_news": display_evidence["related_prior_news"],
            "additional_prior_evidence_metadata": related_prior,
            "full_prior_filing_evidence_checked": packet["retrieval_metadata"][
                "full_prior_filing_search_completed"
            ],
            "documents_searched": packet["retrieval_metadata"][
                "documents_searched"
            ],
            "sections_searched": packet["retrieval_metadata"]["sections_searched"],
            "timing_violations": packet["retrieval_metadata"]["timing_violations"],
        },
        "novelty": {
            **packet["novelty_review"],
            "related_prior_8k_count": sum(
                span.get("source_type") == "SEC_8_K" for span in related_prior
            ),
            "related_prior_news_count": sum(
                span.get("source_type") == "NEWS_HEADLINE"
                for span in related_prior
            ),
            "unresolved_uncertainty": packet["retrieval_metadata"][
                "unresolved_gaps"
            ],
        },
        "interpretation_layers": {
            "facts": facts,
            "inferences": inferences,
            "uncertainties": [
                packet["skeptic_review"]["opposite_interpretation"],
                "The frozen packet does not establish a market effect.",
            ],
        },
        "economic_mechanism": {
            "label": "POSSIBLE MECHANISM — NOT ESTABLISHED FACT",
            "affected_financial_driver": POSSIBLE_DRIVERS[ticker],
            "proposed_causal_chain": packet["research_hypotheses"][0]["mechanism"],
            "supporting_evidence_ids": packet["research_hypotheses"][0][
                "evidence_ids"
            ],
            "counterargument": packet["skeptic_review"][
                "opposite_interpretation"
            ],
            "confidence": "Not separately scored in the frozen packet",
        },
        "research_hypotheses": [public_hypothesis(packet)],
        "financial_quantities": [
            public_quantity(quantity)
            for quantity in packet["financial_quantities"]
        ],
        "affected_entities_and_instruments": {
            "grounded_relationships": [],
            "status": "No grounded instrument relationship was established.",
        },
        "scenarios": {
            "status": "Not produced by the frozen bounded packet",
            "disclaimer": "Scenarios are structured research frames, not forecasts.",
            "bull": None,
            "base": None,
            "bear": None,
        },
        "trade_research": {
            "status": "NO_ACTIONABLE_TRADE_VIEW",
            "candidate_bias": packet["illustrative_trade_hypothesis"][
                "candidate_view"
            ],
            "instrument_class": packet["illustrative_trade_hypothesis"][
                "instrument"
            ],
            "missing_market_checks": packet["illustrative_trade_hypothesis"][
                "required_market_checks"
            ],
            "readiness_failure_reason": packet["skeptic_review"]["instrument_fit"],
            "research_only": True,
        },
        "skeptical_review": {
            "strongest_objections": packet["skeptic_review"]["objections"],
            "alternate_explanation": packet["skeptic_review"][
                "opposite_interpretation"
            ],
            "unsupported_claims_removed": [
                "Unsupported V1 causal extensions were removed before publication."
            ],
            "counterevidence_effect": {
                "novelty": packet["counterevidence_review"]["effect_on_novelty"],
                "mechanism": packet["counterevidence_review"][
                    "effect_on_mechanism"
                ],
                "trade_hypothesis": packet["counterevidence_review"][
                    "effect_on_trade_hypothesis"
                ],
            },
            "final_status": packet["skeptic_review"]["status"],
        },
    }


def find_evidence(packet: dict[str, Any], evidence_id: str) -> dict[str, Any]:
    stack: list[Any] = [packet]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if current.get("evidence_id") == evidence_id and "text" in current:
                return compact_evidence(current)
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    raise KeyError(evidence_id)


def public_efx_rejection(packet: dict[str, Any]) -> dict[str, Any]:
    evidence_ids = {
        "prior_top_up": "evidence-index-v2:000003318520000011:paragraph-00470",
        "settlement_finality": (
            "evidence-index-v2:000003318522000014:paragraph-00434"
        ),
        "deposit_made": "evidence-index-v2:000003318522000014:paragraph-01732",
    }
    return {
        "public_schema_version": "1.0",
        "public_safe": True,
        "kind": "grounding_rejection",
        "feature_name": "Experimental Research Idea Engine",
        "title": "When the Evidence Rejects the Idea",
        "experimental_disclaimer": DISCLAIMER,
        "human_review_status": (
            "Independent evidence review and automated grounding checks completed. "
            "Formal blinded human ratings remain pending."
        ),
        "identity": {
            "issuer": packet["issuer"],
            "ticker": packet["ticker"],
            "change_id": packet["change_id"],
            "filing_date": packet["filing_date"],
            "section": packet["section"],
            "sec_url": packet["source_url"],
        },
        "source_packet": {
            "packet_id": packet["packet_id"],
            "packet_hash": packet["packet_hash"],
            "file_sha256": file_sha256(
                SOURCE_DIR / f"{packet['change_id']}.json"
            ),
            "status": packet["packet_status"],
            "immutable": True,
        },
        "rejected_v1_interpretation": {
            "label": "REJECTED V1 INTERPRETATION",
            "defects": [
                "The selected prior excerpt omitted relevant language.",
                "The $125 million conditional top-up appeared falsely new.",
                "The $346.7 million remaining balance was misread as an exposure cap.",
                "Unsupported liquidity, reserve, and bondholder mechanisms followed.",
            ],
        },
        "full_prior_evidence_review": {
            "full_prior_filing_evidence_checked": True,
            "prior_top_up_evidence": find_evidence(
                packet, evidence_ids["prior_top_up"]
            ),
            "settlement_finality_evidence": find_evidence(
                packet, evidence_ids["settlement_finality"]
            ),
            "deposit_evidence": find_evidence(
                packet, evidence_ids["deposit_made"]
            ),
            "quantity_roles": [
                {
                    "amount": "$125M",
                    "correct_role": "Conditional top-up",
                    "novelty_result": "PREVIOUSLY_DISCLOSED_IN_10K",
                },
                {
                    "amount": "$346.7M",
                    "correct_role": "Remaining payment balance",
                    "novelty_result": "Not an exposure cap",
                },
                {
                    "amount": "~$345M",
                    "correct_role": "Cash deposit",
                    "novelty_result": "Current-period settlement update",
                },
            ],
            "comparison_status": "INCOMPARABLE_QUANTITIES",
        },
        "final_result": {
            "defensible_update": [
                "Settlement finality",
                "Approximately $345 million cash deposit",
            ],
            "rejected_claims": [
                "Reserve inadequacy",
                "Current liquidity stress",
                "Bondholder impact",
            ],
            "packet_disposition": packet["packet_status"],
            "skeptic_status": packet["skeptic_review"]["status"],
            "trade_research_status": "NO_ACTIONABLE_TRADE_VIEW",
        },
        "value_statement": (
            "The engine’s value is not generating more ideas. It is preventing "
            "unsupported ideas from reaching the analyst."
        ),
    }


def safe_failure_reason(packet: dict[str, Any]) -> str:
    objections = packet["skeptic_review"].get("objections") or []
    if objections:
        return objections[0]
    status = packet["skeptic_review"]["status"]
    reasons = {
        "REJECT_PREVIOUSLY_DISCLOSED": (
            "The claimed novelty was already present in eligible prior disclosure."
        ),
        "REJECT_UNSUPPORTED_MECHANISM": (
            "The evidence did not support the proposed economic mechanism."
        ),
    }
    return reasons.get(status, "The packet did not clear the grounding gate.")


def main() -> None:
    packets = {
        packet["ticker"]: packet
        for packet in (
            load_packet(path.stem)
            for path in sorted(SOURCE_DIR.glob("*.json"))
            if path.name != "index.json"
        )
    }
    outputs = {
        "rh.json": public_publishable_packet(packets["RH"]),
        "dvn.json": public_publishable_packet(packets["DVN"]),
        "efx_rejection.json": public_efx_rejection(packets["EFX"]),
    }
    for filename, payload in outputs.items():
        write_json(OUTPUT_DIR / filename, payload)

    files = {
        filename: {
            "sha256": file_sha256(OUTPUT_DIR / filename),
            "source_packet_hash": payload["source_packet"]["packet_hash"],
            "source_packet_file_sha256": payload["source_packet"]["file_sha256"],
        }
        for filename, payload in outputs.items()
    }
    safe_failures = []
    for ticker in SAFE_FAILURE_ORDER:
        packet = packets[ticker]
        safe_failures.append(
            {
                "ticker": ticker,
                "issuer": packet["issuer"],
                "change_id": packet["change_id"],
                "final_status": packet["packet_status"],
                "skeptic_status": packet["skeptic_review"]["status"],
                "reason": safe_failure_reason(packet),
                "published_packet": False,
                "actionable_trade_view": False,
                "route": PUBLIC_ROUTES.get(ticker),
            }
        )
    manifest = {
        "manifest_version": "1.0",
        "feature_name": "Experimental Research Idea Engine",
        "source_version": "Research Idea Engine V2",
        "source_commit": "093c4d80ef1d4e475a1c608131a1e3ab571bc48f",
        "frozen": True,
        "new_packet_generation_performed": False,
        "experimental_disclaimer": DISCLAIMER,
        "human_review_status": (
            "Independent evidence review and automated grounding checks completed. "
            "Formal blinded human ratings remain pending."
        ),
        "summary": {
            "cases_reviewed": 8,
            "publishable_hypotheses": 2,
            "safe_failures": 6,
            "actionable_trade_views": 0,
            "published_packet_evidence_coverage_ratio": 1.0,
            "broader_generation": "BLOCKED",
        },
        "selectivity_statement": (
            "The engine is designed to reject unsupported stories rather than "
            "generate an idea for every disclosure."
        ),
        "publishable": [
            {
                "ticker": ticker,
                "issuer": packets[ticker]["issuer"],
                "change_id": packets[ticker]["change_id"],
                "filing_date": packets[ticker]["filing_date"],
                "section": packets[ticker]["section"],
                "category": packets[ticker]["provisional_classification"][
                    "category"
                ],
                "final_novelty": packets[ticker]["novelty_review"][
                    "final_novelty"
                ],
                "evidence_coverage_ratio": 1.0,
                "skeptic_status": "PASS_HYPOTHESIS_ONLY",
                "hypothesis_count": 1,
                "trade_readiness": "NO_ACTIONABLE_TRADE_VIEW",
                "route": PUBLIC_ROUTES[ticker],
            }
            for ticker in ("RH", "DVN")
        ],
        "safe_failures": safe_failures,
        "public_files": files,
        "excluded_content": [
            "private reviewer notes",
            "local filesystem paths",
            "unpublished speculative claims",
            "licensed article bodies",
            "future outcomes",
            "hidden reasoning traces",
        ],
    }
    write_json(OUTPUT_DIR / "manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": "PASS",
                "output_directory": "demo/data/research_ideas/v2",
                "public_files": {
                    **files,
                    "manifest.json": {
                        "sha256": file_sha256(OUTPUT_DIR / "manifest.json")
                    },
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
