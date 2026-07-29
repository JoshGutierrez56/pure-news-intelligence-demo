#!/usr/bin/env python3
"""Export validated Research Idea Engine V1 packets as JSON and Markdown.

Exports are deterministic views of existing packet fields. The script never
generates, edits, summarizes, or supplements a research claim. Source packets
must pass the final-packet validator before any export is written.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from research_idea_common import (
    INPUT_BUNDLE_PATH,
    LANGUAGE_REGISTRY_PATH,
    PACKET_DIR,
    SCHEMA_PATH,
    load_json,
    sha256_file,
)
from validate_research_idea_packets import (
    ValidationSetupError,
    validate_packet_set,
)


DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "research_idea_exports"
    / "v1"
)
EXPORT_FIELDS = (
    "packet_version",
    "packet_id",
    "packet_hash",
    "packet_status",
    "change_id",
    "issuer",
    "ticker",
    "filing_date",
    "formation_timestamp",
    "section",
    "source_url",
    "input_lineage",
    "evidence",
    "frozen_classification",
    "system_interpretation",
    "economic_mechanisms",
    "affected_entities",
    "research_hypotheses",
    "analyst_questions",
    "scenario_analysis",
    "illustrative_trade_hypothesis",
    "skeptical_review",
    "confidence",
    "analyst_disposition",
    "audit_metadata",
    "disclaimer",
)


class ExportError(RuntimeError):
    """Raised when a validated packet cannot be exported."""


def export_view(packet: dict[str, Any]) -> dict[str, Any]:
    """Return the user-facing packet fields without changing their values."""

    missing = [field for field in EXPORT_FIELDS if field not in packet]
    if missing:
        raise ExportError(
            "validated packet is missing export fields: " + ", ".join(missing)
        )
    return {
        "export_version": "research_idea_evidence_hypothesis_export_v1",
        "source_packet_id": packet["packet_id"],
        "source_packet_sha256": packet["packet_hash"],
        "packet": {field: packet[field] for field in EXPORT_FIELDS},
    }


def _inline(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).replace("\r", " ").replace("\n", " ")


def _list(
    lines: list[str],
    values: Iterable[Any],
    *,
    empty_label: str = "None recorded in the packet.",
) -> None:
    rendered = list(values)
    if not rendered:
        lines.append(f"- {empty_label}")
        return
    lines.extend(f"- {_inline(value)}" for value in rendered)


def _fenced(lines: list[str], value: Any) -> None:
    text = "" if value is None else str(value)
    longest = max(
        (len(match.group(0)) for match in re.finditer(r"`+", text)),
        default=0,
    )
    fence = "`" * max(3, longest + 1)
    lines.extend([fence, text, fence])


def _evidence_ids(lines: list[str], values: Iterable[Any]) -> None:
    identifiers = list(values)
    lines.append(
        "- Evidence IDs: "
        + (
            ", ".join(f"`{_inline(value)}`" for value in identifiers)
            if identifiers
            else "none recorded in the packet"
        )
    )


def packet_markdown(packet: dict[str, Any]) -> str:
    """Render packet values verbatim under fixed, non-analytical labels."""

    interpretation = packet["system_interpretation"]
    classification = packet["frozen_classification"]
    evidence = packet["evidence"]
    lines = [
        f"# AI Research Idea — {packet['issuer']} ({packet['ticker']})",
        "",
        f"> {packet['disclaimer']}",
        "",
        "## Packet identity",
        "",
        f"- Packet ID: `{packet['packet_id']}`",
        f"- Packet SHA-256: `{packet['packet_hash']}`",
        f"- Packet status: `{packet['packet_status']}`",
        f"- Change ID: `{packet['change_id']}`",
        f"- Filing date: `{packet['filing_date']}`",
        f"- Formation timestamp: `{packet['formation_timestamp']}`",
        f"- Filing section: `{packet['section']}`",
        f"- Source: {packet['source_url']}",
        "",
        "## Source evidence",
        "",
        f"- Prior filing ID: `{evidence['prior_filing_id']}`",
        f"- Current filing ID: `{evidence['current_filing_id']}`",
        f"- Prior filing source: {evidence['prior_source_url']}",
        f"- Current filing source: {evidence['current_source_url']}",
        f"- Evidence offsets verified: "
        f"`{_inline(evidence['evidence_offsets_verified'])}`",
        "",
        "### Prior excerpt",
        "",
    ]
    _fenced(lines, evidence["prior_excerpt"])
    lines.extend(["", "### Current excerpt", ""])
    _fenced(lines, evidence["current_excerpt"])
    lines.extend(["", "### Added text", ""])
    _fenced(lines, evidence["added_text"])
    lines.extend(["", "### Removed text", ""])
    _fenced(lines, evidence["removed_text"])

    lines.extend(["", "### Evidence identifiers", ""])
    for label, identifier in evidence["evidence_ids"].items():
        lines.append(f"- {label}: `{identifier}`")
    lines.extend(
        [
            f"- Prior offsets: "
            f"`{json.dumps(evidence['evidence_offsets']['prior'], sort_keys=True)}`",
            f"- Current offsets: "
            f"`{json.dumps(evidence['evidence_offsets']['current'], sort_keys=True)}`",
            "",
            "### Related prior 8-K evidence",
            "",
        ]
    )
    if not evidence["related_prior_8k"]:
        lines.append("- None recorded in the packet.")
    for item in evidence["related_prior_8k"]:
        lines.extend(
            [
                f"- `{item['evidence_id']}` — "
                f"{item['acceptance_timestamp']} — {item['url']}",
                f"  - Accession: `{item['accession_number']}`",
                f"  - Information date: `{item['information_date']}`",
                f"  - Primary category: {_inline(item['primary_category'])}",
                f"  - Item codes: "
                f"{', '.join(map(_inline, item['item_codes'])) or 'none'}",
                f"  - Matched terms: "
                f"{', '.join(map(_inline, item['matched_terms'])) or 'none'}",
                f"  - Match score: {_inline(item['match_score'])}",
                f"  - Similarity: {_inline(item['similarity'])}",
            ]
        )
    lines.extend(["", "### Related prior news evidence", ""])
    if not evidence["related_prior_news"]:
        lines.append("- None recorded in the packet.")
    for item in evidence["related_prior_news"]:
        lines.extend(
            [
                f"- `{item['evidence_id']}` — "
                f"{item['publication_timestamp']} — {item['headline']}",
                f"  - Story chain: `{item['story_chain_id']}`",
                f"  - Provider: {_inline(item['provider_host'])}",
                f"  - Matched terms: "
                f"{', '.join(map(_inline, item['matched_terms'])) or 'none'}",
                f"  - Match score: {_inline(item['match_score'])}",
                f"  - Similarity: {_inline(item['similarity'])}",
            ]
        )

    lines.extend(
        [
            "",
            "## What changed",
            "",
            interpretation["plain_language_change"],
            "",
            "### Evidence facts",
            "",
        ]
    )
    for fact in interpretation["evidence_facts"]:
        lines.append(
            f"- `{fact['fact_id']}` [{fact['fact_type']}]: "
            f"{fact['statement']}"
        )
        _evidence_ids(lines, fact["evidence_ids"])
    lines.extend(["", "### System inferences", ""])
    if not interpretation["inferences"]:
        lines.append("- None recorded in the packet.")
    for inference in interpretation["inferences"]:
        lines.extend(
            [
                f"- `{inference['inference_id']}` "
                f"[{inference['inference_type']}; "
                f"confidence {_inline(inference['confidence'])}]: "
                f"{inference['statement']}",
                f"  - Caveat: {inference['caveat']}",
            ]
        )
        _evidence_ids(lines, inference["evidence_ids"])
    lines.extend(["", "### Uncertainties", ""])
    for uncertainty in interpretation["uncertainties"]:
        lines.extend(
            [
                f"- `{uncertainty['uncertainty_id']}`: "
                f"{uncertainty['uncertainty']}",
                f"  - Why it matters: {uncertainty['why_it_matters']}",
                "  - Data needed: "
                + "; ".join(map(_inline, uncertainty["data_needed"])),
            ]
        )

    lines.extend(
        [
            "",
            "## Frozen novelty and materiality",
            "",
            f"- Category: {_inline(classification['category'])}",
            f"- Direction: {_inline(classification['direction'])}",
            f"- Materiality: {_inline(classification['materiality'])}",
            f"- Novelty: {_inline(classification['novelty'])}",
            f"- Frozen confidence: {_inline(classification['confidence'])}",
            f"- Classification method: "
            f"{_inline(classification['classification_method'])}",
            f"- Novelty method: {_inline(classification['novelty_method'])}",
            f"- Novelty is a causal claim: "
            f"`{_inline(classification['novelty_is_causal_claim'])}`",
            "",
            "## Economic mechanisms",
            "",
        ]
    )
    if not packet["economic_mechanisms"]:
        lines.append("- None recorded in the packet.")
    for mechanism in packet["economic_mechanisms"]:
        lines.extend(
            [
                f"### {mechanism['mechanism_id']}",
                "",
                mechanism["mechanism"],
                "",
                f"- Affected financial driver: "
                f"{mechanism['affected_financial_driver']}",
                f"- Mechanism confidence: "
                f"{_inline(mechanism['mechanism_confidence'])}",
                "- Causal chain:",
            ]
        )
        _list(lines, mechanism["causal_chain"])
        lines.append(f"- Counterargument: {mechanism['counterargument']}")
        _evidence_ids(lines, mechanism["supporting_evidence_ids"])
        lines.append("")

    lines.extend(["## Research hypotheses", ""])
    if not packet["research_hypotheses"]:
        lines.append("- None recorded in the packet.")
    for hypothesis in packet["research_hypotheses"]:
        lines.extend(
            [
                f"### {hypothesis['title']} (`{hypothesis['hypothesis_id']}`)",
                "",
                hypothesis["hypothesis"],
                "",
                f"- Expected direction: {hypothesis['expected_direction']}",
                f"- Time horizon: {hypothesis['time_horizon']}",
                f"- Unit of analysis: {hypothesis['unit_of_analysis']}",
                f"- Novelty assessment: {hypothesis['novelty_assessment']}",
                f"- Testability score: "
                f"{_inline(hypothesis['testability_score'])}",
                f"- Grounding score: {_inline(hypothesis['grounding_score'])}",
                "- Required data:",
            ]
        )
        _list(lines, hypothesis["required_data"])
        lines.append("- Confirmation conditions:")
        _list(lines, hypothesis["confirmation_conditions"])
        lines.append("- Falsification conditions:")
        _list(lines, hypothesis["falsification_conditions"])
        lines.append("- Confounders:")
        _list(lines, hypothesis["confounders"])
        _evidence_ids(lines, hypothesis["evidence_ids"])
        lines.append("")

    lines.extend(["## Analyst questions", ""])
    if not packet["analyst_questions"]:
        lines.append("- None recorded in the packet.")
    for question in packet["analyst_questions"]:
        lines.extend(
            [
                f"- `{question['question_id']}`: {question['question']}",
                f"  - Why it matters: {question['why_it_matters']}",
                "  - Required data: "
                + "; ".join(map(_inline, question["required_data"])),
            ]
        )
        _evidence_ids(lines, question["evidence_ids"])

    lines.extend(["", "## Affected entities", ""])
    if not packet["affected_entities"]:
        lines.append("- None recorded in the packet.")
    for entity in packet["affected_entities"]:
        lines.extend(
            [
                f"- `{entity['entity_id']}` — {entity['entity_or_group']}",
                f"  - Relationship: {entity['relationship']}",
                f"  - Possible effect: {entity['possible_effect']}",
                f"  - Reason: {entity['reason']}",
                f"  - Confidence: {_inline(entity['confidence'])}",
            ]
        )
        _evidence_ids(lines, entity["evidence_ids"])

    lines.extend(["", "## Bull / base / bear scenarios", ""])
    for scenario_name in ("bull", "base", "bear"):
        scenario = packet["scenario_analysis"][scenario_name]
        lines.extend(
            [
                f"### {scenario_name.title()}",
                "",
                scenario["scenario"],
                "",
                "- Conditions:",
            ]
        )
        _list(lines, scenario["conditions"])
        lines.append("- Implications:")
        _list(lines, scenario["implications"])
        _evidence_ids(lines, scenario["evidence_ids"])
        lines.append("")

    trade = packet["illustrative_trade_hypothesis"]
    lines.extend(
        [
            "## Illustrative Trade Hypothesis — Analyst Review Required",
            "",
            f"- Status: `{trade['status']}`",
            f"- Candidate view: {trade['candidate_view']}",
            f"- Instrument class to investigate: "
            f"{trade['preferred_instrument_class_to_investigate']}",
            f"- Instrument rationale: {trade['instrument_rationale']}",
            f"- Expected horizon: {trade['expected_horizon']}",
            f"- Trade readiness: `{trade['trade_readiness']}`",
            f"- Readiness reason: {trade['trade_readiness_reason']}",
            f"- Current market data used: "
            f"`{_inline(trade['current_market_data_used'])}`",
            f"- Illustrative only: `{_inline(trade['illustrative_only'])}`",
            f"- Analyst review required: "
            f"`{_inline(trade['analyst_review_required'])}`",
            f"- No position size generated: "
            f"`{_inline(trade['no_position_size_generated'])}`",
            "- Entry or confirmation conditions:",
        ]
    )
    _list(lines, trade["entry_or_confirmation_conditions"])
    lines.append("- Invalidation conditions:")
    _list(lines, trade["invalidation_conditions"])
    lines.append("- Key risks:")
    _list(lines, trade["key_risks"])
    lines.append("- Market data required before action:")
    _list(lines, trade["market_data_required_before_action"])
    lines.append("- Liquidity and cost checks:")
    _list(lines, trade["liquidity_and_cost_checks"])
    _evidence_ids(lines, trade["evidence_ids"])

    review = packet["skeptical_review"]
    lines.extend(
        [
            "",
            "## Skeptical review",
            "",
            f"- Final review status: `{review['final_review_status']}`",
            f"- Critical grounding defect: "
            f"`{_inline(review['critical_grounding_defect'])}`",
            f"- Review summary: {review['review_summary']}",
            "- Critical objections:",
        ]
    )
    _list(lines, review["critical_objections"])
    lines.append("- Alternative explanations:")
    _list(lines, review["alternative_explanations"])
    lines.append("- Pricing or attention concerns:")
    _list(lines, review["pricing_or_attention_concerns"])
    lines.append("- Unsupported claims removed:")
    _list(lines, review["unsupported_claims_removed"])
    _evidence_ids(lines, review["evidence_ids_reviewed"])

    confidence = packet["confidence"]
    disposition = packet["analyst_disposition"]
    lines.extend(
        [
            "",
            "## Confidence fields",
            "",
        ]
    )
    for field_name, value in confidence.items():
        lines.append(f"- {field_name}: {_inline(value)}")
    lines.extend(
        [
            "",
            "## Analyst disposition",
            "",
            f"- Status: `{disposition['status']}`",
            f"- Notes: {disposition['analyst_notes']}",
            f"- Edited fields: "
            f"{', '.join(map(_inline, disposition['edited_fields'])) or 'none'}",
            f"- Review timestamp: {_inline(disposition['review_timestamp'])}",
            f"- Saved locally only: "
            f"`{_inline(disposition['saved_locally_only'])}`",
            "",
            "## Validation provenance",
            "",
            f"- Packet audit version: "
            f"`{packet['audit_metadata']['audit_version']}`",
            f"- Packet audit timestamp: "
            f"`{packet['audit_metadata']['audited_at']}`",
            f"- Schema validation status: "
            f"`{packet['audit_metadata']['schema_validation']['status']}`",
            f"- Grounding audit status: "
            f"`{packet['audit_metadata']['grounding']['status']}`",
            f"- Future-information audit status: "
            f"`{packet['audit_metadata']['future_information']['status']}`",
            f"- Evidence-integrity audit status: "
            f"`{packet['audit_metadata']['evidence_integrity']['status']}`",
            f"- Prohibited-language audit status: "
            f"`{packet['audit_metadata']['prohibited_language']['status']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _load_selected_packets(
    packet_source: Path, summary: dict[str, Any]
) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for result in summary["packets"]:
        path = (
            packet_source / result["source_file"]
            if packet_source.is_dir()
            else packet_source
        )
        packet = load_json(path)
        if not isinstance(packet, dict):
            raise ExportError(f"packet root is not an object: {path}")
        packets.append(packet)
    packets.sort(key=lambda packet: (packet["change_id"], packet["packet_id"]))
    return packets


def export_packets(
    packets: Iterable[dict[str, Any]],
    output_dir: Path,
    *,
    write_json: bool = True,
    write_markdown: bool = True,
) -> dict[str, Any]:
    """Write deterministic exports and return their hash manifest."""

    entries: list[dict[str, Any]] = []
    for packet in packets:
        change_id = packet["change_id"]
        entry: dict[str, Any] = {
            "change_id": change_id,
            "packet_id": packet["packet_id"],
            "source_packet_sha256": packet["packet_hash"],
        }
        if write_json:
            json_path = output_dir / f"{change_id}.research_idea.json"
            json_payload = (
                json.dumps(
                    export_view(packet),
                    ensure_ascii=False,
                    allow_nan=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
            _atomic_write(json_path, json_payload)
            entry["json"] = {
                "path": json_path.name,
                "sha256": sha256_file(json_path),
            }
        if write_markdown:
            markdown_path = output_dir / f"{change_id}.research_idea.md"
            markdown_payload = packet_markdown(packet).encode("utf-8")
            _atomic_write(markdown_path, markdown_payload)
            entry["markdown"] = {
                "path": markdown_path.name,
                "sha256": sha256_file(markdown_path),
            }
        entries.append(entry)
    manifest = {
        "export_version": "research_idea_evidence_hypothesis_export_v1",
        "status": "PASS",
        "export_count": len(entries),
        "exports": entries,
    }
    manifest_payload = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    _atomic_write(output_dir / "manifest.json", manifest_payload)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packet-dir",
        type=Path,
        default=PACKET_DIR,
        help="Validated final packet directory or a single packet file",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--change-id", action="append", default=[])
    selection.add_argument(
        "--all",
        action="store_true",
        help="Export the complete frozen eight-case set (default)",
    )
    parser.add_argument("--input-bundle", type=Path, default=INPUT_BUNDLE_PATH)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    parser.add_argument(
        "--registry", type=Path, default=LANGUAGE_REGISTRY_PATH
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument("--json-only", action="store_true")
    format_group.add_argument("--markdown-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    export_all = args.all or not args.change_id
    requested = [] if export_all else args.change_id
    try:
        summary = validate_packet_set(
            args.packet_dir,
            input_bundle_path=args.input_bundle,
            schema_path=args.schema,
            registry_path=args.registry,
            mode="final",
            change_ids=requested,
            require_complete=export_all,
        )
        if summary["status"] != "PASS":
            raise ExportError(
                "packet validation failed; no export was written "
                f"({summary['error_count']} errors)"
            )
        packets = _load_selected_packets(args.packet_dir, summary)
        if export_all and len(packets) != 8:
            raise ExportError(
                f"--all requires eight validated packets; found {len(packets)}"
            )
        manifest = export_packets(
            packets,
            args.output_dir,
            write_json=not args.markdown_only,
            write_markdown=not args.json_only,
        )
    except (
        OSError,
        json.JSONDecodeError,
        ValidationSetupError,
        ExportError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
