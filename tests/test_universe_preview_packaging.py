from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "artifacts" / "universe_preview_public_asset_manifest.json"


def git_bytes(*args: str, cwd: Path = ROOT) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    ).stdout


def semantic_hash(raw: bytes) -> str:
    parsed = json.loads(raw.decode("utf-8"))
    canonical = json.dumps(
        parsed,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_asset_manifest_is_deterministic():
    subprocess.run(
        ["python", "scripts/build_universe_preview_asset_manifest.py", "--check"],
        cwd=ROOT,
        check=True,
    )


def test_manifest_uses_committed_git_blobs_as_source_of_truth():
    manifest = load_manifest()
    assert manifest["hash_source"] == "committed Git blobs"
    assert manifest["line_ending_contract"] == "UTF-8 JSON with LF line endings"
    for asset in manifest["assets"]:
        raw = git_bytes("show", f"{manifest['source_commit']}:{asset['path']}")
        assert len(raw) == asset["raw_byte_size"]
        assert hashlib.sha256(raw).hexdigest() == asset["sha256"]
        assert semantic_hash(raw) == asset["semantic_json_sha256"]
        assert b"\r\n" not in raw
        json.loads(raw.decode("utf-8"))


def test_index_and_worktree_match_committed_asset_bytes():
    manifest = load_manifest()
    for asset in manifest["assets"]:
        path = asset["path"]
        committed = git_bytes("show", f"{manifest['source_commit']}:{path}")
        current_head = git_bytes("show", f"HEAD:{path}")
        staged = git_bytes("show", f":{path}")
        worktree = (ROOT / path).read_bytes()
        assert current_head == committed
        assert staged == committed
        assert worktree == committed


def test_path_specific_line_ending_rule_is_narrow():
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "demo/data/universe_preview/*.json text eol=lf" in attributes
    assert "* -text" not in attributes


def test_manifest_record_counts_reconcile():
    assets = {item["path"]: item for item in load_manifest()["assets"]}
    assert assets[
        "demo/data/universe_preview/universe_coverage.json"
    ]["record_count"] == 6190
    assert len(assets) == 4


def test_public_claim_boundary_is_exact_and_unsupported_claims_are_absent():
    page = (ROOT / "demo" / "universe_coverage_preview.html").read_text(
        encoding="utf-8"
    )
    assert (
        "Broad U.S. public-company coverage preview based on issuers observed "
        "in a frozen 2012–2024 SEC 8-K metadata corpus."
    ) in page
    assert (
        "Metadata indexing does not mean full disclosure-change analysis "
        "has been completed."
    ) in page
    for unsupported in (
        "all 6,190 issuers have been fully analyzed",
        "all issuers have 10-K coverage",
        "all news has been collected",
        "current exchange membership",
        "6,190 issuers have evidence packets",
        "full-universe research hypotheses",
    ):
        assert unsupported.lower() not in page.lower()
