from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "demo" / "data" / "research_ideas" / "v2"
SOURCE_DIR = ROOT / "data" / "research_idea_packets" / "v2"
START_RECEIPT = json.loads(
    (ROOT / "artifacts" / "research_idea_public_demo_start_receipt.json").read_text(
        encoding="utf-8"
    )
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_public_safe_file_set_is_bounded():
    assert sorted(path.name for path in PUBLIC_DIR.glob("*.json")) == [
        "dvn.json",
        "efx_rejection.json",
        "manifest.json",
        "rh.json",
    ]


def test_manifest_reconciles_to_validated_bounded_result():
    manifest = load(PUBLIC_DIR / "manifest.json")
    assert manifest["summary"] == {
        "actionable_trade_views": 0,
        "broader_generation": "BLOCKED",
        "cases_reviewed": 8,
        "publishable_hypotheses": 2,
        "published_packet_evidence_coverage_ratio": 1.0,
        "safe_failures": 6,
    }
    assert [item["ticker"] for item in manifest["publishable"]] == ["RH", "DVN"]
    assert [item["ticker"] for item in manifest["safe_failures"]] == [
        "EFX",
        "CHE",
        "DLTR",
        "FCX",
        "KHC",
        "TFC",
    ]
    assert manifest["new_packet_generation_performed"] is False
    assert manifest["human_review_status"].endswith(
        "Formal blinded human ratings remain pending."
    )


def test_public_manifest_hashes_match_public_files_and_frozen_sources():
    manifest = load(PUBLIC_DIR / "manifest.json")
    for filename, record in manifest["public_files"].items():
        assert sha256(PUBLIC_DIR / filename) == record["sha256"]
        source_name = {
            "rh.json": "412b08746bb0ed5a7745.json",
            "dvn.json": "4784f62ad001b2a12af4.json",
            "efx_rejection.json": "279e7d4e407851a19548.json",
        }[filename]
        assert sha256(SOURCE_DIR / source_name) == record["source_packet_file_sha256"]


def test_all_v1_and_v2_packet_files_remain_immutable():
    for version in ("v1", "v2"):
        expected = START_RECEIPT[f"{version}_packet_file_hashes_sha256"]
        for change_id, digest in expected.items():
            path = ROOT / "data" / "research_idea_packets" / version / f"{change_id}.json"
            assert sha256(path) == digest


def test_other_frozen_files_remain_immutable():
    for relative, digest in START_RECEIPT[
        "other_frozen_file_hashes_sha256"
    ].items():
        assert sha256(ROOT / relative) == digest


def test_publishable_public_packets_preserve_grounding_boundaries():
    for filename, ticker in (("rh.json", "RH"), ("dvn.json", "DVN")):
        packet = load(PUBLIC_DIR / filename)
        assert packet["identity"]["ticker"] == ticker
        assert packet["kind"] == "publishable_hypothesis"
        assert packet["publication"]["evidence_coverage_ratio"] == 1.0
        assert packet["publication"]["skeptic_status"] == "PASS_HYPOTHESIS_ONLY"
        assert packet["publication"]["trade_readiness"] == "NOT_READY"
        assert packet["trade_research"]["status"] == "NO_ACTIONABLE_TRADE_VIEW"
        assert packet["source_evidence"]["full_prior_filing_evidence_checked"] is True
        assert packet["research_hypotheses"][0]["future_outcome_validation"] == "NOT_PERFORMED"
        assert packet["research_hypotheses"][0]["falsification_conditions"]
        assert packet["affected_entities_and_instruments"]["grounded_relationships"] == []
        assert packet["scenarios"]["bull"] is None


def test_efx_public_rejection_is_exact_negative_fixture():
    packet = load(PUBLIC_DIR / "efx_rejection.json")
    review = packet["full_prior_evidence_review"]
    roles = {item["amount"]: item for item in review["quantity_roles"]}
    assert roles["$125M"] == {
        "amount": "$125M",
        "correct_role": "Conditional top-up",
        "novelty_result": "PREVIOUSLY_DISCLOSED_IN_10K",
    }
    assert roles["$346.7M"]["correct_role"] == "Remaining payment balance"
    assert roles["$346.7M"]["novelty_result"] == "Not an exposure cap"
    assert roles["~$345M"]["correct_role"] == "Cash deposit"
    assert review["comparison_status"] == "INCOMPARABLE_QUANTITIES"
    assert packet["final_result"]["rejected_claims"] == [
        "Reserve inadequacy",
        "Current liquidity stress",
        "Bondholder impact",
    ]
    assert packet["final_result"]["trade_research_status"] == "NO_ACTIONABLE_TRADE_VIEW"


def test_public_safe_data_contains_no_private_or_future_payloads():
    blocked_keys = {
        "analyst_notes",
        "review_timestamp",
        "outcome",
        "future_return",
        "realized_pnl",
        "chain_of_thought",
        "hidden_reasoning",
    }
    blocked_patterns = (
        re.compile(r"[A-Za-z]:\\"),
        re.compile(r"/Users/"),
        re.compile(r"file://", re.I),
    )

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                assert key.lower() not in blocked_keys
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)
        elif isinstance(value, str):
            yield value

    for path in PUBLIC_DIR.glob("*.json"):
        for value in walk(load(path)):
            assert not any(pattern.search(value) for pattern in blocked_patterns)


