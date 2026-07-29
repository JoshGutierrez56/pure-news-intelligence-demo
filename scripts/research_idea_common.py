"""Shared deterministic controls for Research Idea Engine V1.

This module deliberately contains no model-specific reasoning. It handles
canonical hashing, schema validation, evidence/reference integrity, temporal
leakage checks, prohibited-language checks, and safe skeptical-review edits.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "research_idea_packet_v1.schema.json"
LANGUAGE_REGISTRY_PATH = (
    ROOT / "schemas" / "prohibited_research_idea_language_v1.json"
)
GENERATOR_PROMPT_PATH = ROOT / "prompts" / "research_idea_generator_v1.md"
SKEPTIC_PROMPT_PATH = ROOT / "prompts" / "research_idea_skeptic_v1.md"
PACKET_DIR = ROOT / "demo" / "data" / "research_idea_packets" / "v1"
ARCHIVE_PACKET_DIR = ROOT / "data" / "research_idea_packets" / "v1"
INPUT_BUNDLE_PATH = (
    ROOT
    / "demo"
    / "data"
    / "research_idea_inputs"
    / "v1"
    / "eight_case_inputs.json"
)

PINNED_MODEL = "qwen3.6:35b-a3b"
PINNED_MODEL_DIGEST = (
    "07d35212591fc27746f0a317c975a6d68754fb38e9053d82e25f06057af28522"
)
DEFAULT_DISCLAIMER = (
    "AI-generated research hypothesis based on the cited evidence. It is not "
    "a fact, personalized investment advice, or a validated trading signal. "
    "Analyst review is required."
)
MODEL_OPTIONS = {
    "temperature": 0,
    "seed": 20260728,
    "num_ctx": 32768,
    "num_predict": 8192,
    "top_k": 1,
    "top_p": 1,
    "min_p": 0,
    "presence_penalty": 0,
    "repeat_penalty": 1,
}

PUBLISHABLE_REVIEW_STATUSES = {"PASS", "PASS_WITH_EDITS"}
TERMINAL_REVIEW_STATUSES = PUBLISHABLE_REVIEW_STATUSES | {
    "HOLD_UNSUPPORTED",
    "HOLD_AMBIGUOUS",
    "HOLD_INSUFFICIENT_EVIDENCE",
    "REJECTED_BY_SKEPTIC",
}
NON_ACTIONABLE_VIEWS = {"no actionable view", "insufficient evidence"}

FUTURE_DATA_KEYS = {
    "outcome",
    "maximum_drawdown_12m",
    "realized_volatility_12m",
    "drawdown_worse_than_20pct",
    "abnormal_return_6m",
    "abnormal_return_12m",
    "ex_post_downside_outcome",
    "later_return",
    "later_drawdown",
    "future_filing",
    "post_filing_news",
}

IMMUTABLE_REVIEW_PREFIXES = (
    "/packet_version",
    "/change_id",
    "/issuer",
    "/ticker",
    "/filing_date",
    "/formation_timestamp",
    "/section",
    "/source_url",
    "/evidence",
    "/frozen_classification",
    "/generation_metadata",
    "/analyst_disposition",
    "/disclaimer",
)
ALLOWED_REVIEW_PREFIXES = (
    "/system_interpretation",
    "/economic_mechanisms",
    "/affected_entities",
    "/research_hypotheses",
    "/analyst_questions",
    "/scenario_analysis",
    "/illustrative_trade_hypothesis",
    "/confidence",
)


def canonical_json(value: Any) -> str:
    """Return stable UTF-8 JSON text for hashes and cache keys."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_text(canonical_json(value))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp is empty")
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp lacks timezone: {value}")
    return parsed


