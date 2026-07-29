#!/usr/bin/env python3
"""Deterministic counterevidence retrieval over the V2 evidence index."""

from __future__ import annotations

from typing import Any

from assign_novelty_v2 import rank_matches


COUNTER_MARKERS = (
    "do not believe",
    "does not",
    "did not",
    "not at risk",
    "no assurance",
    "already paid",
    "has paid",
    "deposited",
    "remaining",
    "resolved",
    "effective",
    "insured",
    "insurance",
    "reserved",
    "accrued",
    "best estimate",
    "no material impact",
    "not material",
    "unable to estimate",
)


def search_counterevidence(
    proposition: dict[str, Any],
    *,
    spans: list[dict[str, Any]],
    limit: int = 5,
) -> dict[str, Any]:
    ranked = rank_matches(proposition["exact_wording"], spans, limit=30)
    counter = [
        match
        for match in ranked
        if any(marker in match["text"].lower() for marker in COUNTER_MARKERS)
    ][:limit]
    if not counter:
        counter = ranked[: min(limit, len(ranked))]
    strongest = counter[0] if counter else None
    wording = proposition["exact_wording"].lower()
    mechanism_effect = "NO_CHANGE"
    if strongest:
        text = strongest["text"].lower()
        if (
            any(term in wording for term in ("liquidity stress", "insufficient", "strain"))
            and any(term in text for term in ("cash", "borrowing capacity", "do not believe"))
        ):
            mechanism_effect = "WEAKENS"
        elif (
            any(
                term in wording
                for term in ("reserve", "under-reserved", "inadequate")
            )
            and any(
                term in text
                for term in ("accrued", "best estimate", "reserved")
            )
        ):
            mechanism_effect = "WEAKENS"
        elif strongest["score"] >= 0.5:
            mechanism_effect = "WEAKENS"
    return {
        "search_performed": True,
        "query": proposition["exact_wording"],
        "strongest_counterevidence": strongest,
        "counterevidence_matches": counter,
        "effect_on_novelty": "REASSESS_PRIOR_OCCURRENCE" if counter else "NO_CHANGE",
        "effect_on_mechanism": mechanism_effect,
        "effect_on_trade_hypothesis": (
            "WITHHOLD_IF_MECHANISM_DEPENDS_ON_REJECTED_CLAIM"
            if mechanism_effect == "WEAKENS"
            else "NO_CHANGE"
        ),
        "final_result": "COUNTEREVIDENCE_FOUND" if counter else "NO_COUNTEREVIDENCE_FOUND",
    }
