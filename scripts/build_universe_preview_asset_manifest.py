"""Build a deterministic manifest from committed universe-preview Git blobs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "universe_preview_public_asset_manifest.json"
SOURCE_REF = "43beba2"
ASSET_PATHS = (
    "demo/data/universe_preview/build_receipt.json",
    "demo/data/universe_preview/source_manifest.json",
    "demo/data/universe_preview/universe_coverage.json",
    "demo/data/universe_preview/universe_summary.json",
)


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def canonical_semantic_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def record_count(path: str, value: dict[str, Any]) -> int:
    if path.endswith("universe_coverage.json"):
        return len(value["records"])
    if path.endswith("source_manifest.json"):
        return len(value["sources"])
    return 1


def build() -> dict[str, Any]:
    source_commit = git("rev-parse", SOURCE_REF).decode("ascii").strip()
    build_timestamp = (
        git("show", "-s", "--format=%cI", source_commit).decode("ascii").strip()
    )

    assets = []
    for path in ASSET_PATHS:
        raw = git("show", f"{source_commit}:{path}")
        parsed = json.loads(raw.decode("utf-8"))
        assets.append(
            {
                "path": path,
                "raw_byte_size": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "semantic_json_sha256": hashlib.sha256(
                    canonical_semantic_bytes(parsed)
                ).hexdigest(),
                "record_count": record_count(path, parsed),
                "build_timestamp": build_timestamp,
                "source_commit": source_commit,
            }
        )

    return {
        "schema": "pure-news-universe-preview.public-assets.v1",
        "hash_source": "committed Git blobs",
        "line_ending_contract": "UTF-8 JSON with LF line endings",
        "source_commit": source_commit,
        "build_timestamp": build_timestamp,
        "assets": assets,
    }


def encoded(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = encoded(build())
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != expected:
            raise SystemExit(f"Asset manifest mismatch: {OUTPUT}")
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(expected)


if __name__ == "__main__":
    main()
