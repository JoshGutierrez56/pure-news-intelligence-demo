"""Build the deterministic, metadata-only universe coverage preview.

This script reads only frozen repository artifacts. It performs no network
requests, filing-body downloads, inference, or research-idea generation.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEMO_DATA = ROOT / "demo" / "data"
OUTPUT_DIR = DEMO_DATA / "universe_preview"
AS_OF = "2024-12-31T23:59:59Z"
RECENT_8K_START = "2024-01-01"
SCHEMA_VERSION = "pure-news-universe-preview.v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_gzip_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(gzip.decompress(path.read_bytes()))


def normalize_cik(value: Any) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    if not digits or int(digits) == 0:
        return None
    return digits.zfill(10)


def normalize_ticker(value: Any) -> str | None:
    ticker = re.sub(r"\s+", "", str(value or "")).upper()
    return ticker or None


def accession_from_url(url: str) -> str | None:
    match = re.search(r"/data/\d+/(\d{18})/", url or "")
    if not match:
        return None
    raw = match.group(1)
    return f"{raw[:10]}-{raw[10:12]}-{raw[12:]}"


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def status_for(
    *,
    validated: bool,
    ticker: str | None,
    company_name: str | None,
    latest_10k_date: str | None,
    recent_8k_count: int,
    news_count: int | None,
) -> str:
    if validated:
        return "Fully validated"
    if not ticker or not company_name:
        return "Missing source coverage"
    if recent_8k_count > 0 and news_count is not None:
        return "Metadata indexed"
    if latest_10k_date or recent_8k_count > 0 or news_count is not None:
        return "Partial metadata"
    return "Not yet processed"


def build() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    catalog_path = DEMO_DATA / "catalog.json"
    changes_path = DEMO_DATA / "changes.json"
    ideas_manifest_path = DEMO_DATA / "research_ideas" / "v2" / "manifest.json"
    catalog = load_json(catalog_path)
    changes = load_json(changes_path)["records"]
    ideas_manifest = load_json(ideas_manifest_path)

    source_files = [catalog_path, changes_path, ideas_manifest_path]
    sec_records: list[dict[str, Any]] = []
    for partition in catalog["sources"]["sec"]["partitions"]:
        path = ROOT / "demo" / partition["path"]
        records = load_gzip_json(path)
        if len(records) != partition["records"]:
            raise ValueError(f"SEC partition count mismatch: {path}")
        sec_records.extend(records)
        source_files.append(path)

    news_by_ticker: Counter[str] = Counter()
    latest_news_by_ticker: dict[str, str] = {}
    for partition in catalog["sources"]["news"]["partitions"]:
        path = ROOT / "demo" / partition["path"]
        records = load_gzip_json(path)
        if len(records) != partition["records"]:
            raise ValueError(f"News partition count mismatch: {path}")
        for record in records:
            ticker = normalize_ticker(record.get("ticker"))
            if not ticker:
                continue
            news_by_ticker[ticker] += 1
            timestamp = str(record.get("date") or "")
            if timestamp > latest_news_by_ticker.get(ticker, ""):
                latest_news_by_ticker[ticker] = timestamp
        source_files.append(path)

    sec_by_cik: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in sec_records:
        cik = normalize_cik(record.get("cik"))
        if cik:
            sec_by_cik[cik].append(record)

    curated_10k_by_cik: dict[str, dict[str, Any]] = {}
    validated_ciks: set[str] = set()
    for change in changes:
        match = re.search(r"/data/(\d+)/", change.get("url") or "")
        cik = normalize_cik(match.group(1) if match else None)
        if not cik:
            continue
        validated_ciks.add(cik)
        candidate = {
            "date": change.get("date"),
            "accession": accession_from_url(change.get("url") or ""),
            "url": change.get("url"),
            "ticker": normalize_ticker(change.get("ticker")),
            "issuer": change.get("issuer"),
        }
        prior = curated_10k_by_cik.get(cik)
        if not prior or (
            str(candidate["date"] or ""),
            str(candidate["accession"] or ""),
        ) > (
            str(prior["date"] or ""),
            str(prior["accession"] or ""),
        ):
            curated_10k_by_cik[cik] = candidate

    idea_reviewed_tickers = {
        normalize_ticker(record.get("ticker"))
        for group in ("publishable", "safe_failures")
        for record in ideas_manifest[group]
    }

    issuer_records: list[dict[str, Any]] = []
    for cik in sorted(sec_by_cik):
        filings = sorted(
            sec_by_cik[cik],
            key=lambda row: (
                str(row.get("accepted") or row.get("date") or ""),
                str(row.get("id") or ""),
            ),
        )
        latest_identity = filings[-1]
        ticker = normalize_ticker(latest_identity.get("ticker"))
        company_name = str(latest_identity.get("issuer") or "").strip() or None
        curated = curated_10k_by_cik.get(cik)
        if not ticker and curated:
            ticker = curated["ticker"]
        if not company_name and curated:
            company_name = curated["issuer"]

        recent_8ks = [
            row for row in filings if str(row.get("date") or "") >= RECENT_8K_START
        ]
        news_count = news_by_ticker[ticker] if ticker in news_by_ticker else None
        latest_news = latest_news_by_ticker.get(ticker) if ticker else None
        validated = cik in validated_ciks
        status = status_for(
            validated=validated,
            ticker=ticker,
            company_name=company_name,
            latest_10k_date=curated["date"] if curated else None,
            recent_8k_count=len(recent_8ks),
            news_count=news_count,
        )

        missing_fields: list[str] = []
        missing_fields.extend(["sector", "industry"])
        if not ticker:
            missing_fields.append("ticker")
        if not company_name:
            missing_fields.append("company_name")
        if not curated:
            missing_fields.extend(
                ["latest_10k_date", "latest_10k_accession", "latest_10k_url"]
            )
        if not recent_8ks:
            missing_fields.append("recent_8k_metadata")
        if news_count is None:
            missing_fields.extend(
                ["news_metadata_count", "latest_news_timestamp"]
            )

        provenance = ["frozen_sec_8k_metadata_2012_2024"]
        if news_count is not None:
            provenance.append("permitted_news_metadata_2015_2024")
        if curated:
            provenance.append("curated_disclosure_change_demo")
        if ticker in idea_reviewed_tickers:
            provenance.append("bounded_research_idea_engine_v2")

        issuer_records.append(
            {
                "issuer_id": f"sec-cik-{cik}",
                "ticker": ticker,
                "company_name": company_name,
                "cik": cik,
                "sector": None,
                "industry": None,
                "latest_10k_date": curated["date"] if curated else None,
                "latest_10k_accession": curated["accession"] if curated else None,
                "latest_10k_url": curated["url"] if curated else None,
                "recent_8k_count": len(recent_8ks),
                "latest_8k_date": str(filings[-1].get("date") or "") or None,
                "news_metadata_count": news_count,
                "latest_news_timestamp": latest_news,
                "processing_status": status,
                "validated_demo_status": (
                    "Research Idea Engine reviewed"
                    if ticker in idea_reviewed_tickers
                    else (
                        "Disclosure Change Engine validated"
                        if validated
                        else "Not validated in current demo"
                    )
                ),
                "missing_fields": missing_fields,
                "source_provenance": provenance,
                "as_of_timestamp": AS_OF,
            }
        )

    if len({row["issuer_id"] for row in issuer_records}) != len(issuer_records):
        raise ValueError("Duplicate issuer_id after deterministic de-duplication")

    status_counts = Counter(row["processing_status"] for row in issuer_records)
    missing_counts = Counter(
        field for row in issuer_records for field in row["missing_fields"]
    )
    summary = {
        "schema": f"{SCHEMA_VERSION}.summary",
        "as_of_timestamp": AS_OF,
        "universe_label": "Broad U.S. public-company coverage preview",
        "total_issuers_indexed": len(issuer_records),
        "issuers_with_10k_metadata": sum(
            row["latest_10k_date"] is not None for row in issuer_records
        ),
        "issuers_with_recent_8k_metadata": sum(
            row["recent_8k_count"] > 0 for row in issuer_records
        ),
        "issuers_with_permitted_news_metadata": sum(
            row["news_metadata_count"] is not None for row in issuer_records
        ),
        "issuers_fully_validated": status_counts["Fully validated"],
        "issuers_not_yet_processed": status_counts["Not yet processed"],
        "issuers_indexed_but_not_fully_validated": sum(
            row["processing_status"] != "Fully validated" for row in issuer_records
        ),
        "processing_status_counts": dict(sorted(status_counts.items())),
        "missing_data_counts": dict(sorted(missing_counts.items())),
        "recent_8k_window": {
            "start": RECENT_8K_START,
            "end": "2024-12-31",
        },
        "boundary": (
            "Metadata indexing does not mean completed disclosure-change analysis "
            "or Research Idea Engine review."
        ),
    }
    coverage = {
        "schema": f"{SCHEMA_VERSION}.coverage",
        "as_of_timestamp": AS_OF,
        "records": issuer_records,
    }
    source_manifest = {
        "schema": f"{SCHEMA_VERSION}.sources",
        "as_of_timestamp": AS_OF,
        "universe_definition": {
            "label": "Broad U.S. public-company coverage preview",
            "source": "Unique CIKs observed in the frozen parsed SEC 8-K metadata corpus",
            "source_date_range": ["2012-01-03", "2024-12-31"],
            "filters": [
                "valid non-zero CIK",
                "latest SEC record supplies canonical issuer name and ticker",
                "one deterministic record per normalized CIK",
            ],
            "issuer_count": len(issuer_records),
            "index_membership_claim": None,
        },
        "sources": [
            {
                "id": "frozen_sec_8k_metadata_2012_2024",
                "description": catalog["boundaries"]["sec"]["description"],
                "records": len(sec_records),
                "body_surface": catalog["boundaries"]["sec"]["bodySurface"],
            },
            {
                "id": "permitted_news_metadata_2015_2024",
                "description": catalog["boundaries"]["news"]["description"],
                "records": sum(news_by_ticker.values()),
                "body_surface": catalog["boundaries"]["news"]["bodySurface"],
            },
            {
                "id": "curated_disclosure_change_demo",
                "description": "Frozen curated 10-K change records",
                "records": len(changes),
                "unique_issuers_in_public_records": len(validated_ciks),
            },
            {
                "id": "bounded_research_idea_engine_v2",
                "description": "Eight bounded frozen review outcomes",
                "records": len(idea_reviewed_tickers),
            },
        ],
        "input_hashes_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
            for path in sorted(set(source_files))
        },
        "rights_and_exclusions": [
            "Public SEC metadata and links only; filing bodies are not duplicated.",
            "Permitted news metadata only; article bodies are excluded.",
            "No live API call is made by the builder or public preview.",
        ],
    }

    coverage_bytes = canonical_json(coverage)
    summary_bytes = canonical_json(summary)
    source_bytes = canonical_json(source_manifest)
    build_receipt = {
        "schema": f"{SCHEMA_VERSION}.build-receipt",
        "builder": "scripts/build_universe_preview.py",
        "builder_sha256": sha256(Path(__file__)),
        "as_of_timestamp": AS_OF,
        "deterministic_sort": "normalized CIK ascending",
        "output_hashes_sha256": {
            "universe_coverage.json": hashlib.sha256(coverage_bytes).hexdigest(),
            "universe_summary.json": hashlib.sha256(summary_bytes).hexdigest(),
            "source_manifest.json": hashlib.sha256(source_bytes).hexdigest(),
        },
        "validation": {
            "duplicate_issuer_ids": 0,
            "input_partition_count_mismatches": 0,
            "network_calls": 0,
            "filing_bodies_downloaded": 0,
            "article_bodies_included": 0,
            "research_ideas_generated": 0,
        },
    }
    return coverage, summary, source_manifest, build_receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if committed outputs differ from a deterministic rebuild.",
    )
    args = parser.parse_args()
    values = build()
    names = (
        "universe_coverage.json",
        "universe_summary.json",
        "source_manifest.json",
        "build_receipt.json",
    )
    outputs = {name: canonical_json(value) for name, value in zip(names, values)}
    if args.check:
        for name, expected in outputs.items():
            path = OUTPUT_DIR / name
            if not path.exists() or path.read_bytes() != expected:
                raise SystemExit(f"Deterministic output mismatch: {path}")
        return
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in outputs.items():
        (OUTPUT_DIR / name).write_bytes(payload)


if __name__ == "__main__":
    main()
