from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START = json.loads(
    (ROOT / "artifacts" / "pure_news_final_polish_start_receipt.json").read_text(
        encoding="utf-8"
    )
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_share_package_is_complete():
    expected = {
        "PROJECT_OVERVIEW.md",
        "ONE_PAGE_SUMMARY.md",
        "DEMO_GUIDE.md",
        "FAQ.md",
        "KNOWN_LIMITATIONS.md",
        "FUTURE_RESEARCH.md",
        "RESEARCH_CLAIMS.md",
        "RELEASE_NOTES_v1.0.0.md",
    }
    assert {path.name for path in (ROOT / "share").glob("*.md")} == expected


def test_public_trust_routes_exist():
    for name in (
        "faq.html",
        "known_limitations.html",
        "future_research.html",
        "public_architecture.html",
    ):
        assert (ROOT / "demo" / name).is_file()


def test_repository_documentation_is_complete():
    for name in (
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CITATION.cff",
        "LICENSE_STATUS.md",
    ):
        assert (ROOT / name).is_file()


def test_locked_claims_are_reconciled_in_share_package():
    claims = (ROOT / "share" / "RESEARCH_CLAIMS.md").read_text(encoding="utf-8")
    for phrase in (
        "Eight Research Idea Engine cases",
        "RH and DVN",
        "Six cases failed safely",
        "Zero actionable trade views",
        "Formal blinded human ratings: pending",
        "60-case phase: blocked and not run",
        "Sharpe-ratio improvement",
        "Information-coefficient improvement",
    ):
        assert phrase in claims


def test_frozen_packets_and_locked_sources_remain_unchanged():
    for version in ("v1", "v2"):
        for change_id, digest in START[f"frozen_{version}_packet_hashes_sha256"].items():
            assert sha256(
                ROOT / "data" / "research_idea_packets" / version / f"{change_id}.json"
            ) == digest
    for relative, digest in START["other_frozen_hashes_sha256"].items():
        assert sha256(ROOT / relative) == digest


def test_public_manifest_byte_hash_remains_exact():
    assert (
        sha256(ROOT / "demo" / "data" / "research_ideas" / "v2" / "manifest.json")
        == START["public_manifest_sha256"]
    )


def test_no_release_or_deployment_claim_is_added():
    release_notes = (ROOT / "share" / "RELEASE_NOTES_v1.0.0.md").read_text(
        encoding="utf-8"
    )
    assert "not automatically tagged, released, or deployed" in release_notes
