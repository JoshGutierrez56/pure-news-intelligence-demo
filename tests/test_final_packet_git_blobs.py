from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = ROOT / "demo" / "data" / "research_ideas" / "v2"
CANONICAL = {
    "rh.json": {
        "raw": "684dfea02feaeb76d8a3de134118e18a8bfe192216757a8c127cf6fa5b1e5585",
        "semantic": "7ad8dfa3c196950ca78ef18410b452c6256c90711077282ed7c020df0ebcf750",
    },
    "dvn.json": {
        "raw": "103b1894bba6fb1ed3ed82e907315e92f3c749262c65aeaed1a0a4b7db6db655",
        "semantic": "9e9ae28abf9aaa27f7a206613bfb71756c25982d7ccf89ff7dc805d2e5982a9c",
    },
    "efx_rejection.json": {
        "raw": "e92004321017a148b8f88df832d7b535ca90535e8e0b94c1e9988e96ba8d388c",
        "semantic": "a5229d3f4864b4ee61a66ca602a91308720dfc96bc9a6115c8665ee4fd1550d2",
    },
}
UNCHANGED_PUBLIC_ASSETS = {
    "demo/data/research_ideas/v2/manifest.json":
        "1611006a6a85fa9702846b22af4a957d2a2d2d0597123f7615d65bf71077f2d7",
    "demo/data/universe_preview/build_receipt.json":
        "8baaa7f4bb1c2a15a4a300e19492011759772186a83fae9a9ea8f033fe0bc6ac",
    "demo/data/universe_preview/source_manifest.json":
        "8b896467a719c4f2fb23eacdeb8166239740cd300f7517c82a619b53461f94cb",
    "demo/data/universe_preview/universe_coverage.json":
        "9a5930919767b8295ea82c47109935529e2406ad5b0ecab10d5a029b88e35628",
    "demo/data/universe_preview/universe_summary.json":
        "09f35d5ce2f1f8ffbe6a0a357b0b848875d687c94e1d0e8f3d329c388d04d7a2",
}


def git_blob(spec: str) -> bytes:
    return subprocess.run(
        ["git", "show", spec],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def semantic_digest(raw: bytes) -> str:
    parsed = json.loads(raw.decode("utf-8"))
    canonical = json.dumps(
        parsed,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return digest(canonical)


def test_committed_index_and_worktree_packet_bytes_are_canonical():
    for name, expected in CANONICAL.items():
        relative = f"demo/data/research_ideas/v2/{name}"
        committed = git_blob(f"HEAD:{relative}")
        staged = git_blob(f":{relative}")
        working = (ROOT / relative).read_bytes()
        assert digest(committed) == expected["raw"]
        assert staged == committed
        assert working == committed
        assert semantic_digest(committed) == expected["semantic"]


def test_manifest_declares_the_same_canonical_packet_hashes():
    manifest = json.loads((PACKET_DIR / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in CANONICAL.items():
        assert manifest["public_files"][name]["sha256"] == expected["raw"]


def test_rh_and_dvn_semantics_remain_hypothesis_only():
    for name in ("rh.json", "dvn.json"):
        packet = json.loads(git_blob(f"HEAD:demo/data/research_ideas/v2/{name}"))
        assert packet["publication"]["skeptic_status"] == "PASS_HYPOTHESIS_ONLY"
        assert packet["publication"]["evidence_coverage_ratio"] == 1.0
        assert packet["trade_research"]["status"] == "NO_ACTIONABLE_TRADE_VIEW"
        assert packet["interpretation_layers"]["facts"]
        assert "inferences" in packet["interpretation_layers"]
        assert packet["research_hypotheses"][0]["falsification_conditions"]
        assert packet["skeptical_review"]["strongest_objections"]
        assert packet["publication"]["analyst_review_required"] is True


def test_efx_rejection_semantics_remain_intact():
    packet = json.loads(
        git_blob("HEAD:demo/data/research_ideas/v2/efx_rejection.json")
    )
    result = packet["final_result"]
    review = packet["full_prior_evidence_review"]
    roles = {item["amount"]: item for item in review["quantity_roles"]}
    assert result["packet_disposition"] == "REJECT_MISLEADING_COMPARISON"
    assert result["trade_research_status"] == "NO_ACTIONABLE_TRADE_VIEW"
    assert review["comparison_status"] == "INCOMPARABLE_QUANTITIES"
    assert roles["$125M"]["novelty_result"] == "PREVIOUSLY_DISCLOSED_IN_10K"
    assert roles["$346.7M"]["correct_role"] == "Remaining payment balance"
    assert roles["~$345M"]["correct_role"] == "Cash deposit"
    assert "Current liquidity stress" in result["rejected_claims"]
    assert "Bondholder impact" in result["rejected_claims"]


def test_gitattributes_scope_is_exact_and_unrelated_assets_are_unchanged():
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for name in CANONICAL:
        assert f"demo/data/research_ideas/v2/{name} -text" in attributes
    assert "demo/data/research_ideas/v2/*.json -text" not in attributes
    for path, expected in UNCHANGED_PUBLIC_ASSETS.items():
        assert digest(git_blob(f"HEAD:{path}")) == expected
