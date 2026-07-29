#!/usr/bin/env python3
"""Build the deterministic V2 evidence index for the frozen eight cases.

The selected V1 excerpts remain untouched and are treated as display evidence.
Novelty search runs over complete eligible filing text plus the already-frozen
8-K and news metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = (
    ROOT
    / "demo"
    / "data"
    / "research_idea_inputs"
    / "v1"
    / "eight_case_inputs.json"
)
OUTPUT_DIR = ROOT / "data" / "research_idea_evidence_index" / "v2"
RECEIPT_PATH = ROOT / "artifacts" / "research_idea_evidence_index_v2_receipt.json"
USER_AGENT = "PureNewsResearchIdea/2.0 evidence-index contact: research@example.com"

BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "tr",
    "td",
    "th",
    "li",
    "br",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
}
SKIP_TAGS = {"script", "style", "noscript", "svg"}
ITEM_HEADING_RE = re.compile(
    r"^\s*item\s+(?P<item>1a|1b|2|3|4|5|6|7a|7|8|9a|9b|9|10|11|12|13|14|15|16)"
    r"\b[\s.:—-]*(?P<title>.*)$",
    re.IGNORECASE,
)
LIQUIDITY_RE = re.compile(r"\bliquidity\s+and\s+capital\s+resources\b", re.I)


class FilingHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in SKIP_TAGS:
            self.skip_depth += 1
        elif not self.skip_depth and lowered in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        elif not self.skip_depth and lowered in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def fetch(url: str, *, attempts: int = 4) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "identity",
            "Host": "www.sec.gov" if "sec.gov" in url else "",
        },
    )
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def html_to_text(payload: bytes) -> str:
    decoded = payload.decode("utf-8", errors="replace")
    parser = FilingHTMLParser()
    parser.feed(decoded)
    lines: list[str] = []
    for raw in "".join(parser.parts).splitlines():
        normalized = " ".join(html.unescape(raw).replace("\xa0", " ").split())
        if normalized:
            lines.append(normalized)
    return "\n".join(lines)


def section_for_heading(text: str, current: str) -> str:
    match = ITEM_HEADING_RE.match(text)
    if match:
        return f"item_{match.group('item').lower()}"
    if LIQUIDITY_RE.search(text) and len(text) < 180:
        return "liquidity_and_capital_resources"
    return current


def paragraphs(
    text: str,
    *,
    document_id: str,
    source_type: str,
    filing_date: str,
    acceptance_timestamp: str,
    display_excerpt: str,
    point_in_time_eligible: bool,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    cursor = 0
    section = "full_filing"
    normalized_display = " ".join(display_excerpt.lower().split())
    seen_text_hashes: set[str] = set()
    for paragraph_number, raw in enumerate(text.splitlines(), start=1):
        value = " ".join(raw.split())
        if not value:
            continue
        section = section_for_heading(value, section)
        is_heading = bool(ITEM_HEADING_RE.match(value) or LIQUIDITY_RE.search(value))
        if len(value) < 20 and not is_heading:
            continue
        text_hash = sha256_bytes(value.encode("utf-8"))
        if text_hash in seen_text_hashes:
            continue
        seen_text_hashes.add(text_hash)
        start = text.find(raw, cursor)
        if start < 0:
            start = cursor
        end = start + len(raw)
        cursor = end
        normalized_value = " ".join(value.lower().split())
        inside_display = bool(
            normalized_display
            and
            normalized_value
            and (
                normalized_value in normalized_display
                or normalized_display in normalized_value
            )
        )
        evidence_id = (
            f"evidence-index-v2:{document_id}:paragraph-{paragraph_number:05d}"
        )
        output.append(
            {
                "evidence_id": evidence_id,
                "document_id": document_id,
                "source_type": source_type,
                "filing_date": filing_date,
                "acceptance_timestamp": acceptance_timestamp,
                "section": section,
                "paragraph_number": paragraph_number,
                "start_offset": start,
                "end_offset": end,
                "text": value,
                "text_sha256": text_hash,
                "point_in_time_eligible": point_in_time_eligible,
                "inside_display_excerpt": inside_display,
                "outside_display_excerpt": not inside_display,
            }
        )
    return output


def submissions(cik: str) -> dict[str, Any]:
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/submissions.json"
    try:
        return json.loads(fetch(url).decode("utf-8"))
    except Exception:
        # Correct SEC endpoint for submissions metadata.
        url = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))


def older_10k_documents(
    source: dict[str, Any], *, maximum: int = 2
) -> list[dict[str, str]]:
    cik = source["identifiers"]["cik"]
    formation = datetime.fromisoformat(
        source["formation_timestamp"].replace("Z", "+00:00")
    )
    known = {
        source["identifiers"]["current_accession_number"].replace("-", ""),
        source["identifiers"]["prior_accession_number"].replace("-", ""),
    }
    try:
        data = submissions(cik)
    except Exception:
        return []
    recent = data.get("filings", {}).get("recent", {})
    rows = zip(
        recent.get("form", []),
        recent.get("accessionNumber", []),
        recent.get("filingDate", []),
        recent.get("acceptanceDateTime", []),
        recent.get("primaryDocument", []),
    )
    candidates: list[dict[str, str]] = []
    for form, accession, filing_date, accepted, primary in rows:
        if form not in {"10-K", "10-K/A"}:
            continue
        compact = accession.replace("-", "")
        if compact in known:
            continue
        try:
            accepted_dt = datetime.fromisoformat(str(accepted).replace("Z", "+00:00"))
        except ValueError:
            accepted_dt = datetime.fromisoformat(f"{filing_date}T23:59:59+00:00")
        if accepted_dt > formation:
            continue
        url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{compact}/{primary}"
        )
        candidates.append(
            {
                "accession_number": accession,
                "filing_date": filing_date,
                "acceptance_timestamp": accepted_dt.isoformat().replace("+00:00", "Z"),
                "source_url": url,
                "source_type": "SEC_10_K",
            }
        )
    return sorted(
        candidates, key=lambda item: item["acceptance_timestamp"], reverse=True
    )[:maximum]


def document_specs(source: dict[str, Any]) -> list[dict[str, str]]:
    current = {
        "accession_number": source["identifiers"]["current_accession_number"],
        "filing_date": source["filing_date"],
        "acceptance_timestamp": source["formation_timestamp"],
        "source_url": source["source_url"],
        "source_type": "SEC_10_K_CURRENT",
        "display_excerpt": source["evidence"]["current_excerpt"],
    }
    prior = {
        "accession_number": source["identifiers"]["prior_accession_number"],
        "filing_date": source["prior_filing"]["filing_date"],
        "acceptance_timestamp": source["prior_filing"]["acceptance_timestamp"],
        "source_url": source["prior_filing"]["source_url"],
        "source_type": "SEC_10_K",
        "display_excerpt": source["evidence"]["prior_excerpt"],
    }
    older = older_10k_documents(source)
    for item in older:
        item["display_excerpt"] = ""
    return [current, prior, *older]


def build_case(source: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    formation = datetime.fromisoformat(
        source["formation_timestamp"].replace("Z", "+00:00")
    )
    documents: list[dict[str, Any]] = []
    spans: list[dict[str, Any]] = []
    failures: list[str] = []
    seen_urls: set[str] = set()
    for spec in document_specs(source):
        if spec["source_url"] in seen_urls:
            continue
        seen_urls.add(spec["source_url"])
        document_id = spec["accession_number"].replace("-", "")
        try:
            payload = fetch(spec["source_url"])
            text = html_to_text(payload)
            if len(text) < 5000:
                raise RuntimeError(f"extracted text too short: {len(text)}")
            accepted = datetime.fromisoformat(
                spec["acceptance_timestamp"].replace("Z", "+00:00")
            )
            eligible = accepted <= formation
            doc_spans = paragraphs(
                text,
                document_id=document_id,
                source_type=spec["source_type"],
                filing_date=spec["filing_date"],
                acceptance_timestamp=spec["acceptance_timestamp"],
                display_excerpt=spec["display_excerpt"],
                point_in_time_eligible=eligible,
            )
            documents.append(
                {
                    "document_id": document_id,
                    "accession_number": spec["accession_number"],
                    "filing_date": spec["filing_date"],
                    "acceptance_timestamp": spec["acceptance_timestamp"],
                    "source_url": spec["source_url"],
                    "source_type": spec["source_type"],
                    "document_sha256": sha256_bytes(payload),
                    "extracted_text_sha256": sha256_bytes(text.encode("utf-8")),
                    "extracted_character_count": len(text),
                    "paragraph_count": len(doc_spans),
                    "point_in_time_eligible": eligible,
                }
            )
            spans.extend(doc_spans)
        except Exception as exc:
            failures.append(f"{source['ticker']} {spec['source_url']}: {exc}")
    # Frozen related evidence is included exactly as metadata allowed at formation.
    for item in source["evidence"].get("related_prior_8k", []):
        text = str(item.get("excerpt") or " ".join(item.get("matched_terms", [])))
        spans.append(
            {
                "evidence_id": item["evidence_id"],
                "document_id": item["accession_number"].replace("-", ""),
                "source_type": "SEC_8_K",
                "filing_date": item.get("information_date"),
                "acceptance_timestamp": item["acceptance_timestamp"],
                "section": "8_k",
                "paragraph_number": 1,
                "start_offset": 0,
                "end_offset": len(text),
                "text": text,
                "text_sha256": sha256_bytes(text.encode("utf-8")),
                "point_in_time_eligible": True,
                "inside_display_excerpt": False,
                "outside_display_excerpt": True,
            }
        )
    for item in source["evidence"].get("related_prior_news", []):
        text = item["headline"]
        spans.append(
            {
                "evidence_id": item["evidence_id"],
                "document_id": item["story_chain_id"],
                "source_type": "NEWS_HEADLINE",
                "filing_date": item["publication_timestamp"][:10],
                "acceptance_timestamp": item["publication_timestamp"],
                "section": "headline",
                "paragraph_number": 1,
                "start_offset": 0,
                "end_offset": len(text),
                "text": text,
                "text_sha256": sha256_bytes(text.encode("utf-8")),
                "point_in_time_eligible": True,
                "inside_display_excerpt": False,
                "outside_display_excerpt": True,
            }
        )
    spans.sort(
        key=lambda item: (
            item.get("acceptance_timestamp") or "",
            item["document_id"],
            item["paragraph_number"],
        )
    )
    return (
        {
            "index_version": "2.0",
            "change_id": source["change_id"],
            "issuer": source["issuer"],
            "ticker": source["ticker"],
            "formation_timestamp": source["formation_timestamp"],
            "provisional_novelty": source["novelty"]["classification"],
            "display_evidence": {
                "prior_excerpt": source["evidence"]["prior_excerpt"],
                "current_excerpt": source["evidence"]["current_excerpt"],
                "prior_offsets": source["evidence"]["offsets"]["prior"],
                "current_offsets": source["evidence"]["offsets"]["current"],
            },
            "documents": documents,
            "spans": spans,
            "full_prior_filing_search_completed": bool(
                any(doc["source_type"] == "SEC_10_K" for doc in documents)
            ),
        },
        failures,
    )


def build() -> dict[str, Any]:
    bundle = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, Any]] = []
    failures: list[str] = []
    all_documents: dict[str, dict[str, Any]] = {}
    all_spans: list[dict[str, Any]] = []
    for source in bundle["inputs"]:
        case, case_failures = build_case(source)
        write_json(OUTPUT_DIR / f"{source['change_id']}.json", case)
        cases.append(case)
        failures.extend(case_failures)
        for document in case["documents"]:
            all_documents[document["document_id"]] = document
        all_spans.extend(case["spans"])
    text_hash_counts = Counter(item["text_sha256"] for item in all_spans)
    duplicate_spans = sum(count - 1 for count in text_hash_counts.values() if count > 1)
    timing_violations = [
        item["evidence_id"]
        for item in all_spans
        if not item["point_in_time_eligible"]
    ]
    section_counts = Counter(item["section"] for item in all_spans)
    index_hashes = {
        case["change_id"]: sha256_bytes(
            (OUTPUT_DIR / f"{case['change_id']}.json").read_bytes()
        )
        for case in cases
    }
    receipt = {
        "receipt_version": "2.0",
        "index_version": "2.0",
        "source_bundle_sha256": sha256_bytes(INPUT_PATH.read_bytes()),
        "issuers_indexed": sorted({case["issuer"] for case in cases}),
        "issuer_count": len(cases),
        "filings_indexed": len(all_documents),
        "sections_indexed": dict(sorted(section_counts.items())),
        "paragraphs_indexed": len(all_spans),
        "failed_extractions": failures,
        "failed_extraction_count": len(failures),
        "duplicate_spans": duplicate_spans,
        "timing_violations": timing_violations,
        "timing_violation_count": len(timing_violations),
        "document_hashes": {
            document_id: document["document_sha256"]
            for document_id, document in sorted(all_documents.items())
        },
        "case_index_hashes": index_hashes,
        "full_prior_filing_search_completed": all(
            case["full_prior_filing_search_completed"] for case in cases
        ),
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_json(receipt).encode("utf-8"))
    write_json(RECEIPT_PATH, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    receipt = build()
    print(json.dumps(receipt, indent=2))
    return 1 if receipt["failed_extraction_count"] or receipt["timing_violation_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
