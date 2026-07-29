#!/usr/bin/env python3
"""Deterministic financial-quantity extraction and role compatibility checks."""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from typing import Any


MONEY_RE = re.compile(
    r"(?P<currency>\$|USD\s*)?"
    r"(?P<number>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"\s*(?P<scale>billion|million|thousand|bn|mm|m|k)?\b",
    re.IGNORECASE,
)
PERCENT_RE = re.compile(r"(?P<number>\d+(?:\.\d+)?)\s*%")
DATE_RE = re.compile(
    r"\b(?:19|20)\d{2}(?:-\d{2}-\d{2})?\b"
    r"|\b(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},\s+(?:19|20)\d{2}\b",
    re.IGNORECASE,
)
DURATION_RE = re.compile(
    r"\b(?:up to|within|over|for)\s+\d+(?:\.\d+)?\s+"
    r"(?:days?|weeks?|months?|quarters?|years?)\b",
    re.IGNORECASE,
)

SCALE_FACTORS = {
    None: Decimal("1"),
    "": Decimal("1"),
    "k": Decimal("1000"),
    "thousand": Decimal("1000"),
    "m": Decimal("1000000"),
    "mm": Decimal("1000000"),
    "million": Decimal("1000000"),
    "bn": Decimal("1000000000"),
    "billion": Decimal("1000000000"),
}

ROLE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("conditional top-up", ("additional", "if ", "fund is exhausted", "top-up")),
    ("remaining balance", ("remaining", "left to pay", "outstanding balance")),
    ("cash deposit", ("deposit", "deposited", "settlement fund")),
    ("payment already made", ("paid", "payment made")),
    ("future payment", ("to be paid", "will pay", "payable", "future payment")),
    ("recognized expense", ("recorded expense", "recognized expense", "charge")),
    ("reserve", ("reserve", "accrual", "accrued")),
    ("settlement amount", ("settlement amount", "settlement fund", "settlement")),
    ("maximum exposure", ("maximum", "up to", "not to exceed", "cap")),
    ("total obligation", ("total obligation", "aggregate obligation")),
    ("estimated loss", ("estimated loss", "best estimate", "reasonably possible loss")),
    ("available liquidity", ("available liquidity", "cash on hand")),
    ("borrowing capacity", ("borrowing capacity", "credit facility", "revolver")),
    ("covenant threshold", ("covenant", "threshold", "ratio")),
)


def _quantity_id(text: str, start: int, raw: str) -> str:
    digest = hashlib.sha256(f"{start}\0{raw}\0{text}".encode("utf-8")).hexdigest()
    return f"quantity-v2:{digest[:20]}"


def classify_financial_role(context: str) -> str:
    lowered = " ".join(context.lower().split())
    for role, markers in ROLE_RULES:
        if any(marker in lowered for marker in markers):
            return role
    return "unknown or ambiguous"


def classify_conditionality(context: str) -> str:
    lowered = context.lower()
    if any(marker in lowered for marker in ("if ", "could", "may ", "contingent")):
        return "conditional"
    if any(marker in lowered for marker in ("agreed to", "committed", "will ")):
        return "committed"
    return "unconditional_or_unspecified"


def classify_payment_status(context: str) -> str:
    lowered = context.lower()
    if any(marker in lowered for marker in ("already paid", "has paid", "deposited")):
        return "paid"
    if "remaining" in lowered:
        return "remaining"
    if any(marker in lowered for marker in ("to be paid", "will pay", "payable")):
        return "future"
    if any(marker in lowered for marker in ("could", "may", "if ")):
        return "conditional"
    return "unspecified"


