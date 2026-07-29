#!/usr/bin/env python3
"""Deterministically split generated statements into reviewable propositions."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable


CLAUSE_SPLIT_RE = re.compile(
    r"\s*(?:;|\bbut\b|\bwhile\b|\bwhereas\b|,\s+(?:which|suggesting|indicating)\b)\s*",
    re.IGNORECASE,
)


def claim_type(statement: str) -> str:
    lowered = statement.lower()
    if any(
        marker in lowered
        for marker in (
            "will ",
            "likely ",
            "may ",
            "could ",
            "would ",
            "hypothesis",
            "if ",
        )
    ):
        return "hypothesis"
    if any(
        marker in lowered
        for marker in ("suggests", "indicates", "implies", "reflects", "signals")
    ):
        return "interpretation"
    if any(
        marker in lowered
        for marker in ("market", "bondholder", "valuation", "mispricing", "spread")
    ):
        return "speculative_extension"
    return "fact"


def _id(statement: str, ordinal: int) -> str:
    digest = hashlib.sha256(
        f"{ordinal}\0{' '.join(statement.split())}".encode("utf-8")
    ).hexdigest()
    return f"proposition-v2:{digest[:20]}"


def split_clauses(statement: str) -> list[str]:
    normalized = " ".join(statement.strip().split())
    if not normalized:
        return []
    clauses = [item.strip(" ,.") for item in CLAUSE_SPLIT_RE.split(normalized)]
    expanded: list[str] = []
    for clause in clauses:
        # Split an explicit two-part "and" construction only when both sides
        # contain their own verb-like token. This avoids shredding noun lists.
        parts = re.split(r"\s+\band\b\s+", clause, maxsplit=1, flags=re.I)
        if len(parts) == 2 and all(
            re.search(
                r"\b(?:is|are|was|were|has|have|exists|faces|states|reports|"
                r"represents|creates|indicates|suggests|may|could|will)\b",
                part,
                re.I,
            )
            for part in parts
        ):
            expanded.extend(part.strip(" ,.") for part in parts)
        else:
            expanded.append(clause)
    return [item for item in expanded if item]


def decompose_statement(
    statement: str,
    *,
    source_evidence_ids: Iterable[str] = (),
    source_path: str = "",
) -> list[dict[str, Any]]:
    propositions: list[dict[str, Any]] = []
    for ordinal, clause in enumerate(split_clauses(statement), start=1):
        kind = claim_type(clause)
        propositions.append(
            {
                "proposition_id": _id(clause, ordinal),
                "exact_wording": clause,
                "claim_type": kind,
                "source_path": source_path,
                "source_evidence_ids": sorted(set(map(str, source_evidence_ids))),
                "counterevidence_ids": [],
                "prior_occurrence_search": {
                    "performed": False,
                    "query_terms": [],
                    "documents_searched": [],
                    "top_matches": [],
                },
                "novelty_status": "UNCLEAR",
                "support_status": "AMBIGUOUS",
                "confidence": 0.0,
                "final_disposition": "PENDING_REVIEW",
            }
        )
    return propositions


def decompose_packet(packet: dict[str, Any]) -> list[dict[str, Any]]:
    propositions: list[dict[str, Any]] = []
    interpretation = packet.get("system_interpretation") or {}
    plain_change = str(interpretation.get("plain_language_change", "")).strip()
    if plain_change:
        plain_claims = decompose_statement(
            plain_change,
            source_evidence_ids=(
                packet.get("evidence", {}).get("evidence_ids", {}).values()
            ),
            source_path="/system_interpretation/plain_language_change",
        )
        for claim in plain_claims:
            if claim["claim_type"] == "fact":
                claim["claim_type"] = "interpretation"
        propositions.extend(plain_claims)
    for index, fact in enumerate(interpretation.get("evidence_facts", [])):
        fact_claims = decompose_statement(
            str(fact.get("statement", "")),
            source_evidence_ids=fact.get("evidence_ids", []),
            source_path=f"/system_interpretation/evidence_facts/{index}/statement",
        )
        for claim in fact_claims:
            claim["claim_type"] = "fact"
        propositions.extend(fact_claims)
    for index, inference in enumerate(interpretation.get("inferences", [])):
        inference_claims = decompose_statement(
            str(inference.get("statement", "")),
            source_evidence_ids=inference.get("evidence_ids", []),
            source_path=f"/system_interpretation/inferences/{index}/statement",
        )
        for claim in inference_claims:
            if claim["claim_type"] == "fact":
                claim["claim_type"] = "interpretation"
        propositions.extend(inference_claims)
    for index, hypothesis in enumerate(packet.get("research_hypotheses", [])):
        hypothesis_claims = decompose_statement(
            str(hypothesis.get("hypothesis", "")),
            source_evidence_ids=hypothesis.get("evidence_ids", []),
            source_path=f"/research_hypotheses/{index}/hypothesis",
        )
        for claim in hypothesis_claims:
            claim["claim_type"] = "hypothesis"
        propositions.extend(hypothesis_claims)
    for mechanism_index, mechanism in enumerate(
        packet.get("economic_mechanisms", [])
    ):
        for step_index, step in enumerate(mechanism.get("causal_chain", [])):
            mechanism_claims = decompose_statement(
                str(step),
                source_evidence_ids=mechanism.get(
                    "supporting_evidence_ids", []
                ),
                source_path=(
                    f"/economic_mechanisms/{mechanism_index}/"
                    f"causal_chain/{step_index}"
                ),
            )
            for claim in mechanism_claims:
                if claim["claim_type"] == "fact":
                    claim["claim_type"] = "interpretation"
            propositions.extend(mechanism_claims)
    for entity_index, entity in enumerate(packet.get("affected_entities", [])):
        for field in ("entity_or_group", "reason", "possible_effect"):
            statement = str(entity.get(field, "")).strip()
            if not statement:
                continue
            if field == "entity_or_group":
                statement = f"Proposed affected entity or group: {statement}"
            entity_claims = decompose_statement(
                statement,
                source_evidence_ids=entity.get("evidence_ids", []),
                source_path=f"/affected_entities/{entity_index}/{field}",
            )
            for claim in entity_claims:
                if claim["claim_type"] == "fact":
                    claim["claim_type"] = "interpretation"
            propositions.extend(entity_claims)
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for proposition in propositions:
        key = proposition["exact_wording"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(proposition)
    return deduped
