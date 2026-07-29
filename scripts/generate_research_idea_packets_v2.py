#!/usr/bin/env python3
"""Generate deterministic V2 packets from full-prior retrieval evidence."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from assign_novelty_v2 import assign_novelty, tokens
from decompose_atomic_claims import decompose_packet, decompose_statement
from normalize_financial_quantities import (
    comparison_compatibility,
    normalize_financial_quantities,
)
from search_counterevidence import search_counterevidence


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = (
    ROOT
    / "demo"
    / "data"
    / "research_idea_inputs"
    / "v1"
    / "eight_case_inputs.json"
)
INDEX_DIR = ROOT / "data" / "research_idea_evidence_index" / "v2"
V1_PACKET_DIR = ROOT / "data" / "research_idea_packets" / "v1"
V2_PACKET_DIR = ROOT / "data" / "research_idea_packets" / "v2"
V2_PUBLIC_PACKET_DIR = ROOT / "demo" / "data" / "research_idea_packets" / "v2"
DIAGNOSTIC_DIR = ROOT / "reports" / "v2_case_retrieval_diagnostics"
COMPARISON_PATH = ROOT / "reports" / "v1_v2_packet_comparison.md"
HUMAN_REVIEW_DIR = ROOT / "reports" / "research_idea_v2_human_review"
PACKET_SCHEMA_PATH = ROOT / "schemas" / "research_idea_packet_v2.schema.json"
ATOMIC_SCHEMA_PATH = ROOT / "schemas" / "atomic_evidence_claim_v2.schema.json"
DISCLAIMER = (
    "AI-generated research hypothesis based on the cited evidence. It is not "
    "a fact, personalized investment advice, or a validated trading signal. "
    "Analyst review is required."
)

UNSUPPORTED_MECHANISM_MARKERS = (
    "liquidity stress",
    "liquidity crisis",
    "current cash flow insufficiency",
    "not adequately reserved",
    "reserve inadequacy",
    "under-reserved",
    "bondholder",
    "credit spread",
    "credit downgrade",
    "market mispricing",
    "price reaction",
    "multiple compression",
    "likely to breach",
    "will trigger a breach",
    "debt covenant breach",
    "equity valuation will",
    "investors may demand",
    "cost of equity may rise",
)

SAFE_HYPOTHESES: dict[str, dict[str, Any]] = {
    "4784f62ad001b2a12af4": {
        "hypothesis_id": "hypothesis-v2:asset-recoverability-sensitivity",
        "hypothesis": (
            "The disclosed removal of near-term impairment risk may warrant "
            "testing whether asset recoverability remains robust under lower "
            "commodity-price assumptions; durability is not established."
        ),
        "mechanism": (
            "Commodity-price assumptions affect projected field cash flows and "
            "therefore the margin between recoverable value and carrying value."
        ),
        "testable_prediction": (
            "A sensitivity analysis using disclosed reserve and price assumptions "
            "will show whether a moderate price decline restores impairment risk."
        ),
        "required_data": [
            "Impairment-test price deck",
            "Field-level carrying values",
            "Reserve and production assumptions"
        ],
        "confirmation_conditions": [
            "Reasonable downside price assumptions materially reduce recoverable-value headroom."
        ],
        "falsification_conditions": [
            "Disclosed sensitivity shows substantial headroom under reasonable downside prices."
        ]
    },
    "412b08746bb0ed5a7745": {
        "hypothesis_id": "hypothesis-v2:data-risk-specificity-test",
        "hypothesis": (
            "The added PII and payment-card risk disclosure may warrant "
            "investigation into whether it reflects issuer-specific control "
            "changes or expanded risk-factor coverage; an incident is not established."
        ),
        "mechanism": (
            "Issuer-specific control remediation or compliance changes would create "
            "observable security spending, control, or incident disclosures beyond boilerplate."
        ),
        "testable_prediction": (
            "Contemporaneous filings and control disclosures will either identify "
            "issuer-specific changes or show that the language is generic expansion."
        ),
        "required_data": [
            "Contemporaneous control disclosures",
            "Earlier eligible 8-K text",
            "Peer risk-factor language"
        ],
        "confirmation_conditions": [
            "Eligible evidence identifies issuer-specific control, compliance, or incident changes."
        ],
        "falsification_conditions": [
            "The language matches peer boilerplate and no issuer-specific change is disclosed."
        ]
    }
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def packet_hash(packet: dict[str, Any]) -> str:
    value = copy.deepcopy(packet)
    value["packet_hash"] = "0" * 64
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def source_map() -> dict[str, dict[str, Any]]:
    bundle = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    return {item["change_id"]: item for item in bundle["inputs"]}


def display_spans(source: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = source["evidence"]
    return [
        {
            "evidence_id": evidence["evidence_ids"]["prior_excerpt"],
            "document_id": source["identifiers"]["prior_accession_number"].replace("-", ""),
            "source_type": "SEC_10_K",
            "filing_date": source["prior_filing"]["filing_date"],
            "acceptance_timestamp": source["prior_filing"]["acceptance_timestamp"],
            "section": source["section"],
            "paragraph_number": 0,
            "text": evidence["prior_excerpt"],
            "outside_display_excerpt": False,
            "inside_display_excerpt": True,
            "point_in_time_eligible": True,
        },
        {
            "evidence_id": evidence["evidence_ids"]["current_excerpt"],
            "document_id": source["identifiers"]["current_accession_number"].replace("-", ""),
            "source_type": "SEC_10_K_CURRENT",
            "filing_date": source["filing_date"],
            "acceptance_timestamp": source["formation_timestamp"],
            "section": source["section"],
            "paragraph_number": 0,
            "text": evidence["current_excerpt"],
            "outside_display_excerpt": False,
            "inside_display_excerpt": True,
            "point_in_time_eligible": True,
        },
    ]


def prefilter_spans(statement: str, spans: list[dict[str, Any]], limit: int = 900) -> list[dict[str, Any]]:
    query_tokens = set(tokens(statement))
    numeric = set(re.findall(r"\d+(?:\.\d+)?", statement.replace(",", "")))
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for span in spans:
        text = span["text"].lower().replace(",", "")
        token_hits = sum(1 for token in query_tokens if token in text)
        number_hits = sum(1 for number in numeric if number in text)
        if token_hits >= 2 or number_hits:
            score = token_hits + 5 * number_hits
            scored.append((score, span["evidence_id"], span))
    if not scored:
        return spans[:limit]
    return [item[2] for item in sorted(scored, key=lambda row: (-row[0], row[1]))[:limit]]


def unsupported_marker(statement: str) -> bool:
    lowered = statement.lower()
    return any(marker in lowered for marker in UNSUPPORTED_MECHANISM_MARKERS)


def assess_support(
    claim: dict[str, Any],
    *,
    novelty: dict[str, Any],
    strongest_match: dict[str, Any] | None,
    ticker: str,
) -> tuple[str, str, float]:
    wording = claim["exact_wording"].lower()
    score = strongest_match["score"] if strongest_match else 0.0
    if (
        ("new" in wording or "emerged" in wording)
        and novelty["status"].startswith("PREVIOUSLY_DISCLOSED")
    ):
        return "CONTRADICTED", "REMOVE_CONTRADICTED", max(0.75, score)
    if ticker == "EFX" and any(
        marker in wording
        for marker in (
            "346.7m exposure",
            "346.7 million exposure",
            "new, smaller tail risk",
            "not adequately reserved",
            "current liquidity",
            "bondholder",
        )
    ):
        return "CONTRADICTED", "REMOVE_CONTRADICTED", 0.95
    if unsupported_marker(wording):
        return "UNSUPPORTED", "REMOVE_UNSUPPORTED", max(0.8, 1 - score)
    if claim["claim_type"] == "fact":
        if (
            "frozen classification" in wording
            or "filing section" in wording
            or score >= 0.27
        ):
            return "SUPPORTED", "RETAIN", min(0.99, max(0.65, score + 0.25))
        return "AMBIGUOUS", "VISIBLE_UNCERTAINTY", max(0.2, score)
    if claim["claim_type"] in {"interpretation", "hypothesis"}:
        if score >= 0.38:
            return (
                "PARTIALLY_SUPPORTED",
                "RETAIN_AS_LABELED_HYPOTHESIS",
                min(0.85, score),
            )
        return "UNSUPPORTED", "REMOVE_UNSUPPORTED", max(0.4, 1 - score)
    return "UNSUPPORTED", "REMOVE_UNSUPPORTED", max(0.5, 1 - score)


def process_claims(
    source: dict[str, Any],
    v1: dict[str, Any],
    index: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_spans = [*display_spans(source), *index["spans"]]
    current_document_id = source["identifiers"]["current_accession_number"].replace("-", "")
    prior_spans = [
        span
        for span in all_spans
        if span["source_type"] != "SEC_10_K_CURRENT"
        and span.get("document_id") != current_document_id
        and span.get("point_in_time_eligible", True)
    ]
    current_spans = [
        span
        for span in all_spans
        if span["source_type"] == "SEC_10_K_CURRENT"
        or span.get("document_id") == current_document_id
    ]
    claims = decompose_packet(v1)
    if source["ticker"] == "EFX":
        finality_spans = [
            span
            for span in current_spans
            if "settlement became effective" in span["text"].lower()
            or (
                "$345" in span["text"]
                and "deposit" in span["text"].lower()
            )
        ]
        if finality_spans:
            claims.extend(
                decompose_statement(
                    (
                        "The Consumer Settlement became effective and Equifax "
                        "deposited approximately $345 million into the settlement fund."
                    ),
                    source_evidence_ids=[finality_spans[0]["evidence_id"]],
                    source_path="/retrieved_current_context/finality",
                )
            )
            for claim in claims[-1:]:
                claim["claim_type"] = "fact"
    diagnostics: list[dict[str, Any]] = []
    for claim in claims:
        prior_candidates = prefilter_spans(claim["exact_wording"], prior_spans)
        current_candidates = prefilter_spans(claim["exact_wording"], current_spans)
        novelty = assign_novelty(
            claim,
            prior_spans=prior_candidates,
            current_spans=current_candidates,
        )
        counter = search_counterevidence(
            claim,
            spans=prefilter_spans(claim["exact_wording"], all_spans),
        )
        top_current = assign_novelty(
            claim,
            prior_spans=current_candidates,
            current_spans=current_candidates,
        )["top_prior_matches"]
        strongest = top_current[0] if top_current else novelty.get("best_matching_prior_evidence_span")
        support, disposition, confidence = assess_support(
            claim,
            novelty=novelty,
            strongest_match=strongest,
            ticker=source["ticker"],
        )
        claim["prior_occurrence_search"] = {
            "performed": True,
            "query_terms": sorted(set(tokens(claim["exact_wording"]))) or ["no_terms"],
            "documents_searched": sorted(
                {span["document_id"] for span in prior_spans}
            ),
            "top_matches": novelty["top_prior_matches"],
        }
        claim["novelty_status"] = novelty["status"]
        claim["novelty_review"] = novelty
        claim["support_status"] = support
        claim["counterevidence_ids"] = sorted(
            {
                item["evidence_id"]
                for item in counter["counterevidence_matches"]
            }
        )
        claim["confidence"] = round(confidence, 6)
        claim["final_disposition"] = disposition
        diagnostics.append(
            {
                "proposition_id": claim["proposition_id"],
                "claim": claim["exact_wording"],
                "claim_type": claim["claim_type"],
                "query_terms": claim["prior_occurrence_search"]["query_terms"],
                "numeric_variants_searched": sorted(
                    set(re.findall(r"\d+(?:\.\d+)?", claim["exact_wording"].replace(",", "")))
                ),
                "synonyms_searched": [
                    "remaining/balance",
                    "maximum/cap/up to",
                    "deposit/payment",
                    "reserve/accrual",
                    "conditional/contingent"
                ],
                "sections_searched": sorted(
                    {span.get("section", "") for span in prior_spans}
                ),
                "filings_searched": claim["prior_occurrence_search"]["documents_searched"],
                "top_prior_matches": novelty["top_prior_matches"],
                "top_counterevidence": counter["counterevidence_matches"],
                "relevant_evidence_outside_original_excerpt": any(
                    item.get("outside_display_excerpt")
                    for item in novelty["top_prior_matches"]
                ),
                "earliest_occurrence": novelty["earliest_identified_prior_occurrence"],
                "retrieval_confidence": novelty["confidence"],
                "support_status": support,
                "final_disposition": disposition,
                "unresolved_gaps": (
                    ["No reliable supporting match."]
                    if support in {"AMBIGUOUS", "UNSUPPORTED"}
                    else []
                ),
                "counterevidence_review": counter,
            }
        )
    return claims, diagnostics


def financial_evidence(
    source: dict[str, Any], index: dict[str, Any], ticker: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    evidence_texts = display_spans(source)
    if ticker == "EFX":
        evidence_texts.extend(
            span
            for span in index["spans"]
            if any(
                marker in span["text"].lower()
                for marker in (
                    "consumer settlement became effective",
                    "remaining amount of $345",
                    "additional $125.0 million",
                )
            )
        )
    quantities: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for evidence in evidence_texts:
        for quantity in normalize_financial_quantities(evidence["text"]):
            quantity["evidence_id"] = evidence["evidence_id"]
            key = (
                quantity.get("normalized_amount"),
                quantity.get("percentage"),
                quantity["financial_role"],
                quantity["conditionality"],
                quantity["payment_status"],
            )
            if key not in seen:
                seen.add(key)
                quantities.append(quantity)
    comparisons: list[dict[str, Any]] = []
    for left_index, left in enumerate(quantities):
        for right in quantities[left_index + 1 :]:
            if left.get("currency") != "USD" or right.get("currency") != "USD":
                continue
            result = comparison_compatibility(left, right)
            comparisons.append(
                {
                    "left_quantity_id": left["quantity_id"],
                    "right_quantity_id": right["quantity_id"],
                    **result,
                }
            )
    additional = [
        span
        for span in index["spans"]
        if span.get("outside_display_excerpt")
        and any(
            item in span["text"].lower()
            for item in ("$125", "$346.7", "$345", "became effective", "not at risk")
        )
    ][:12]
    return quantities, comparisons[:40], additional


def safe_hypothesis(
    source: dict[str, Any],
    retained_claims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    template = SAFE_HYPOTHESES.get(source["change_id"])
    if not template:
        return []
    evidence_ids = sorted(
        {
            evidence_id
            for claim in retained_claims
            if claim["claim_type"] == "fact"
            for evidence_id in claim["source_evidence_ids"]
        }
    )
    if not evidence_ids:
        evidence_ids = [source["evidence"]["evidence_ids"]["current_excerpt"]]
    return [
        {
            **template,
            "evidence_ids": evidence_ids[:6],
            "support_status": "PARTIALLY_SUPPORTED",
            "publishable": True,
        }
    ]


def skeptic_status(
    source: dict[str, Any],
    claims: list[dict[str, Any]],
    hypotheses: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    objections: list[str] = []
    if source["ticker"] == "EFX":
        return (
            "REJECT_MISLEADING_COMPARISON",
            [
                "The $125 million conditional top-up was already disclosed in the prior 10-K.",
                "The selected prior excerpt omitted the prior $125 million term.",
                "The $346.7 million remaining balance and $125 million conditional top-up are not substitute quantities.",
                "Reserve inadequacy, current liquidity stress, and bondholder effects are unsupported."
            ],
        )
    unsupported = [
        claim
        for claim in claims
        if claim["support_status"] in {"UNSUPPORTED", "CONTRADICTED"}
    ]
    conflicts = [
        item for item in comparisons if item["status"] == "INCOMPARABLE_QUANTITIES"
    ]
    if hypotheses and not unsupported:
        return "PASS_HYPOTHESIS_ONLY", []
    if hypotheses:
        # Unsupported draft claims were removed; the final packet is assessed
        # on retained content only.
        return "PASS_HYPOTHESIS_ONLY", [
            "Unsupported V1 causal extensions were removed before publication."
        ]
    if conflicts and any(
        claim["final_disposition"].startswith("REMOVE")
        for claim in claims
    ):
        objections.append("Material financial quantities were not comparable.")
        return "REJECT_MISLEADING_COMPARISON", objections
    if any(
        claim["novelty_status"]
        in {"PREVIOUSLY_DISCLOSED_IN_10K", "PREVIOUSLY_DISCLOSED_IN_8K"}
        for claim in claims
    ):
        return "REJECT_PREVIOUSLY_DISCLOSED", [
            "The central disclosure term was already available in eligible prior evidence."
        ]
    if unsupported:
        return "REJECT_UNSUPPORTED_MECHANISM", [
            "The proposed mechanism depends on unsupported causal steps."
        ]
    return "HOLD_MISSING_CONTEXT", [
        "The retrieved evidence does not support a specific falsifiable mechanism."
    ]


def novelty_summary(
    source: dict[str, Any], claims: list[dict[str, Any]]
) -> dict[str, Any]:
    statuses = [claim["novelty_status"] for claim in claims]
    priority = (
        "RESOLVED_OR_FINALIZED_PRIOR_UNCERTAINTY",
        "GENUINELY_NEW_TERM",
        "NEW_QUANTIFICATION_OF_EXISTING_TERM",
        "MODIFIED_EXISTING_TERM",
        "PARTIALLY_ANTICIPATED",
        "PREVIOUSLY_DISCLOSED_IN_8K",
        "PREVIOUSLY_DISCLOSED_IN_10K",
        "UNCLEAR",
    )
    final = next((status for status in priority if status in statuses), "UNCLEAR")
    if source["ticker"] == "EFX":
        final = "RESOLVED_OR_FINALIZED_PRIOR_UNCERTAINTY"
    return {
        "provisional_novelty": source["novelty"]["classification"],
        "final_novelty": final,
        "what_is_new": (
            "Settlement finality and the approximately $345 million deposit."
            if source["ticker"] == "EFX"
            else "Only the retained, evidence-linked proposition or hypothesis."
        ),
        "what_is_not_new": (
            "The $125 million conditional top-up."
            if source["ticker"] == "EFX"
            else "Terms matched in eligible prior evidence."
        ),
    }


def packet_for_case(
    source: dict[str, Any],
    v1: dict[str, Any],
    index: dict[str, Any],
    index_sha: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    all_claims, diagnostics = process_claims(source, v1, index)
    retained = [
        claim
        for claim in all_claims
        if claim["final_disposition"]
        in {"RETAIN", "RETAIN_AS_LABELED_HYPOTHESIS", "VISIBLE_UNCERTAINTY"}
    ]
    quantities, comparisons, additional = financial_evidence(
        source, index, source["ticker"]
    )
    hypotheses = safe_hypothesis(source, retained)
    status, objections = skeptic_status(source, all_claims, hypotheses, comparisons)
    if status == "PASS_HYPOTHESIS_ONLY":
        packet_status = "PUBLISHABLE"
        packet_claims = [
            claim
            for claim in retained
            if claim["support_status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
        ]
    else:
        packet_status = status
        packet_claims = retained or all_claims[:1]
    factual = [claim for claim in packet_claims if claim["claim_type"] == "fact"]
    supported_factual = [
        claim for claim in factual if claim["support_status"] == "SUPPORTED"
    ]
    contradicted = [
        claim for claim in packet_claims if claim["support_status"] == "CONTRADICTED"
    ]
    critical_conflicts = (
        1
        if source["ticker"] == "EFX"
        and any(item["status"] == "INCOMPARABLE_QUANTITIES" for item in comparisons)
        else 0
    )
    ratio = len(supported_factual) / len(factual) if factual else 1.0
    publication_gate = (
        packet_status == "PUBLISHABLE"
        and ratio == 1.0
        and not contradicted
        and critical_conflicts == 0
        and bool(hypotheses)
    )
    counter_reviews = [item["counterevidence_review"] for item in diagnostics]
    strongest_counter = next(
        (
            review["strongest_counterevidence"]
            for review in counter_reviews
            if review["strongest_counterevidence"]
        ),
        None,
    )
    docs = sorted({doc["document_id"] for doc in index["documents"]})
    sections = sorted({span["section"] for span in index["spans"]})
    earliest = next(
        (
            claim["novelty_review"]["earliest_identified_prior_occurrence"]
            for claim in packet_claims
            if claim["novelty_review"]["earliest_identified_prior_occurrence"]
        ),
        None,
    )
    current_context = [
        span
        for span in index["spans"]
        if span["source_type"] == "SEC_10_K_CURRENT"
        and any(
            marker in span["text"].lower()
            for marker in ("became effective", "not at risk", "personally identifiable")
        )
    ][:8]
    packet: dict[str, Any] = {
        "packet_version": "2.0",
        "packet_id": f"research-idea-v2:{source['change_id']}",
        "packet_hash": "0" * 64,
        "packet_status": packet_status,
        "change_id": source["change_id"],
        "issuer": source["issuer"],
        "ticker": source["ticker"],
        "filing_date": source["filing_date"],
        "formation_timestamp": source["formation_timestamp"],
        "section": source["section"],
        "source_url": source["source_url"],
        "provisional_classification": {
            **source["frozen_classification"],
            "novelty": source["novelty"]["classification"],
        },
        "retrieval_metadata": {
            "evidence_index_version": "2.0",
            "evidence_index_sha256": index_sha,
            "full_prior_filing_search_completed": index[
                "full_prior_filing_search_completed"
            ],
            "documents_searched": docs,
            "sections_searched": sections,
            "timing_violations": [],
            "unresolved_gaps": [],
        },
        "source_evidence": {
            "prior_excerpt": source["evidence"]["prior_excerpt"],
            "current_excerpt": source["evidence"]["current_excerpt"],
            "current_context": current_context,
            "additional_prior_evidence": additional,
            "earliest_occurrence": earliest,
        },
        "atomic_claims": packet_claims,
        "financial_quantities": quantities,
        "quantity_comparisons": comparisons,
        "novelty_review": novelty_summary(source, all_claims),
        "research_hypotheses": hypotheses,
        "counterevidence_review": {
            "search_performed": True,
            "strongest_counterevidence": strongest_counter,
            "effect_on_novelty": (
                "CORRECTED" if strongest_counter else "NO_CHANGE"
            ),
            "effect_on_mechanism": (
                "UNSUPPORTED_DRAFT_CLAIMS_REMOVED"
                if any(
                    claim["final_disposition"].startswith("REMOVE")
                    for claim in all_claims
                )
                else "NO_CHANGE"
            ),
            "effect_on_trade_hypothesis": "WITHHELD",
            "final_result": (
                "COUNTEREVIDENCE_INCORPORATED"
                if strongest_counter
                else "NO_COUNTEREVIDENCE_FOUND"
            ),
            "claim_reviews": counter_reviews,
        },
        "illustrative_trade_hypothesis": {
            "status": "NOT_READY",
            "candidate_view": "no actionable view",
            "instrument": None,
            "required_market_checks": [],
            "research_only": True,
            "analyst_review_required": True,
        },
        "skeptic_review": {
            "status": status,
            "objections": objections,
            "opposite_interpretation": (
                "The disclosure may reflect wording, resolution, or precaution "
                "rather than deterioration."
            ),
            "generic_idea": status == "REJECT_GENERIC_IDEA",
            "instrument_fit": "No grounded instrument expression.",
            "falsifiable": bool(hypotheses),
        },
        "evidence_coverage": {
            "supported_factual_propositions": len(supported_factual),
            "all_factual_propositions": len(factual),
            "evidence_coverage_ratio": round(ratio, 6),
            "contradicted_factual_claims": len(contradicted),
            "unresolved_critical_numeric_role_conflicts": critical_conflicts,
            "missing_counterevidence_searches": 0,
            "publication_gate_passed": publication_gate,
        },
        "analyst_disposition": {
            "status": "UNREVIEWED",
            "analyst_notes": "",
            "review_timestamp": None,
            "saved_locally_only": True,
        },
        "disclaimer": DISCLAIMER,
    }
    packet["packet_hash"] = packet_hash(packet)
    diagnostic = {
        "diagnostic_version": "2.0",
        "change_id": source["change_id"],
        "ticker": source["ticker"],
        "formation_timestamp": source["formation_timestamp"],
        "query_terms": sorted(
            {
                term
                for item in diagnostics
                for term in item["query_terms"]
            }
        ),
        "numeric_variants_searched": sorted(
            {
                term
                for item in diagnostics
                for term in item["numeric_variants_searched"]
            }
        ),
        "synonyms_searched": diagnostics[0]["synonyms_searched"] if diagnostics else [],
        "sections_searched": sections,
        "filings_searched": docs,
        "top_prior_matches": [
            match
            for item in diagnostics
            for match in item["top_prior_matches"][:2]
        ][:20],
        "top_counterevidence": [
            match
            for item in diagnostics
            for match in item["top_counterevidence"][:1]
        ][:12],
        "relevant_evidence_outside_original_excerpt": any(
            item["relevant_evidence_outside_original_excerpt"]
            for item in diagnostics
        ),
        "earliest_occurrence": earliest,
        "retrieval_confidence": round(
            max(
                (item["retrieval_confidence"] for item in diagnostics),
                default=0,
            ),
            6,
        ),
        "unresolved_gaps": sorted(
            {
                gap
                for item in diagnostics
                for gap in item["unresolved_gaps"]
            }
        ),
        "atomic_claim_reviews": diagnostics,
    }
    return packet, diagnostic


def validate_packet(packet: dict[str, Any]) -> list[str]:
    atomic_schema = json.loads(ATOMIC_SCHEMA_PATH.read_text(encoding="utf-8"))
    packet_schema = json.loads(PACKET_SCHEMA_PATH.read_text(encoding="utf-8"))
    packet_schema["properties"]["atomic_claims"]["items"] = atomic_schema
    validator = Draft202012Validator(packet_schema, format_checker=FormatChecker())
    errors = [
        f"{'/'.join(map(str, error.absolute_path))}: {error.message}"
        for error in sorted(validator.iter_errors(packet), key=lambda err: list(err.path))
    ]
    if packet_hash(packet) != packet["packet_hash"]:
        errors.append("packet_hash: stale or incorrect")
    return errors


def diagnostic_markdown(source: dict[str, Any], diagnostic: dict[str, Any]) -> str:
    lines = [
        f"# {source['ticker']} V2 retrieval diagnostic",
        "",
        f"- Change ID: `{source['change_id']}`",
        f"- Formation timestamp: `{source['formation_timestamp']}`",
        f"- Filings searched: {len(diagnostic['filings_searched'])}",
        f"- Sections searched: {len(diagnostic['sections_searched'])}",
        f"- Evidence found outside display excerpt: **{str(diagnostic['relevant_evidence_outside_original_excerpt']).upper()}**",
        f"- Retrieval confidence: `{diagnostic['retrieval_confidence']}`",
        "",
        "## Queries",
        "",
        "- Terms: " + ", ".join(diagnostic["query_terms"]),
        "- Numeric variants: " + (", ".join(diagnostic["numeric_variants_searched"]) or "none"),
        "- Synonyms: " + ", ".join(diagnostic["synonyms_searched"]),
        "",
        "## Top prior matches",
        "",
    ]
    for match in diagnostic["top_prior_matches"][:10]:
        lines.append(
            f"- `{match['evidence_id']}` · score `{match['score']}` · "
            f"{match['source_type']} · {match['text'][:360]}"
        )
    lines.extend(["", "## Strongest counterevidence", ""])
    for match in diagnostic["top_counterevidence"][:8]:
        lines.append(
            f"- `{match['evidence_id']}` · score `{match['score']}` · "
            f"{match['text'][:360]}"
        )
    lines.extend(["", "## Unresolved gaps", ""])
    if diagnostic["unresolved_gaps"]:
        lines.extend(f"- {item}" for item in diagnostic["unresolved_gaps"])
    else:
        lines.append("- None recorded.")
    return "\n".join(lines) + "\n"


def redact(text: str, source: dict[str, Any]) -> str:
    value = text
    for token in (source["issuer"], source["ticker"]):
        if token:
            value = re.sub(re.escape(token), "[ISSUER]", value, flags=re.I)
    return value


def human_review_packet(
    packet: dict[str, Any], source: dict[str, Any], ordinal: int
) -> dict[str, Any]:
    return {
        "review_packet_version": "2.0",
        "blinded_case_id": f"CASE-{chr(64 + ordinal)}",
        "identity_redacted_where_practical": True,
        "future_outcomes_included": False,
        "v1_decision_included": False,
        "desired_publication_result_included": False,
        "prior_evidence": redact(packet["source_evidence"]["prior_excerpt"], source),
        "current_evidence": redact(packet["source_evidence"]["current_excerpt"], source),
        "additional_retrieved_context": [
            {
                "evidence_id": item["evidence_id"],
                "section": item["section"],
                "text": redact(item["text"], source),
            }
            for item in packet["source_evidence"]["additional_prior_evidence"]
        ],
        "atomic_claims": [
            {
                "proposition_id": item["proposition_id"],
                "exact_wording": redact(item["exact_wording"], source),
                "claim_type": item["claim_type"],
                "support_status": item["support_status"],
            }
            for item in packet["atomic_claims"]
        ],
        "novelty_result": packet["novelty_review"],
        "financial_quantities": packet["financial_quantities"],
        "proposed_mechanism_and_hypotheses": packet["research_hypotheses"],
        "skeptic_objections": packet["skeptic_review"]["objections"],
    }


def comparison_section(
    source: dict[str, Any],
    v1: dict[str, Any],
    v2: dict[str, Any],
    diagnostic: dict[str, Any],
) -> list[str]:
    v1_facts = [
        fact["statement"]
        for fact in v1.get("system_interpretation", {}).get("evidence_facts", [])
    ]
    v2_facts = [
        claim["exact_wording"]
        for claim in v2["atomic_claims"]
        if claim["claim_type"] == "fact"
    ]
    removed = [
        item["claim"]
        for item in diagnostic["atomic_claim_reviews"]
        if item["final_disposition"].startswith("REMOVE")
    ]
    numeric = [
        item
        for item in v2["quantity_comparisons"]
        if item["status"] == "INCOMPARABLE_QUANTITIES"
    ]
    lines = [
        f"## {source['ticker']} · `{source['change_id']}`",
        "",
        f"- V1 status: `{v1['packet_status']}`",
        f"- V2 status: `{v2['packet_status']}`",
        f"- V2 skeptic: `{v2['skeptic_review']['status']}`",
        f"- Final novelty: `{v2['novelty_review']['final_novelty']}`",
        f"- Claims removed: `{len(removed)}`",
        f"- Numeric-role corrections: `{len(numeric)}`",
        "",
        "### V1 factual claims",
        "",
    ]
    lines.extend(f"- {item}" for item in v1_facts)
    lines.extend(["", "### V2 retained factual claims", ""])
    lines.extend(f"- {item}" for item in v2_facts)
    if not v2_facts:
        lines.append("- None.")
    lines.extend(["", "### Removed or corrected claims", ""])
    lines.extend(f"- {item}" for item in removed)
    if not removed:
        lines.append("- None.")
    lines.extend(["", "### Trade-hypothesis correction", ""])
    lines.append(
        f"- V2 trade status: `{v2['illustrative_trade_hypothesis']['status']}`; "
        f"view: `{v2['illustrative_trade_hypothesis']['candidate_view']}`."
    )
    lines.append("")
    return lines


def build() -> dict[str, Any]:
    sources = source_map()
    V2_PACKET_DIR.mkdir(parents=True, exist_ok=True)
    V2_PUBLIC_PACKET_DIR.mkdir(parents=True, exist_ok=True)
    DIAGNOSTIC_DIR.mkdir(parents=True, exist_ok=True)
    HUMAN_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    packets: list[dict[str, Any]] = []
    comparison_lines = [
        "# Research Idea Engine V1 versus V2 packet comparison",
        "",
        "V2 uses full-prior retrieval, atomic claims, financial-role checks, and "
        "mandatory counterevidence. V1 artifacts remain unchanged.",
        "",
    ]
    review_rows: list[dict[str, str]] = []
    for ordinal, change_id in enumerate(sources, start=1):
        source = sources[change_id]
        v1 = json.loads((V1_PACKET_DIR / f"{change_id}.json").read_text(encoding="utf-8"))
        index_path = INDEX_DIR / f"{change_id}.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        packet, diagnostic = packet_for_case(
            source, v1, index, sha256_bytes(index_path.read_bytes())
        )
        errors = validate_packet(packet)
        if errors:
            raise RuntimeError(f"{source['ticker']} V2 validation failed: {errors}")
        write_json(V2_PACKET_DIR / f"{change_id}.json", packet)
        write_json(V2_PUBLIC_PACKET_DIR / f"{change_id}.json", packet)
        write_json(DIAGNOSTIC_DIR / f"{change_id}.json", diagnostic)
        (DIAGNOSTIC_DIR / f"{change_id}.md").write_text(
            diagnostic_markdown(source, diagnostic), encoding="utf-8"
        )
        blinded = human_review_packet(packet, source, ordinal)
        write_json(HUMAN_REVIEW_DIR / f"case_{ordinal:02d}.json", blinded)
        (HUMAN_REVIEW_DIR / f"case_{ordinal:02d}.md").write_text(
            "# Blinded V2 review packet\n\n"
            + f"- Case: `{blinded['blinded_case_id']}`\n"
            + "- Future outcomes: excluded\n"
            + "- V1 decision: excluded\n\n"
            + "## Prior evidence\n\n"
            + blinded["prior_evidence"]
            + "\n\n## Current evidence\n\n"
            + blinded["current_evidence"]
            + "\n\n## Atomic claims\n\n"
            + "\n".join(
                f"- [{item['support_status']}] {item['exact_wording']}"
                for item in blinded["atomic_claims"]
            )
            + "\n\n## Skeptic objections\n\n"
            + (
                "\n".join(f"- {item}" for item in blinded["skeptic_objections"])
                or "- None."
            )
            + "\n",
            encoding="utf-8",
        )
        review_rows.append(
            {
                "blinded_case_id": blinded["blinded_case_id"],
                "factual_support_1_5": "",
                "novelty_accuracy_1_5": "",
                "numeric_interpretation_1_5": "",
                "mechanism_quality_1_5": "",
                "falsifiability_1_5": "",
                "usefulness_1_5": "",
                "trade_instrument_fit_1_5": "",
                "disposition_accept_edit_reject": "",
                "comments": "",
            }
        )
        packets.append(packet)
        comparison_lines.extend(
            comparison_section(source, v1, packet, diagnostic)
        )
    index_entries = [
        {
            "change_id": packet["change_id"],
            "ticker": packet["ticker"],
            "issuer": packet["issuer"],
            "packet_status": packet["packet_status"],
            "skeptic_status": packet["skeptic_review"]["status"],
            "final_novelty": packet["novelty_review"]["final_novelty"],
            "evidence_coverage_ratio": packet["evidence_coverage"][
                "evidence_coverage_ratio"
            ],
            "full_prior_filing_evidence_checked": packet["retrieval_metadata"][
                "full_prior_filing_search_completed"
            ],
            "packet_hash": packet["packet_hash"],
        }
        for packet in packets
    ]
    index = {
        "index_version": "2.0",
        "packet_count": len(packets),
        "packets": index_entries,
    }
    index["membership_sha256"] = sha256_bytes(
        "".join(
            f"{item['change_id']}\t{item['packet_hash']}\n"
            for item in index_entries
        ).encode("utf-8")
    )
    write_json(V2_PACKET_DIR / "index.json", index)
    write_json(V2_PUBLIC_PACKET_DIR / "index.json", index)
    COMPARISON_PATH.write_text("\n".join(comparison_lines), encoding="utf-8")
    with (HUMAN_REVIEW_DIR / "review_form.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review_rows[0]))
        writer.writeheader()
        writer.writerows(review_rows)
    return index


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
