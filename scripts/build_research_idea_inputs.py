#!/usr/bin/env python3
"""Build the locked eight-case, formation-time research-idea input bundle.

The builder is intentionally fail-closed. It accepts only the authoritative
eight-row case-study CSV at its frozen SHA-256 and only reads the explicit
source-column prefix ending at ``change_novelty_method``. Later outcome fields
are never copied into the bundle.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse


SOURCE_SHA256 = "fa7e4fb3809d622ddee4144fc3b75d54314db7091491d3635f194b0f5349396d"
EXPECTED_ROW_COUNT = 8
EXPECTED_CASES = (
    (1, "dbe75bc24f2888f4166a", "TFC"),
    (2, "8f5336b55618ffe68e8a", "KHC"),
    (3, "339fae2941721ee094b0", "DLTR"),
    (4, "4784f62ad001b2a12af4", "DVN"),
    (5, "412b08746bb0ed5a7745", "RH"),
    (6, "8d4598f4ea16f15c7048", "FCX"),
    (7, "279e7d4e407851a19548", "EFX"),
    (8, "2f22dc2216c9df31d377", "CHE"),
)

# This tuple is both the schema lock and the allowed-input boundary. The source
# CSV contains additional columns after change_novelty_method; none are read.
ALLOWED_SOURCE_COLUMNS = (
    "case_order",
    "current_filing_id",
    "featured_change_id",
    "selection_rationale",
    "selection_used_future_outcomes",
    "change_change_id",
    "change_current_filing_id",
    "change_prior_filing_id",
    "change_current_accession_number",
    "change_prior_accession_number",
    "change_cik",
    "change_permno",
    "change_company_name",
    "change_ticker",
    "change_sector_code",
    "change_current_filing_date",
    "change_prior_filing_date",
    "change_current_acceptance",
    "change_prior_acceptance",
    "change_section",
    "change_category",
    "change_category_slug",
    "change_direction",
    "change_materiality",
    "change_prior_excerpt",
    "change_current_excerpt",
    "change_prior_start_offset",
    "change_prior_end_offset",
    "change_current_start_offset",
    "change_current_end_offset",
    "change_added_text",
    "change_removed_text",
    "change_changed_numbers",
    "change_new_entities",
    "change_alignment_similarity",
    "change_confidence",
    "change_classification_method",
    "change_alignment_model",
    "change_matched_terms",
    "change_why_it_matters",
    "change_current_sec_url",
    "change_prior_sec_url",
    "change_evidence_provenance",
    "change_novelty_after_prior_disclosures",
    "change_related_8ks",
    "change_related_news",
    "change_prior_8k_search_count",
    "change_prior_news_search_count",
    "change_novelty_method",
)

# These source columns are deliberately beyond the cutoff. The output audit
# rejects them as keys if a future edit accidentally introduces any of them.
FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "change_novelty_is_causal_claim",
        "maximum_drawdown_12m",
        "realized_volatility_12m",
        "drawdown_worse_than_20pct",
        "abnormal_return_6m",
        "abnormal_return_12m",
        "ex_post_downside_outcome",
        "selection_stage",
        "outcome_stage",
    }
)

PROVENANCE_SOURCE_KEYS = frozenset(
    {
        "current_parsed_artifact_hash",
        "current_parsed_path",
        "current_primary_document_hash",
        "prior_parsed_artifact_hash",
        "prior_parsed_path",
        "prior_primary_document_hash",
    }
)
PROVENANCE_HASH_KEYS = (
    "current_parsed_artifact_hash",
    "current_primary_document_hash",
    "prior_parsed_artifact_hash",
    "prior_primary_document_hash",
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_PATH_RE = re.compile(r"(?i)(?:^|[\s\"'])[a-z]:[\\/]")
LOCAL_URI_RE = re.compile(r"(?i)\bfile://")
POSIX_HOME_RE = re.compile(r"(?:^|[\s\"'])(?:/home/|/Users/)")


class BuildError(RuntimeError):
    """Raised when a locked source or formation-time invariant fails."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def parse_int(value: str, field: str, *, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise BuildError(f"{field} must be an integer") from exc
    if minimum is not None and parsed < minimum:
        raise BuildError(f"{field} must be >= {minimum}")
    return parsed