def iter_json(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    """Yield every JSON value with an RFC 6901-style path."""

    yield path or "/", value
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from iter_json(child, f"{path}/{escaped}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_json(child, f"{path}/{index}")


def packet_without_hash(packet: dict[str, Any]) -> dict[str, Any]:
    """Return the canonical hash preimage required by packet schema V1.

    The field remains present and is replaced with 64 zeroes. Removing it
    would produce a different digest and would violate the frozen schema's
    explicitly documented hash rule.
    """

    copy_packet = copy.deepcopy(packet)
    copy_packet["packet_hash"] = "0" * 64
    return copy_packet


def compute_packet_hash(packet: dict[str, Any]) -> str:
    return sha256_json(packet_without_hash(packet))


def compute_cache_key(
    *,
    stage: str,
    model_digest: str,
    prompt_hash: str,
    schema_hash: str,
    input_hash: str,
    options: dict[str, Any],
) -> str:
    return sha256_json(
        {
            "stage": stage,
            "model_digest": model_digest,
            "prompt_hash": prompt_hash,
            "schema_hash": schema_hash,
            "input_hash": input_hash,
            "options": options,
        }
    )


@dataclass
class AuditFinding:
    code: str
    severity: str
    message: str
    path: str = "/"
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
            "detail": self.detail,
        }


@dataclass
class AuditResult:
    change_id: str
    findings: list[AuditFinding] = field(default_factory=list)

    def add(
        self,
        code: str,
        severity: str,
        message: str,
        path: str = "/",
        **detail: Any,
    ) -> None:
        self.findings.append(
            AuditFinding(code, severity, message, path, detail)
        )

    @property
    def errors(self) -> list[AuditFinding]:
        return [finding for finding in self.findings if finding.severity == "ERROR"]

    @property
    def warnings(self) -> list[AuditFinding]:
        return [
            finding for finding in self.findings if finding.severity == "WARNING"
        ]

    @property
    def passed(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "status": "PASS" if self.passed else "FAIL",
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "findings": [finding.as_dict() for finding in self.findings],
        }


def validate_schema(
    packet: dict[str, Any], schema: dict[str, Any] | None = None
) -> list[AuditFinding]:
    active_schema = schema or load_json(SCHEMA_PATH)
    validator = Draft202012Validator(
        active_schema,
        format_checker=FormatChecker(),
    )
    findings: list[AuditFinding] = []
    for error in sorted(validator.iter_errors(packet), key=lambda item: list(item.path)):
        pointer = "".join(
            f"/{str(part).replace('~', '~0').replace('/', '~1')}"
            for part in error.absolute_path
        )
        findings.append(
            AuditFinding(
                code="SCHEMA_VALIDATION",
                severity="ERROR",
                path=pointer or "/",
                message=error.message,
            )
        )
    return findings


def is_negated_context(
    text: str,
    start: int,
    end: int,
    registry: dict[str, Any],
    *,
    window: int = 72,
) -> bool:
    lowered = text.casefold()
    clause_boundary = max(
        lowered.rfind(delimiter, max(0, start - window), start)
        for delimiter in (
            ".",
            "!",
            "?",
            ";",
            ":",
            "\n",
            "\r",
            "—",
            "–",
            "-",
            "|",
            "/",
            "\\",
        )
    )
    prefix = lowered[max(clause_boundary + 1, start - window) : start]
    bridge_terms = {
        str(term).casefold()
        for term in registry.get("direct_negation_bridge_terms", [])
    }
    for term in sorted(
        registry.get("negated_context_terms", []),
        key=len,
        reverse=True,
    ):
        matches = list(re.finditer(rf"\b{re.escape(term.casefold())}\b", prefix))
        if not matches:
            continue
        between = prefix[matches[-1].end() :].strip()
        between_tokens = [
            token.casefold()
            for token in re.findall(r"\b[\w'-]+\b", between)
        ]
        if (
            len(between) <= 32
            and len(between_tokens) <= 4
            and all(token in bridge_terms for token in between_tokens)
            and not re.search(
                r"\b(?:and|but|however|yet|then|although|though|"
                r"nevertheless|nonetheless|still|whereas|while|except|"
                r"instead)\b"
                r"|[^\w\s'’]",
                between,
            )
        ):
            return True

    suffix = lowered[end : min(len(lowered), end + window)]
    return bool(
        re.match(
            r"^\s+(?:(?:is|are|was|were|remains?|must\s+be)\s+)?"
            r"(?:strictly\s+)?(?:prohibited|excluded|removed|not\s+generated|not\s+provided)\b",
            suffix,
        )
    )


def prohibited_language_findings(
    packet: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> list[AuditFinding]:
    active_registry = registry or load_json(LANGUAGE_REGISTRY_PATH)
    allowed_statements = {
        statement.casefold().strip()
        for statement in active_registry.get("allowed_exact_statements", [])
    }
    allowed_paths = set(active_registry.get("always_allowed_json_paths", []))
    findings: list[AuditFinding] = []
    for path, value in iter_json(packet):
        if not isinstance(value, str) or not value.strip():
            continue
        # Exact source evidence may contain regulated vocabulary. It remains
        # visible evidence, not generated transaction language.
        if path.startswith("/evidence/"):
            continue
        # The skeptic may quote a phrase solely to document its removal.
        if path.startswith("/skeptical_review/unsupported_claims_removed"):
            continue
        if path in allowed_paths or value.casefold().strip() in allowed_statements:
            continue
        lowered = value.casefold()
        for phrase in active_registry.get("blocked_phrases", []):
            phrase_lower = phrase.casefold()
            cursor = 0
            while True:
                position = lowered.find(phrase_lower, cursor)
                if position < 0:
                    break
                if not is_negated_context(
                    value,
                    position,
                    position + len(phrase_lower),
                    active_registry,
                ):
                    findings.append(
                        AuditFinding(
                            code="PROHIBITED_PHRASE",
                            severity="ERROR",
                            path=path,
                            message=f"Prohibited generated phrase: {phrase}",
                            detail={"phrase": phrase},
                        )
                    )
                cursor = position + len(phrase_lower)
        for entry in active_registry.get("blocked_patterns", []):
            for match in re.finditer(entry["pattern"], value, flags=re.IGNORECASE):
                if not is_negated_context(
                    value,
                    match.start(),
                    match.end(),
                    active_registry,
                ):
                    findings.append(
                        AuditFinding(
                            code="PROHIBITED_PATTERN",
                            severity="ERROR",
                            path=path,
                            message=f"Prohibited generated pattern: {entry['id']}",
                            detail={
                                "pattern_id": entry["id"],
                                "match": match.group(0),
                            },
                        )
                    )
    return findings


def collect_evidence_ids(packet: dict[str, Any]) -> set[str]:
    evidence = packet.get("evidence", {})
    identifiers: set[str] = set()
    items = evidence.get("evidence_items", [])
    if isinstance(items, list):
        identifiers.update(
            str(item.get("evidence_id"))
            for item in items
            if isinstance(item, dict) and item.get("evidence_id")
        )
    explicit = evidence.get("evidence_ids", {})
    if isinstance(explicit, dict):
        identifiers.update(str(value) for value in explicit.values() if value)
    for collection_name in ("related_prior_8k", "related_prior_news"):
        for item in evidence.get(collection_name, []) or []:
            if isinstance(item, dict) and item.get("evidence_id"):
                identifiers.add(str(item["evidence_id"]))
    return identifiers


def _referenced_evidence_ids(packet: dict[str, Any]) -> Iterator[tuple[str, str]]:
    analytical_roots = (
        "system_interpretation",
        "economic_mechanisms",
        "affected_entities",
        "research_hypotheses",
        "analyst_questions",
        "scenario_analysis",
        "illustrative_trade_hypothesis",
    )

    def walk(value: Any, path: str) -> Iterator[tuple[str, str]]:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}/{key}"
                if key in {"evidence_ids", "supporting_evidence_ids"} and isinstance(
                    child, list
                ):
                    for evidence_id in child:
                        yield child_path, str(evidence_id)
                else:
                    yield from walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                yield from walk(child, f"{path}/{index}")

    for root_name in analytical_roots:
        yield from walk(packet.get(root_name), f"/{root_name}")


def _input_records(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("records", "cases", "inputs"):
        records = bundle.get(key)
        if isinstance(records, list):
            return records
    raise ValueError("input bundle does not contain records, cases, or inputs")


def find_input(
    bundle: dict[str, Any], change_id: str
) -> dict[str, Any] | None:
    return next(
        (
            record
            for record in _input_records(bundle)
            if str(record.get("change_id")) == str(change_id)
        ),
        None,
    )


def _check_immutable_match(
    result: AuditResult,
    packet: dict[str, Any],
    source_input: dict[str, Any],
) -> None:
    direct_fields = (
        "change_id",
        "issuer",
        "ticker",
        "filing_date",
        "formation_timestamp",
        "section",
        "source_url",
    )
    for field_name in direct_fields:
        if field_name in source_input and packet.get(field_name) != source_input[field_name]:
            result.add(
                "IMMUTABLE_INPUT_MISMATCH",
                "ERROR",
                f"{field_name} does not match the frozen formation-time input.",
                f"/{field_name}",
            )
    expected_evidence = source_input.get("evidence", {})
    actual_evidence = packet.get("evidence", {})
    for field_name in ("prior_excerpt", "current_excerpt", "added_text", "removed_text"):
        if actual_evidence.get(field_name) != expected_evidence.get(field_name):
            result.add(
                "IMMUTABLE_INPUT_MISMATCH",
                "ERROR",
                f"evidence.{field_name} does not match the frozen input.",
                f"/evidence/{field_name}",
            )
    input_ids = expected_evidence.get("evidence_ids", {})
    packet_ids = actual_evidence.get("evidence_ids", {})
    if packet_ids != input_ids:
        result.add(
            "IMMUTABLE_INPUT_MISMATCH",
            "ERROR",
            "Evidence IDs do not exactly match the frozen input.",
            "/evidence/evidence_ids",
        )
    input_offsets = expected_evidence.get("offsets", {})
    packet_offsets = actual_evidence.get("evidence_offsets", {})
    if packet_offsets != input_offsets:
        result.add(
            "IMMUTABLE_INPUT_MISMATCH",
            "ERROR",
            "Evidence offsets do not exactly match the frozen input.",
            "/evidence/evidence_offsets",
        )
    for collection_name in ("related_prior_8k", "related_prior_news"):
        if actual_evidence.get(collection_name, []) != expected_evidence.get(
            collection_name, []
        ):
            result.add(
                "IMMUTABLE_INPUT_MISMATCH",
                "ERROR",
                f"evidence.{collection_name} does not match the frozen input.",
                f"/evidence/{collection_name}",
            )
    expected_frozen = source_input.get("frozen_classification", {})
    actual_frozen = packet.get("frozen_classification", {})
    for field_name in (
        "category",
        "direction",
        "materiality",
        "confidence",
        "classification_method",
    ):
        if actual_frozen.get(field_name) != expected_frozen.get(field_name):
            result.add(
                "IMMUTABLE_INPUT_MISMATCH",
                "ERROR",
                f"frozen_classification.{field_name} does not match the input.",
                f"/frozen_classification/{field_name}",
            )
    expected_novelty = source_input.get("novelty", {})
    if actual_frozen.get("novelty") != expected_novelty.get("classification"):
        result.add(
            "IMMUTABLE_INPUT_MISMATCH",
            "ERROR",
            "Frozen novelty classification does not match the input.",
            "/frozen_classification/novelty",
        )
    if actual_frozen.get("novelty_method") != expected_novelty.get("method"):
        result.add(
            "IMMUTABLE_INPUT_MISMATCH",
            "ERROR",
            "Frozen novelty method does not match the input.",
            "/frozen_classification/novelty_method",
        )


def _check_future_timestamps(result: AuditResult, packet: dict[str, Any]) -> None:
    try:
        formation = parse_timestamp(packet.get("formation_timestamp", ""))
    except ValueError as exc:
        result.add(
            "FORMATION_TIMESTAMP",
            "ERROR",
            str(exc),
            "/formation_timestamp",
        )
        return
    evidence = packet.get("evidence", {})
    timestamp_fields = (
        ("related_prior_8k", "acceptance_timestamp"),
        ("related_prior_8ks", "acceptance_timestamp"),
        ("related_prior_news", "publication_timestamp"),
    )
    for collection_name, timestamp_name in timestamp_fields:
        for index, item in enumerate(evidence.get(collection_name, []) or []):
            if not isinstance(item, dict) or not item.get(timestamp_name):
                continue
            path = f"/evidence/{collection_name}/{index}/{timestamp_name}"
            try:
                observed = parse_timestamp(str(item[timestamp_name]))
            except ValueError as exc:
                result.add("EVIDENCE_TIMESTAMP", "ERROR", str(exc), path)
                continue
            if observed > formation:
                result.add(
                    "FUTURE_DATA_LEAKAGE",
                    "ERROR",
                    "Evidence timestamp is later than the formation timestamp.",
                    path,
                    formation_timestamp=packet.get("formation_timestamp"),
                    evidence_timestamp=item[timestamp_name],
                )


def _check_future_keys(result: AuditResult, packet: dict[str, Any]) -> None:
    for path, _value in iter_json(packet):
        key = path.rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~")
        if key.casefold() in FUTURE_DATA_KEYS:
            result.add(
                "EX_POST_FIELD_PRESENT",
                "ERROR",
                f"Prohibited ex-post field present: {key}",
                path,
            )


def _check_quality_rules(result: AuditResult, packet: dict[str, Any]) -> None:
    review_status = (
        packet.get("skeptical_review", {}).get("final_review_status", "")
    )
    if review_status not in TERMINAL_REVIEW_STATUSES:
        result.add(
            "SKEPTIC_STATUS",
            "ERROR",
            "Skeptical review is missing a terminal status.",
            "/skeptical_review/final_review_status",
        )
    publishable = review_status in PUBLISHABLE_REVIEW_STATUSES
    evidence = packet.get("evidence", {})
    if evidence.get("evidence_offsets_verified") is not True:
        result.add(
            "SOURCE_OFFSET_INTEGRITY",
            "ERROR",
            "Evidence offsets are not verified.",
            "/evidence/evidence_offsets_verified",
        )
    if not packet.get("source_url"):
        result.add(
            "SOURCE_URL",
            "ERROR",
            "Source URL is required.",
            "/source_url",
        )
    facts = packet.get("system_interpretation", {}).get("evidence_facts", [])
    inferences = packet.get("system_interpretation", {}).get("inferences", [])
    if publishable and not facts:
        result.add(
            "FACT_INFERENCE_SEPARATION",
            "ERROR",
            "A publishable packet requires explicit evidence facts.",
            "/system_interpretation/evidence_facts",
        )
    if publishable and not inferences:
        result.add(
            "FACT_INFERENCE_SEPARATION",
            "ERROR",
            "A publishable packet requires explicit inferences.",
            "/system_interpretation/inferences",
        )
    evidence_ids = collect_evidence_ids(packet)
    for path, evidence_id in _referenced_evidence_ids(packet):
        if evidence_id not in evidence_ids:
            result.add(
                "UNKNOWN_EVIDENCE_ID",
                "ERROR",
                f"Unknown evidence ID: {evidence_id}",
                path,
            )
    mechanisms = packet.get("economic_mechanisms", [])
    hypotheses = packet.get("research_hypotheses", [])
    if publishable and not mechanisms:
        result.add(
            "GROUNDED_MECHANISM",
            "ERROR",
            "A publishable packet requires at least one mechanism.",
            "/economic_mechanisms",
        )
    if publishable and not hypotheses:
        result.add(
            "FALSIFIABLE_HYPOTHESIS",
            "ERROR",
            "A publishable packet requires at least one research hypothesis.",
            "/research_hypotheses",
        )
    for index, mechanism in enumerate(mechanisms):
        if publishable and not mechanism.get("supporting_evidence_ids"):
            result.add(
                "GROUNDED_MECHANISM",
                "ERROR",
                "Mechanism lacks a supporting evidence ID.",
                f"/economic_mechanisms/{index}/supporting_evidence_ids",
            )
        if publishable and not mechanism.get("counterargument"):
            result.add(
                "MECHANISM_COUNTERARGUMENT",
                "ERROR",
                "Mechanism lacks a counterargument.",
                f"/economic_mechanisms/{index}/counterargument",
            )
    for index, hypothesis in enumerate(hypotheses):
        checks = (
            ("required_data", "REQUIRED_DATA"),
            ("confirmation_conditions", "CONFIRMATION_CONDITION"),
            ("falsification_conditions", "FALSIFICATION_CONDITION"),
            ("confounders", "CONFOUNDER"),
            ("evidence_ids", "HYPOTHESIS_EVIDENCE"),
        )
        for field_name, code in checks:
            if publishable and not hypothesis.get(field_name):
                result.add(
                    code,
                    "ERROR",
                    f"Hypothesis lacks {field_name.replace('_', ' ')}.",
                    f"/research_hypotheses/{index}/{field_name}",
                )
    scenarios = packet.get("scenario_analysis", {})
    for scenario_name in ("bull", "base", "bear"):
        scenario = scenarios.get(scenario_name)
        if not isinstance(scenario, dict):
            result.add(
                "SCENARIO_COMPLETENESS",
                "ERROR",
                f"Missing {scenario_name} scenario.",
                f"/scenario_analysis/{scenario_name}",
            )
            continue
        for field_name in ("scenario", "conditions", "implications"):
            if not scenario.get(field_name) and (
                field_name == "scenario" or publishable
            ):
                result.add(
                    "SCENARIO_COMPLETENESS",
                    "ERROR",
                    f"{scenario_name} scenario lacks {field_name}.",
                    f"/scenario_analysis/{scenario_name}/{field_name}",
                )
    trade = packet.get("illustrative_trade_hypothesis", {})
    if trade.get("no_position_size_generated") is not True:
        result.add(
            "POSITION_SIZE",
            "ERROR",
            "no_position_size_generated must be true.",
            "/illustrative_trade_hypothesis/no_position_size_generated",
        )
    candidate_view = str(trade.get("candidate_view", "")).casefold()
    if candidate_view and candidate_view not in NON_ACTIONABLE_VIEWS:
        for field_name in (
            "invalidation_conditions",
            "key_risks",
            "market_data_required_before_action",
            "liquidity_and_cost_checks",
        ):
            if not trade.get(field_name):
                result.add(
                    "TRADE_GUARDRAIL",
                    "ERROR",
                    f"Trade hypothesis lacks {field_name.replace('_', ' ')}.",
                    f"/illustrative_trade_hypothesis/{field_name}",
                )
    if packet.get("disclaimer") != DEFAULT_DISCLAIMER:
        result.add(
            "DISCLAIMER",
            "ERROR",
            "The required disclaimer does not match exactly.",
            "/disclaimer",
        )


def audit_packet(
    packet: dict[str, Any],
    *,
    source_input: dict[str, Any] | None = None,
    schema: dict[str, Any] | None = None,
    registry: dict[str, Any] | None = None,
) -> AuditResult:
    result = AuditResult(str(packet.get("change_id", "UNKNOWN")))
    result.findings.extend(validate_schema(packet, schema))
    result.findings.extend(prohibited_language_findings(packet, registry))
    _check_future_keys(result, packet)
    _check_future_timestamps(result, packet)
    _check_quality_rules(result, packet)
    if source_input is not None:
        _check_immutable_match(result, packet, source_input)
    stored_hash = packet.get("packet_hash")
    if stored_hash:
        computed = compute_packet_hash(packet)
        if stored_hash != computed:
            result.add(
                "PACKET_HASH",
                "ERROR",
                "Stored packet hash does not match canonical packet content.",
                "/packet_hash",
                stored=stored_hash,
                computed=computed,
            )
    return result


def _decode_pointer(pointer: str) -> list[str]:
    if not pointer.startswith("/") or pointer == "/":
        raise ValueError("correction path must be a non-root JSON pointer")
    return [
        part.replace("~1", "/").replace("~0", "~")
        for part in pointer[1:].split("/")
    ]


def _replace_pointer(document: Any, pointer: str, replacement: Any) -> None:
    parts = _decode_pointer(pointer)
    cursor = document
    for part in parts[:-1]:
        cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
    leaf = parts[-1]
    if isinstance(cursor, list):
        cursor[int(leaf)] = replacement
    else:
        if leaf not in cursor:
            raise KeyError(pointer)
        cursor[leaf] = replacement


def _read_pointer(document: Any, pointer: str) -> Any:
    cursor = document
    for part in _decode_pointer(pointer):
        cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
    return cursor


def apply_reviewer_corrections(
    packet: dict[str, Any],
    corrections: Iterable[dict[str, Any]],
    *,
    maximum: int = 20,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    revised = copy.deepcopy(packet)
    applied: list[dict[str, Any]] = []
    for index, correction in enumerate(corrections):
        if index >= maximum:
            raise ValueError(f"reviewer returned more than {maximum} corrections")
        pointer = str(correction.get("path", ""))
        if pointer.startswith(IMMUTABLE_REVIEW_PREFIXES):
            raise ValueError(f"reviewer attempted to edit immutable field: {pointer}")
        if not pointer.startswith(ALLOWED_REVIEW_PREFIXES):
            raise ValueError(f"reviewer edit is outside allowed inference fields: {pointer}")
        replacement = correction.get("replacement")
        prior_value = copy.deepcopy(_read_pointer(revised, pointer))
        _replace_pointer(revised, pointer, replacement)
        if prior_value == replacement:
            continue
        applied.append(
            {
                "path": pointer,
                "reason": str(correction.get("reason", "")).strip(),
            }
        )
    return revised, applied


def assert_unique_change_ids(packets: Iterable[dict[str, Any]]) -> None:
    seen_change_ids: set[str] = set()
    seen_packet_ids: set[str] = set()
    for packet in packets:
        change_id = str(packet.get("change_id", ""))
        if not change_id:
            raise ValueError("packet is missing change_id")
        if change_id in seen_change_ids:
            raise ValueError(f"duplicate packet change_id: {change_id}")
        seen_change_ids.add(change_id)

        packet_id = str(packet.get("packet_id", ""))
        if not packet_id:
            raise ValueError("packet is missing packet_id")
        if packet_id in seen_packet_ids:
            raise ValueError(f"duplicate packet_id: {packet_id}")
        seen_packet_ids.add(packet_id)