def test_public_positioning_avoids_prohibited_product_names():
    prohibited = (
        "Trade Recommendation Engine",
        "AI Stock Picker",
        "Alpha Generator",
        "Buy/Sell Signal",
        "Investment Recommendation",
        "Automated Portfolio Manager",
    )
    paths = [
        ROOT / "demo" / "research_ideas.html",
        ROOT / "demo" / "research_idea_rh.html",
        ROOT / "demo" / "research_idea_dvn.html",
        ROOT / "demo" / "research_idea_efx.html",
        ROOT / "demo" / "research_idea_methodology.html",
        ROOT / "demo" / "assets" / "research_ideas.js",
        *PUBLIC_DIR.glob("*.json"),
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8").casefold()
        assert not any(phrase.casefold() in text for phrase in prohibited)


def test_public_routes_exist_and_use_relative_assets():
    routes = [
        "research_ideas.html",
        "research_idea_rh.html",
        "research_idea_dvn.html",
        "research_idea_efx.html",
        "research_idea_methodology.html",
    ]
    for route in routes:
        text = (ROOT / "demo" / route).read_text(encoding="utf-8")
        assert 'href="assets/style.css"' in text
        assert "http://localhost" not in text
        assert "127.0.0.1" not in text


def test_public_builder_is_deterministic():
    before = {path.name: sha256(path) for path in PUBLIC_DIR.glob("*.json")}
    subprocess.run(
        ["python", "scripts/build_public_research_ideas.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    after = {path.name: sha256(path) for path in PUBLIC_DIR.glob("*.json")}
    assert after == before


def test_p3_pages_reconcile_public_claims_and_routes():
    pages = {
        "index.html": (
            "Turn a Verified Change into a Testable Research Question",
            "<strong>8</strong><span>cases reviewed",
            "<strong>2</strong><span>publishable hypotheses",
            "<strong>6</strong><span>safe failures",
            "<strong>0</strong><span>actionable trade views",
        ),
        "demo/assets/site.js": (
            "Research Idea Engine V2",
            "READY_FOR_PUBLIC_DEMO",
            "60-case phase remains blocked",
        ),
        "demo/methodology.html": ("How Research Ideas Are Grounded",),
        "demo/innovation_framework.html": ("A research-question layer, governed by safe refusal",),
        "demo/pilot_plan.html": ("Only after hypotheses are frozen prospectively",),
        "demo/case_studies.html": ("Three Outcomes the Engine Can Produce",),
    }
    for relative, phrases in pages.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for phrase in phrases:
            assert phrase in text


def test_p3_shared_navigation_and_no_live_generation():
    pages = (
        ROOT / "index.html",
        ROOT / "demo/professor_presentation.html",
        ROOT / "demo/ranked_change_feed.html",
        ROOT / "demo/case_studies.html",
        ROOT / "demo/research_results.html",
        ROOT / "demo/methodology.html",
        ROOT / "demo/innovation_framework.html",
        ROOT / "demo/pilot_plan.html",
        ROOT / "demo/professor_materials.html",
    )
    for path in pages:
        text = path.read_text(encoding="utf-8")
        if path.name != "research_results.html":
            assert "research_ideas.html" in text
            assert "Research Ideas" in text
    assert 'location.pathname.endsWith("/research_results.html")' in (
        ROOT / "demo/assets/site.js"
    ).read_text(encoding="utf-8")
    assert "Generate Research Idea" not in (
        ROOT / "demo/assets/feed.js"
    ).read_text(encoding="utf-8")


def test_readme_documents_frozen_public_architecture():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for phrase in (
        "Experimental Research Idea Engine",
        "demo/research_ideas.html",
        "public-safe layer",
        "browser-local storage",
        "does not run live model inference",
        "Broader scaling remains blocked",
    ):
        assert phrase in text


def test_deployment_is_unchanged_before_p5():
    result = subprocess.run(
        ["git", "rev-parse", "origin/gh-pages"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "74ec311a7eaf3e848ef242da4f5a8a4ff7b1613a"
