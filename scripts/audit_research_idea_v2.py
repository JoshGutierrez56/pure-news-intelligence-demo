#!/usr/bin/env python3
"""Run the explicit V2 language, future-data, preservation, and deployment audits."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_idea_common import prohibited_language_findings


ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = ROOT / "data" / "research_idea_packets" / "v2"
ARTIFACT_DIR = ROOT / "artifacts"
START_RECEIPT = ARTIFACT_DIR / "research_idea_engine_v2_start_receipt.json"
FUTURE_KEYS = {
    "outcome",
    "outcome_date",
    "later_return",
    "future_return",
    "abnormal_return_6m",
    "realized_pnl",
    "post_filing_performance",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def walk_keys(value: Any, prefix: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}"
            if key.lower() in FUTURE_KEYS:
                findings.append(child_path)
            findings.extend(walk_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(walk_keys(child, f"{prefix}[{index}]"))
    return findings


def write_json(name: str, payload: dict[str, Any]) -> None:
    (ARTIFACT_DIR / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    packet_paths = sorted(
        path for path in PACKET_DIR.glob("*.json") if path.name != "index.json"
    )
    packets = [(path, load(path)) for path in packet_paths]

    language_findings = []
    for path, packet in packets:
        for finding in prohibited_language_findings(packet):
            evidence_only_path = any(
                marker in finding.path
                for marker in (
                    "/source_evidence/",
                    "/top_prior_matches/",
                    "/prior_occurrence_search/top_matches/",
                    "/counterevidence_matches/",
                    "/strongest_counterevidence/text",
                    "/best_matching_prior_evidence_span/text",
                )
            )
            if not evidence_only_path:
                language_findings.append({"packet": path.name, **finding.as_dict()})
    write_json(
        "research_idea_v2_prohibited_language_audit.json",
        {
            "audit": "prohibited_language",
            "audited_at_utc": now,
            "packet_count": len(packets),
            "finding_count": len(language_findings),
            "findings": language_findings,
            "status": "PASS" if not language_findings else "FAIL",
        },
    )

    future_findings = [
        {"packet": path.name, "paths": walk_keys(packet)}
        for path, packet in packets
        if walk_keys(packet)
    ]
    write_json(
        "research_idea_v2_future_data_leakage_audit.json",
        {
            "audit": "future_data_leakage",
            "audited_at_utc": now,
            "packet_count": len(packets),
            "forbidden_keys": sorted(FUTURE_KEYS),
            "findings": future_findings,
            "status": "PASS" if not future_findings else "FAIL",
        },
    )

    start = load(START_RECEIPT)
    expected: dict[str, str] = {
        f"data/research_idea_packets/v1/{change_id}.json": digest
        for change_id, digest in start["v1_packet_hashes"].items()
    }
    expected.update(start["efx_review_hashes"])
    expected.update(
        {
            key: value
            for key, value in start["frozen_source_data_hashes"].items()
            if "/" in key
        }
    )
    preservation = {
        relative: {
            "expected_sha256": expected_hash,
            "actual_sha256": sha256(ROOT / relative),
            "preserved": sha256(ROOT / relative) == expected_hash,
        }
        for relative, expected_hash in sorted(expected.items())
    }
    preservation_status = all(item["preserved"] for item in preservation.values())
    write_json(
        "research_idea_v2_frozen_source_hash_audit.json",
        {
            "audit": "frozen_source_hash",
            "audited_at_utc": now,
            "protected_file_count": len(preservation),
            "files": preservation,
            "logical_frozen_hashes_carried_forward": {
                key: value
                for key, value in start["frozen_source_data_hashes"].items()
                if "/" not in key
            },
            "status": "PASS" if preservation_status else "FAIL",
        },
    )

    expected_public_commit = start["public_deployment"]["commit"]
    remote = subprocess.run(
        ["git", "ls-remote", "origin", "refs/heads/gh-pages"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    actual_public_commit = remote.split()[0] if remote else None
    write_json(
        "research_idea_v2_public_deployment_audit.json",
        {
            "audit": "public_deployment_unchanged",
            "audited_at_utc": now,
            "expected_public_commit": expected_public_commit,
            "actual_public_commit": actual_public_commit,
            "deployment_performed": False,
            "status": (
                "PASS" if actual_public_commit == expected_public_commit else "FAIL"
            ),
        },
    )

    statuses = [
        not language_findings,
        not future_findings,
        preservation_status,
        actual_public_commit == expected_public_commit,
    ]
    print(json.dumps({"status": "PASS" if all(statuses) else "FAIL"}))
    return 0 if all(statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