def parse_float(
    value: str,
    field: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise BuildError(f"{field} must be numeric") from exc
    if not math.isfinite(parsed):
        raise BuildError(f"{field} must be finite")
    if minimum is not None and parsed < minimum:
        raise BuildError(f"{field} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise BuildError(f"{field} must be <= {maximum}")
    return parsed


def parse_bool(value: str, field: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise BuildError(f"{field} must be True or False")


def parse_json(value: str, field: str, expected_type: type) -> Any:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise BuildError(f"{field} is not valid JSON") from exc
    if not isinstance(parsed, expected_type):
        raise BuildError(f"{field} must decode to {expected_type.__name__}")
    return parsed


def parse_timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BuildError(f"{field} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise BuildError(f"{field} must include a timezone")
    return parsed


def parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise BuildError(f"{field} is not an ISO date") from exc


def require_https_url(value: str, field: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise BuildError(f"{field} must be an absolute HTTPS URL")
    return value


def evidence_id(change_id: str, evidence_kind: str, suffix: str | None = None) -> str:
    base = f"evidence-v1:{change_id}:{evidence_kind}"
    return f"{base}:{suffix}" if suffix else base


def validate_prior_timestamp(
    value: str, field: str, formation_timestamp: datetime
) -> None:
    if parse_timestamp(value, field) > formation_timestamp:
        raise BuildError(f"{field} is later than the formation timestamp")


def with_related_evidence_ids(
    *,
    change_id: str,
    formation_timestamp: datetime,
    current_filing_date: date,
    related_8ks: list[dict[str, Any]],
    related_news: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized_8ks: list[dict[str, Any]] = []
    seen_8k_ids: set[str] = set()
    for index, item in enumerate(related_8ks):
        field = f"change_related_8ks[{index}]"
        if not isinstance(item, dict):
            raise BuildError(f"{field} must be an object")
        accession = item.get("accession_number")
        if not isinstance(accession, str) or not accession:
            raise BuildError(f"{field}.accession_number is required")
        acceptance = item.get("acceptance_timestamp")
        if not isinstance(acceptance, str):
            raise BuildError(f"{field}.acceptance_timestamp is required")
        validate_prior_timestamp(
            acceptance, f"{field}.acceptance_timestamp", formation_timestamp
        )
        information_date = item.get("information_date")
        if not isinstance(information_date, str):
            raise BuildError(f"{field}.information_date is required")
        if parse_date(information_date, f"{field}.information_date") > current_filing_date:
            raise BuildError(f"{field}.information_date is after the filing date")
        url = item.get("url")
        if not isinstance(url, str):
            raise BuildError(f"{field}.url is required")
        require_https_url(url, f"{field}.url")
        item_evidence_id = evidence_id(change_id, "prior-8k", accession)
        if item_evidence_id in seen_8k_ids:
            raise BuildError(f"duplicate related 8-K evidence ID: {item_evidence_id}")
        seen_8k_ids.add(item_evidence_id)
        normalized_8ks.append({"evidence_id": item_evidence_id, **item})

    normalized_news: list[dict[str, Any]] = []
    seen_news_ids: set[str] = set()
    for index, item in enumerate(related_news):
        field = f"change_related_news[{index}]"
        if not isinstance(item, dict):
            raise BuildError(f"{field} must be an object")
        story_chain_id = item.get("story_chain_id")
        if not isinstance(story_chain_id, str) or not story_chain_id:
            raise BuildError(f"{field}.story_chain_id is required")
        publication = item.get("publication_timestamp")
        if not isinstance(publication, str):
            raise BuildError(f"{field}.publication_timestamp is required")
        validate_prior_timestamp(
            publication, f"{field}.publication_timestamp", formation_timestamp
        )
        item_evidence_id = evidence_id(change_id, "prior-news", story_chain_id.lower())
        if item_evidence_id in seen_news_ids:
            raise BuildError(f"duplicate related-news evidence ID: {item_evidence_id}")
        seen_news_ids.add(item_evidence_id)
        normalized_news.append({"evidence_id": item_evidence_id, **item})

    return normalized_8ks, normalized_news


def build_member(row: Mapping[str, str]) -> dict[str, Any]:
    case_order = parse_int(row["case_order"], "case_order", minimum=1)
    change_id = row["change_change_id"]
    ticker = row["change_ticker"]

    if row["featured_change_id"] != change_id:
        raise BuildError(f"case {case_order}: featured/change ID mismatch")
    if row["current_filing_id"] != row["change_current_filing_id"]:
        raise BuildError(f"case {case_order}: current filing ID mismatch")

    used_future_outcomes = parse_bool(
        row["selection_used_future_outcomes"], "selection_used_future_outcomes"
    )
    if used_future_outcomes:
        raise BuildError(f"case {case_order}: selection used future outcomes")

    filing_date = parse_date(
        row["change_current_filing_date"], "change_current_filing_date"
    )
    prior_filing_date = parse_date(
        row["change_prior_filing_date"], "change_prior_filing_date"
    )
    formation_timestamp = parse_timestamp(
        row["change_current_acceptance"], "change_current_acceptance"
    )
    prior_acceptance = parse_timestamp(
        row["change_prior_acceptance"], "change_prior_acceptance"
    )
    if prior_filing_date >= filing_date:
        raise BuildError(f"case {case_order}: prior filing date is not earlier")
    if prior_acceptance >= formation_timestamp:
        raise BuildError(f"case {case_order}: prior acceptance is not earlier")
    if formation_timestamp.date() < filing_date:
        raise BuildError(f"case {case_order}: formation precedes filing date")

    prior_start = parse_int(
        row["change_prior_start_offset"], "change_prior_start_offset", minimum=0
    )
    prior_end = parse_int(
        row["change_prior_end_offset"], "change_prior_end_offset", minimum=0
    )
    current_start = parse_int(
        row["change_current_start_offset"], "change_current_start_offset", minimum=0
    )
    current_end = parse_int(
        row["change_current_end_offset"], "change_current_end_offset", minimum=0
    )
    if prior_end <= prior_start or current_end <= current_start:
        raise BuildError(f"case {case_order}: invalid evidence offsets")

    changed_numbers = parse_json(
        row["change_changed_numbers"], "change_changed_numbers", dict
    )
    new_entities = parse_json(row["change_new_entities"], "change_new_entities", list)
    matched_terms = parse_json(row["change_matched_terms"], "change_matched_terms", list)
    related_8ks = parse_json(row["change_related_8ks"], "change_related_8ks", list)
    related_news = parse_json(row["change_related_news"], "change_related_news", list)
    related_8ks, related_news = with_related_evidence_ids(
        change_id=change_id,
        formation_timestamp=formation_timestamp,
        current_filing_date=filing_date,
        related_8ks=related_8ks,
        related_news=related_news,
    )

    provenance = parse_json(
        row["change_evidence_provenance"], "change_evidence_provenance", dict
    )
    if set(provenance) != PROVENANCE_SOURCE_KEYS:
        raise BuildError(
            f"case {case_order}: unexpected evidence-provenance schema"
        )
    document_hashes: dict[str, str] = {}
    for key in PROVENANCE_HASH_KEYS:
        value = provenance.get(key)
        if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
            raise BuildError(f"case {case_order}: invalid provenance hash {key}")
        document_hashes[key] = value

    current_sec_url = require_https_url(
        row["change_current_sec_url"], "change_current_sec_url"
    )
    prior_sec_url = require_https_url(
        row["change_prior_sec_url"], "change_prior_sec_url"
    )

    evidence_ids = {
        "prior_excerpt": evidence_id(change_id, "prior-10k-excerpt"),
        "current_excerpt": evidence_id(change_id, "current-10k-excerpt"),
        "added_text": evidence_id(change_id, "added-text"),
        "removed_text": evidence_id(change_id, "removed-text"),
    }

    member: dict[str, Any] = {
        "input_version": "1.0",
        "input_id": f"research-idea-input-v1:{change_id}",
        "case_order": case_order,
        "change_id": change_id,
        "issuer": row["change_company_name"],
        "ticker": ticker,
        "filing_date": row["change_current_filing_date"],
        "formation_timestamp": row["change_current_acceptance"],
        "section": row["change_section"],
        "source_url": current_sec_url,
        "selection": {
            "rationale": row["selection_rationale"],
            "used_future_outcomes": used_future_outcomes,
        },
        "identifiers": {
            "cik": row["change_cik"],
            "permno": row["change_permno"],
            "sector_code": row["change_sector_code"],
            "current_filing_id": row["change_current_filing_id"],
            "prior_filing_id": row["change_prior_filing_id"],
            "current_accession_number": row["change_current_accession_number"],
            "prior_accession_number": row["change_prior_accession_number"],
        },
        "prior_filing": {
            "filing_date": row["change_prior_filing_date"],
            "acceptance_timestamp": row["change_prior_acceptance"],
            "source_url": prior_sec_url,
        },
        "evidence": {
            "evidence_ids": evidence_ids,
            "prior_excerpt": row["change_prior_excerpt"],
            "current_excerpt": row["change_current_excerpt"],
            "added_text": row["change_added_text"],
            "removed_text": row["change_removed_text"],
            "offsets": {
                "prior": {"start": prior_start, "end": prior_end},
                "current": {"start": current_start, "end": current_end},
            },
            "changed_numbers": changed_numbers,
            "new_entities": new_entities,
            "related_prior_8k": related_8ks,
            "related_prior_news": related_news,
        },
        "frozen_classification": {
            "category": row["change_category"],
            "category_slug": row["change_category_slug"],
            "direction": row["change_direction"],
            "materiality": row["change_materiality"],
            "confidence": parse_float(
                row["change_confidence"],
                "change_confidence",
                minimum=0.0,
                maximum=1.0,
            ),
            "classification_method": row["change_classification_method"],
            "alignment_model": row["change_alignment_model"],
            "alignment_similarity": parse_float(
                row["change_alignment_similarity"],
                "change_alignment_similarity",
                minimum=0.0,
                maximum=1.0,
            ),
            "matched_terms": matched_terms,
        },
        "reason": {
            "code": row["change_category_slug"],
            "why_it_matters": row["change_why_it_matters"],
        },
        "novelty": {
            "classification": row["change_novelty_after_prior_disclosures"],
            "prior_8k_search_count": parse_int(
                row["change_prior_8k_search_count"],
                "change_prior_8k_search_count",
                minimum=0,
            ),
            "prior_news_search_count": parse_int(
                row["change_prior_news_search_count"],
                "change_prior_news_search_count",
                minimum=0,
            ),
            "method": row["change_novelty_method"],
        },
        "provenance": {"document_hashes": document_hashes},
    }
    member["member_sha256"] = sha256_bytes(canonical_json_bytes(member))
    return member


def walk_json(value: Any, *, path: str = "$") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield path, key, child
            yield from walk_json(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            if isinstance(child, (dict, list)):
                yield from walk_json(child, path=child_path)
            else:
                yield child_path, f"[{index}]", child


def audit_bundle(bundle: Mapping[str, Any]) -> dict[str, int]:
    forbidden_key_count = 0
    local_path_value_count = 0
    for path, key, value in walk_json(bundle):
        if key in FORBIDDEN_OUTPUT_KEYS:
            forbidden_key_count += 1
        if isinstance(value, str) and (
            WINDOWS_PATH_RE.search(value)
            or LOCAL_URI_RE.search(value)
            or POSIX_HOME_RE.search(value)
        ):
            local_path_value_count += 1
            raise BuildError(f"local filesystem path leaked at {path}.{key}")
    if forbidden_key_count:
        raise BuildError(f"bundle contains {forbidden_key_count} forbidden keys")

    inputs = bundle.get("inputs")
    if not isinstance(inputs, list) or len(inputs) != EXPECTED_ROW_COUNT:
        raise BuildError("bundle input count changed during construction")
    if len({member["input_id"] for member in inputs}) != len(inputs):
        raise BuildError("bundle contains duplicate input IDs")

    for member in inputs:
        expected_hash = member["member_sha256"]
        hash_input = {key: value for key, value in member.items() if key != "member_sha256"}
        if sha256_bytes(canonical_json_bytes(hash_input)) != expected_hash:
            raise BuildError(f"member hash mismatch for {member['input_id']}")

    manifest = "".join(
        f"{member['input_id']}\t{member['member_sha256']}\n" for member in inputs
    ).encode("utf-8")
    if sha256_bytes(manifest) != bundle["bundle_sha256"]:
        raise BuildError("bundle manifest hash mismatch")

    return {
        "forbidden_key_count": forbidden_key_count,
        "local_path_value_count": local_path_value_count,
        "member_hashes_verified": len(inputs),
    }


def load_locked_rows(source: Path) -> list[dict[str, str]]:
    if not source.is_file():
        raise BuildError(f"source file not found: {source}")
    actual_hash = sha256_file(source)
    if actual_hash != SOURCE_SHA256:
        raise BuildError(
            f"source SHA-256 mismatch: expected {SOURCE_SHA256}, got {actual_hash}"
        )

    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        if fieldnames[: len(ALLOWED_SOURCE_COLUMNS)] != ALLOWED_SOURCE_COLUMNS:
            raise BuildError(
                "source schema mismatch before the change_novelty_method cutoff"
            )
        rows = [
            {column: raw_row[column] for column in ALLOWED_SOURCE_COLUMNS}
            for raw_row in reader
        ]

    if len(rows) != EXPECTED_ROW_COUNT:
        raise BuildError(
            f"source row-count mismatch: expected {EXPECTED_ROW_COUNT}, got {len(rows)}"
        )
    rows.sort(key=lambda row: parse_int(row["case_order"], "case_order"))
    observed = tuple(
        (
            parse_int(row["case_order"], "case_order"),
            row["change_change_id"],
            row["change_ticker"],
        )
        for row in rows
    )
    if observed != EXPECTED_CASES:
        raise BuildError(
            "source case-order/change-ID/ticker membership does not match the lock"
        )
    return rows


def build_bundle(source: Path) -> tuple[dict[str, Any], dict[str, int]]:
    members = [build_member(row) for row in load_locked_rows(source)]
    manifest = "".join(
        f"{member['input_id']}\t{member['member_sha256']}\n" for member in members
    ).encode("utf-8")
    bundle: dict[str, Any] = {
        "bundle_version": "1.0",
        "bundle_kind": "bounded-eight-case-formation-time-inputs",
        "source": {
            "name": "case_studies.csv",
            "sha256": SOURCE_SHA256,
            "row_count": EXPECTED_ROW_COUNT,
            "allowed_column_cutoff": "change_novelty_method",
        },
        "formation_policy": {
            "formation_timestamp_field": "change_current_acceptance",
            "future_information_excluded": True,
            "local_provenance_paths_excluded": True,
            "selection_is_outcome_independent": True,
        },
        "member_hash_algorithm": "sha256(canonical-json-without-member_sha256)",
        "bundle_hash_algorithm": "sha256(ordered-input-id-tab-member-sha256-lf)",
        "case_count": len(members),
        "bundle_sha256": sha256_bytes(manifest),
        "inputs": members,
    }
    return bundle, audit_bundle(bundle)


def default_source() -> Path:
    workspace = Path(__file__).resolve().parents[2]
    return (
        workspace
        / "pure-news-disclosure-change-demo-v1"
        / "reports"
        / "tables"
        / "case_studies.csv"
    )


def default_output() -> Path:
    repository = Path(__file__).resolve().parents[1]
    return (
        repository
        / "demo"
        / "data"
        / "research_idea_inputs"
        / "v1"
        / "eight_case_inputs.json"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=default_source(),
        help="Locked authoritative case_studies.csv source",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output(),
        help="Destination JSON bundle",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = args.source.resolve()
    output = args.output.resolve()
    if source == output:
        raise BuildError("source and output paths must differ")

    bundle, audit = build_bundle(source)
    payload = json.dumps(
        bundle, ensure_ascii=False, allow_nan=False, indent=2
    ).encode("utf-8") + b"\n"

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, output)

    result = {
        "status": "PASS",
        "case_count": bundle["case_count"],
        "bundle_sha256": bundle["bundle_sha256"],
        "output_sha256": sha256_file(output),
        **audit,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