def normalize_financial_quantities(text: str) -> list[dict[str, Any]]:
    quantities: list[dict[str, Any]] = []
    occupied: list[tuple[int, int]] = []
    for match in MONEY_RE.finditer(text):
        raw = match.group(0)
        currency_token = (match.group("currency") or "").strip()
        scale_token = (match.group("scale") or "").lower()
        is_financial = bool(currency_token or scale_token)
        if not is_financial:
            continue
        number = Decimal(match.group("number").replace(",", ""))
        factor = SCALE_FACTORS.get(scale_token, Decimal("1"))
        start, end = match.span()
        context_start = max(0, start - 180)
        context_end = min(len(text), end + 180)
        context = text[context_start:context_end]
        role = classify_financial_role(context)
        quantities.append(
            {
                "quantity_id": _quantity_id(text, start, raw),
                "raw_text": raw,
                "amount": float(number),
                "currency": "USD" if currency_token in {"$", "USD"} else "UNKNOWN",
                "scale": scale_token or "units",
                "normalized_amount": float(number * factor),
                "percentage": None,
                "date": DATE_RE.search(context).group(0)
                if DATE_RE.search(context)
                else None,
                "duration": DURATION_RE.search(context).group(0)
                if DURATION_RE.search(context)
                else None,
                "conditionality": classify_conditionality(context),
                "financial_role": role,
                "gross_net_basis": "net"
                if re.search(r"\bnet of\b", context, re.I)
                else "gross_or_unspecified",
                "payment_status": classify_payment_status(context),
                "historical_current": "historical"
                if re.search(r"\b(?:prior|historical|in 20\d{2}|through 20\d{2})\b", context, re.I)
                else "current_or_unspecified",
                "start_offset": start,
                "end_offset": end,
                "context": " ".join(context.split()),
            }
        )
        occupied.append((start, end))
    for match in PERCENT_RE.finditer(text):
        start, end = match.span()
        if any(start >= left and end <= right for left, right in occupied):
            continue
        context = text[max(0, start - 180) : min(len(text), end + 180)]
        quantities.append(
            {
                "quantity_id": _quantity_id(text, start, match.group(0)),
                "raw_text": match.group(0),
                "amount": None,
                "currency": None,
                "scale": "percentage",
                "normalized_amount": None,
                "percentage": float(match.group("number")),
                "date": DATE_RE.search(context).group(0)
                if DATE_RE.search(context)
                else None,
                "duration": DURATION_RE.search(context).group(0)
                if DURATION_RE.search(context)
                else None,
                "conditionality": classify_conditionality(context),
                "financial_role": classify_financial_role(context),
                "gross_net_basis": "not_applicable",
                "payment_status": "not_applicable",
                "historical_current": "historical"
                if re.search(r"\b(?:prior|historical|in 20\d{2}|through 20\d{2})\b", context, re.I)
                else "current_or_unspecified",
                "start_offset": start,
                "end_offset": end,
                "context": " ".join(context.split()),
            }
        )
    return quantities


def comparison_compatibility(
    left: dict[str, Any], right: dict[str, Any]
) -> dict[str, Any]:
    conflicts: list[str] = []
    if left.get("currency") != right.get("currency"):
        conflicts.append("currency")
    if left.get("financial_role") != right.get("financial_role"):
        conflicts.append("financial_role")
    if left.get("conditionality") != right.get("conditionality"):
        conflicts.append("conditionality")
    if left.get("gross_net_basis") != right.get("gross_net_basis"):
        conflicts.append("gross_net_basis")
    if left.get("payment_status") != right.get("payment_status"):
        conflicts.append("payment_status")
    left_date, right_date = left.get("date"), right.get("date")
    if left_date and right_date and left_date != right_date:
        conflicts.append("period")
    return {
        "status": "INCOMPARABLE_QUANTITIES" if conflicts else "COMPARABLE",
        "conflicts": conflicts,
        "same_unit": left.get("currency") == right.get("currency"),
        "same_role": left.get("financial_role") == right.get("financial_role"),
        "same_period": not (left_date and right_date and left_date != right_date),
        "same_conditionality": left.get("conditionality")
        == right.get("conditionality"),
        "compatible_gross_net_basis": left.get("gross_net_basis")
        == right.get("gross_net_basis"),
        "compatible_payment_basis": left.get("payment_status")
        == right.get("payment_status"),
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    args = parser.parse_args()
    print(json.dumps(normalize_financial_quantities(args.text), indent=2))
