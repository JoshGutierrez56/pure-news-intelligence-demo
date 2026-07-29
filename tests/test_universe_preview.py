from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "demo" / "data" / "universe_preview"
START = json.loads(
    (ROOT / "artifacts" / "pure_news_final_polish_start_receipt.json").read_text(
        encoding="utf-8"
    )
)
spec = importlib.util.spec_from_file_location(
    "build_universe_preview", ROOT / "scripts" / "build_universe_preview.py"
)
builder = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(builder)


def load(name: str):
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_universe_is_deterministic_and_has_expected_issuer_count():
    subprocess.run(
        ["python", "scripts/build_universe_preview.py", "--check"],
        cwd=ROOT,
        check=True,
    )
    coverage = load("universe_coverage.json")
    assert len(coverage["records"]) == 6190
    assert [row["cik"] for row in coverage["records"]] == sorted(
        row["cik"] for row in coverage["records"]
    )


def test_duplicate_removal_and_identifier_normalization():
    records = load("universe_coverage.json")["records"]
    assert len({row["issuer_id"] for row in records}) == len(records)
    assert all(row["issuer_id"] == f"sec-cik-{row['cik']}" for row in records)
    assert all(len(row["cik"]) == 10 and row["cik"].isdigit() for row in records)
    assert all(row["ticker"] is None or row["ticker"] == row["ticker"].upper() for row in records)


def test_latest_10k_and_recent_8k_are_selected_correctly():
    records = {row["ticker"]: row for row in load("universe_coverage.json")["records"]}
    efx = records["EFX"]
    assert efx["latest_10k_date"] == "2022-02-24"
    assert efx["latest_10k_accession"] == "0000033185-22-000014"
    assert efx["latest_10k_url"].startswith("https://www.sec.gov/Archives/")
    assert efx["recent_8k_count"] == 5
    assert efx["latest_8k_date"] == "2024-11-08"


def test_missing_news_is_not_zero_and_provenance_is_complete():
    records = load("universe_coverage.json")["records"]
    unavailable = [row for row in records if row["news_metadata_count"] is None]
    assert len(unavailable) == 5414
    assert all("news_metadata_count" in row["missing_fields"] for row in unavailable)
    assert all(row["source_provenance"] for row in records)
    assert all("frozen_sec_8k_metadata_2012_2024" in row["source_provenance"] for row in records)


def test_status_assignment_and_summary_reconcile():
    coverage = load("universe_coverage.json")
    summary = load("universe_summary.json")
    statuses = {}
    for row in coverage["records"]:
        statuses[row["processing_status"]] = statuses.get(row["processing_status"], 0) + 1
    assert statuses == summary["processing_status_counts"]
    assert summary["total_issuers_indexed"] == 6190
    assert summary["issuers_with_10k_metadata"] == 149
    assert summary["issuers_with_recent_8k_metadata"] == 3072
    assert summary["issuers_with_permitted_news_metadata"] == 776
    assert summary["issuers_fully_validated"] == 149
    assert summary["issuers_not_yet_processed"] == 2973
    assert summary["issuers_indexed_but_not_fully_validated"] == 6041


def test_output_hashes_and_source_manifest_reconcile():
    receipt = load("build_receipt.json")
    for name, digest in receipt["output_hashes_sha256"].items():
        assert sha256(OUTPUT / name) == digest
    manifest = load("source_manifest.json")
    assert manifest["universe_definition"]["index_membership_claim"] is None
    assert manifest["universe_definition"]["issuer_count"] == 6190
    assert manifest["sources"][1]["body_surface"].startswith("headline")


def test_public_data_is_metadata_only():
    text = (OUTPUT / "universe_coverage.json").read_text(encoding="utf-8")
    for prohibited in (
        "article_body",
        "filing_body",
        "chain_of_thought",
        "future_return",
        "realized_pnl",
        "Russell 3000",
    ):
        assert prohibited not in text


def test_frozen_artifacts_and_deployment_remain_unchanged():
    for version in ("v1", "v2"):
        for change_id, digest in START[f"frozen_{version}_packet_hashes_sha256"].items():
            assert sha256(
                ROOT / "data" / "research_idea_packets" / version / f"{change_id}.json"
            ) == digest
    for relative, digest in START["other_frozen_hashes_sha256"].items():
        assert sha256(ROOT / relative) == digest
    result = subprocess.run(
        ["git", "rev-parse", "origin/gh-pages"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "61c50b0b0f8d95ea9b39edd2a2b02d451ef9890f"
