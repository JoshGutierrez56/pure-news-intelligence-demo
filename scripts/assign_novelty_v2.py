#!/usr/bin/env python3
"""Full-prior-record novelty assignment for atomic propositions."""

from __future__ import annotations

import math
import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any, Iterable

from normalize_financial_quantities import normalize_financial_quantities


NOVELTY_TAXONOMY = {
    "GENUINELY_NEW_TERM",
    "NEW_QUANTIFICATION_OF_EXISTING_TERM",
    "MODIFIED_EXISTING_TERM",
    "RESTATED_EXISTING_TERM",
    "RESOLVED_OR_FINALIZED_PRIOR_UNCERTAINTY",
    "PREVIOUSLY_DISCLOSED_IN_10K",
    "PREVIOUSLY_DISCLOSED_IN_8K",
    "PREVIOUSLY_COVERED_IN_NEWS",
    "PARTIALLY_ANTICIPATED",
    "CONTEXT_ONLY_CHANGE",
    "DISPLAY_EXCERPT_OMITTED_PRIOR_EVIDENCE",
    "INCOMPARABLE_QUANTITIES",
    "UNCLEAR",
}

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "for",
    "on",
    "that",
    "this",
    "is",
    "are",
    "was",
    "were",
    "be",
    "could",
    "may",
    "will",
    "with",
    "from",
    "as",
    "by",
}


def tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower())
        if token not in STOPWORDS and len(token) > 1
    ]


def lexical_overlap(left: str, right: str) -> float:
    a, b = set(tokens(left)), set(tokens(right))
    return len(a & b) / len(a | b) if a and b else 0.0


def semantic_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, " ".join(tokens(left)), " ".join(tokens(right))).ratio()


def numeric_terms(text: str) -> set[float]:
    return {
        float(item["normalized_amount"])
        for item in normalize_financial_quantities(text)
        if item.get("normalized_amount") is not None
    }


def _role_terms(text: str) -> set[str]:
    return {
        item["financial_role"]
        for item in normalize_financial_quantities(text)
        if item["financial_role"] != "unknown or ambiguous"
    }


def rank_matches(
    statement: str, spans: Iterable[dict[str, Any]], *, limit: int = 8
) -> list[dict[str, Any]]:
    target_numbers = numeric_terms(statement)
    target_roles = _role_terms(statement)
    matches: list[dict[str, Any]] = []
    for span in spans:
        text = str(span.get("text", ""))
        lex = lexical_overlap(statement, text)
        sem = semantic_similarity(statement, text)
        span_numbers = numeric_terms(text)
        span_roles = _role_terms(text)
        numeric_match = sorted(target_numbers & span_numbers)
        role_match = sorted(target_roles & span_roles)
        score = (
            0.45 * lex
            + 0.30 * sem
            + 0.20 * (1.0 if numeric_match else 0.0)
            + 0.05 * (1.0 if role_match else 0.0)
        )
        if score <= 0:
            continue
        matches.append(
            {
                "evidence_id": span["evidence_id"],
                "source_type": span["source_type"],
                "filing_date": span.get("filing_date"),
                "acceptance_timestamp": span.get("acceptance_timestamp"),
                "section": span.get("section"),
                "paragraph_number": span.get("paragraph_number"),
                "lexical_overlap": round(lex, 6),
                "semantic_similarity": round(sem, 6),
                "matching_numeric_terms": numeric_match,
                "matching_financial_roles": role_match,
                "score": round(score, 6),
                "text": text,
                "outside_display_excerpt": bool(span.get("outside_display_excerpt")),
            }
        )
    return sorted(
        matches,
        key=lambda item: (
            -item["score"],
            item.get("acceptance_timestamp") or "",
            item["evidence_id"],
        ),
    )[:limit]


def assign_novelty(
    proposition: dict[str, Any],
    *,
    prior_spans: list[dict[str, Any]],
    current_spans: list[dict[str, Any]],
) -> dict[str, Any]:
    statement = proposition["exact_wording"]
    matches = rank_matches(statement, prior_spans)
    best = matches[0] if matches else None
    numbers = numeric_terms(statement)
    prior_number_match = bool(best and best["matching_numeric_terms"])
    high_match = bool(
        best
        and (
            best["score"] >= 0.50
            or best["lexical_overlap"] >= 0.42
            or (prior_number_match and best["semantic_similarity"] >= 0.30)
        )
    )
    lowered = statement.lower()
    finality = any(
        term in lowered
        for term in ("became effective", "finalized", "resolved", "appeals resolved")
    )
    if high_match:
        if best["source_type"] == "SEC_8_K":
            status = "PREVIOUSLY_DISCLOSED_IN_8K"
        elif best["source_type"] == "NEWS_HEADLINE":
            status = "PREVIOUSLY_COVERED_IN_NEWS"
        else:
            status = "PREVIOUSLY_DISCLOSED_IN_10K"
    elif finality:
        status = "RESOLVED_OR_FINALIZED_PRIOR_UNCERTAINTY"
    elif matches and best["score"] >= 0.32:
        status = (
            "NEW_QUANTIFICATION_OF_EXISTING_TERM"
            if numbers and not prior_number_match
            else "PARTIALLY_ANTICIPATED"
        )
    elif current_spans:
        status = "GENUINELY_NEW_TERM"
    else:
        status = "UNCLEAR"
    earliest = None
    qualifying = [
        match
        for match in matches
        if match["score"] >= 0.32
    ]
    if qualifying:
        earliest = sorted(
            qualifying,
            key=lambda item: (
                item.get("acceptance_timestamp") or "9999",
                item["evidence_id"],
            ),
        )[0]
    confidence = min(0.99, max(0.15, best["score"] if best else 0.35))
    return {
        "status": status,
        "display_excerpt_status": (
            "DISPLAY_EXCERPT_OMITTED_PRIOR_EVIDENCE"
            if high_match
            and best
            and best["source_type"] in {"SEC_10_K", "SEC_10_K_CURRENT"}
            and best["outside_display_excerpt"]
            else None
        ),
        "earliest_identified_prior_occurrence": earliest,
        "best_matching_prior_evidence_span": best,
        "semantic_similarity": best["semantic_similarity"] if best else 0.0,
        "lexical_overlap": best["lexical_overlap"] if best else 0.0,
        "matching_numeric_terms": best["matching_numeric_terms"] if best else [],
        "matching_legal_or_accounting_role": best["matching_financial_roles"]
        if best
        else [],
        "what_specifically_changed": (
            "Resolution or finality changed while the underlying term pre-existed."
            if finality
            else "See proposition and matched spans."
        ),
        "what_did_not_change": (
            "The matched prior term or amount remained previously disclosed."
            if high_match
            else "No unchanged element established."
        ),
        "confidence": round(confidence, 6),
        "ambiguity_reason": None if status != "UNCLEAR" else "No reliable prior or current match.",
        "top_prior_matches": matches,
    }
