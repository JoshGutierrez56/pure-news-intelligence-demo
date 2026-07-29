from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from assign_novelty_v2 import NOVELTY_TAXONOMY, assign_novelty
from decompose_atomic_claims import decompose_statement
from normalize_financial_quantities import (
    comparison_compatibility,
    normalize_financial_quantities,
)
from search_counterevidence import search_counterevidence
from validate_research_idea_packets_v2 import packet_hash


FIXTURE_PATH = (
    ROOT / "tests" / "fixtures" / "research_idea_v2" / "novelty_role_fixtures.json"
)
PACKET_DIR = ROOT / "data" / "research_idea_packets" / "v2"
INDEX_DIR = ROOT / "data" / "research_idea_evidence_index" / "v2"
EXPECTED_CASES = {
    "dbe75bc24f2888f4166a": "TFC",
    "8f5336b55618ffe68e8a": "KHC",
    "339fae2941721ee094b0": "DLTR",
    "4784f62ad001b2a12af4": "DVN",
    "412b08746bb0ed5a7745": "RH",
    "8d4598f4ea16f15c7048": "FCX",
    "279e7d4e407851a19548": "EFX",
    "2f22dc2216c9df31d377": "CHE",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_fixture_inventory_is_frozen_before_real_rerun():
    fixtures = load_json(FIXTURE_PATH)
    assert fixtures["frozen_before_real_case_rerun"] is True
    assert len(fixtures["fixtures"]) == 16
    assert fixtures["fixtures"][0]["fixture_id"] == "efx-negative-regression"
    assert len({item["fixture_id"] for item in fixtures["fixtures"]}) == 16


def test_atomic_claim_decomposition_separates_hidden_propositions():
    claims = decompose_statement(
        "A conditional obligation exists and the obligation creates liquidity stress.",
        source_evidence_ids=["EV-1"],
        source_path="/claim",
    )
    assert len(claims) == 2
    assert all(item["source_evidence_ids"] == ["EV-1"] for item in claims)
    assert claims[0]["exact_wording"] != claims[1]["exact_wording"]


@pytest.mark.parametrize(
    ("text", "amount", "role"),
    [
        (
            "The remaining $346.7 million will be paid after final adjudication.",
            346700000.0,
            "remaining balance",
        ),
        (
            "The company could fund up to an additional $125 million if the fund is exhausted.",
            125000000.0,
            "conditional top-up",
        ),
        (
            "The company deposited approximately $345 million into the settlement fund.",
            345000000.0,
            "cash deposit",
        ),
    ],
)
def test_financial_role_normalization(text, amount, role):
    quantities = normalize_financial_quantities(text)
    assert any(
        item["normalized_amount"] == amount and item["financial_role"] == role
        for item in quantities
    )


def test_incompatible_quantity_detection():
    left = normalize_financial_quantities(
        "The remaining $346.7 million will be paid."
    )[0]
    right = normalize_financial_quantities(
        "The company could fund up to an additional $125 million if claims increase."
    )[0]
    result = comparison_compatibility(left, right)
    assert result["status"] == "INCOMPARABLE_QUANTITIES"
    assert "financial_role" in result["conflicts"]
    assert "conditionality" in result["conflicts"]


def test_novelty_taxonomy_is_complete():
    expected = {
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
    assert NOVELTY_TAXONOMY == expected


def test_efx_full_prior_search_finds_omitted_top_up():
    index = load_json(INDEX_DIR / "279e7d4e407851a19548.json")
    claim = {
        "exact_wording": (
            "The company could be obligated to fund up to an additional "
            "$125 million if the consumer fund is exhausted."
        )
    }
    prior = [
        span
        for span in index["spans"]
        if span["source_type"] != "SEC_10_K_CURRENT"
    ]
    result = assign_novelty(claim, prior_spans=prior, current_spans=[])
    assert result["status"] == "PREVIOUSLY_DISCLOSED_IN_10K"
    assert (
        result["display_excerpt_status"]
        == "DISPLAY_EXCERPT_OMITTED_PRIOR_EVIDENCE"
    )
    assert result["earliest_identified_prior_occurrence"] is not None


def test_counterevidence_search_is_deterministic():
    spans = [
        {
            "evidence_id": "EV-1",
            "source_type": "SEC_10_K",
            "filing_date": "2020-01-01",
            "acceptance_timestamp": "2020-01-01T00:00:00Z",
            "section": "item_1a",
            "paragraph_number": 1,
            "text": "Management does not believe an additional deposit will be required.",
            "outside_display_excerpt": True,
        }
    ]
    claim = {"exact_wording": "An additional deposit will be required."}
    assert search_counterevidence(claim, spans=spans) == search_counterevidence(
        claim, spans=copy.deepcopy(spans)
    )


def test_evidence_index_is_complete_and_point_in_time():
    receipt = load_json(
        ROOT / "artifacts" / "research_idea_evidence_index_v2_receipt.json"
    )
    assert receipt["issuer_count"] == 8
    assert receipt["filings_indexed"] >= 16
    assert receipt["paragraphs_indexed"] > 0
    assert receipt["failed_extraction_count"] == 0
    assert receipt["timing_violation_count"] == 0
    assert receipt["full_prior_filing_search_completed"] is True


def test_v2_packet_set_is_exact_and_hashes_validate():
    index = load_json(PACKET_DIR / "index.json")
    assert index["packet_count"] == 8
    assert {item["change_id"]: item["ticker"] for item in index["packets"]} == EXPECTED_CASES
    for entry in index["packets"]:
        packet = load_json(PACKET_DIR / f"{entry['change_id']}.json")
        assert packet_hash(packet) == packet["packet_hash"] == entry["packet_hash"]
        public = ROOT / "demo" / "data" / "research_idea_packets" / "v2" / f"{entry['change_id']}.json"
        assert public.read_bytes() == (PACKET_DIR / f"{entry['change_id']}.json").read_bytes()


def test_all_v2_packets_validate_against_frozen_schema():
    atomic = load_json(ROOT / "schemas" / "atomic_evidence_claim_v2.schema.json")
    schema = load_json(ROOT / "schemas" / "research_idea_packet_v2.schema.json")
    schema["properties"]["atomic_claims"]["items"] = atomic
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for path in PACKET_DIR.glob("*.json"):
        if path.name == "index.json":
            continue
        errors = list(validator.iter_errors(load_json(path)))
        assert not errors, [error.message for error in errors]


def test_efx_negative_regression_is_permanent():
    packet = load_json(PACKET_DIR / "279e7d4e407851a19548.json")
    assert packet["packet_status"] == "REJECT_MISLEADING_COMPARISON"
    assert packet["skeptic_review"]["status"] == "REJECT_MISLEADING_COMPARISON"
    assert packet["novelty_review"]["final_novelty"] == "RESOLVED_OR_FINALIZED_PRIOR_UNCERTAINTY"
    assert packet["illustrative_trade_hypothesis"]["candidate_view"] == "no actionable view"
    top_up = next(
        item for item in packet["atomic_claims"] if "$125 million" in item["exact_wording"]
    )
    assert top_up["novelty_status"] == "PREVIOUSLY_DISCLOSED_IN_10K"
    assert top_up["novelty_review"]["display_excerpt_status"] == "DISPLAY_EXCERPT_OMITTED_PRIOR_EVIDENCE"
    forbidden = " ".join(item["exact_wording"] for item in packet["atomic_claims"]).lower()
    assert "not adequately reserved" not in forbidden
    assert "bondholder" not in forbidden


def test_publishable_packets_meet_strict_coverage_gate():
    packets = [
        load_json(path)
        for path in PACKET_DIR.glob("*.json")
        if path.name != "index.json"
    ]
    published = [item for item in packets if item["packet_status"] == "PUBLISHABLE"]
    assert {item["ticker"] for item in published} == {"DVN", "RH"}
    for packet in published:
        assert packet["evidence_coverage"]["evidence_coverage_ratio"] == 1.0
        assert packet["evidence_coverage"]["contradicted_factual_claims"] == 0
        assert packet["evidence_coverage"]["unresolved_critical_numeric_role_conflicts"] == 0
        assert packet["evidence_coverage"]["missing_counterevidence_searches"] == 0
        assert packet["skeptic_review"]["status"] == "PASS_HYPOTHESIS_ONLY"
        assert packet["research_hypotheses"]
        assert packet["illustrative_trade_hypothesis"]["status"] == "NOT_READY"


def test_v1_and_efx_review_preservation():
    receipt = load_json(ROOT / "artifacts" / "research_idea_engine_v2_start_receipt.json")
    for change_id, expected in receipt["v1_packet_hashes"].items():
        path = ROOT / "data" / "research_idea_packets" / "v1" / f"{change_id}.json"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    for relative, expected in receipt["efx_review_hashes"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_prompts_and_packets_exclude_prohibited_action_language():
    blocked = ("price target", "position size", "leverage instruction", "personalized allocation")
    paths = [
        ROOT / "prompts" / "research_idea_generator_v2.md",
        ROOT / "prompts" / "research_idea_skeptic_v2.md",
        *[
            path
            for path in PACKET_DIR.glob("*.json")
            if path.name != "index.json"
        ],
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        if "prompts" in path.parts:
            continue
        assert not any(term in text for term in blocked)


def test_no_future_data_keys_in_v2_packets():
    forbidden = {
        "outcome",
        "later_return",
        "abnormal_return_6m",
        "abnormal_return_12m",
        "maximum_drawdown_12m",
        "realized_volatility_12m",
    }
    for path in PACKET_DIR.glob("*.json"):
        keys: set[str] = set()

        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    keys.add(key)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(load_json(path))
        assert not (keys & forbidden)
