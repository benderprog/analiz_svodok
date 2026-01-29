from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from apps.analysis.dto import AttributeStatus, ExtractedEvent, MatchResult, PortalEvent


def normalize_name(value: str) -> str:
    cleaned = " ".join(value.lower().strip().split())
    return cleaned.replace("ё", "е")


def normalize_offenders(values: list[str]) -> set[str]:
    return {normalize_name(value) for value in values if value.strip()}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def time_window_percent(delta_minutes: float, window_minutes: int) -> float:
    return max(0.0, 100 - (abs(delta_minutes) / window_minutes) * 100)


def evaluate_time(
    extracted: datetime | None,
    candidate: datetime | None,
    window_minutes: int,
    exact: bool,
    allow_near: bool,
) -> AttributeStatus:
    if extracted is None:
        return AttributeStatus(label="timestamp", status=None, percent=None, value=None)
    if candidate is None:
        return AttributeStatus(label="timestamp", status="-", percent=0.0, value=str(extracted))
    if exact:
        return AttributeStatus(label="timestamp", status="+", percent=100.0, value=str(extracted))
    if not allow_near:
        return AttributeStatus(label="timestamp", status="-", percent=0.0, value=str(extracted))
    delta = (candidate - extracted).total_seconds() / 60
    percent = time_window_percent(delta, window_minutes)
    status = "!" if percent > 0 else "-"
    return AttributeStatus(label="timestamp", status=status, percent=percent, value=str(extracted))


def offenders_diff(extracted: set[str], matched: set[str]) -> dict[str, list[str]]:
    return {
        "missing": sorted(matched - extracted),
        "extra": sorted(extracted - matched),
        "overlap": sorted(extracted & matched),
    }


def evaluate_offenders(extracted: list[str], matched: list[str]) -> AttributeStatus:
    if not extracted:
        return AttributeStatus(label="offenders", status=None, percent=None, value="не определено")
    extracted_set = normalize_offenders(extracted)
    matched_set = normalize_offenders(matched)
    similarity = jaccard_similarity(extracted_set, matched_set)
    if similarity == 1.0:
        status = "+"
    elif similarity > 0:
        status = "!"
    else:
        status = "-"
    return AttributeStatus(
        label="offenders",
        status=status,
        percent=round(similarity * 100, 2),
        value=", ".join(sorted(extracted_set)),
        diff=offenders_diff(extracted_set, matched_set),
    )


def evaluate_subdivision(
    extracted: str | None,
    matched: str | None,
    similarity: float | None,
    threshold: float,
) -> AttributeStatus:
    if not extracted:
        return AttributeStatus(label="subdivision", status=None, percent=None, value="не определено")
    if similarity is None or similarity < threshold:
        return AttributeStatus(
            label="subdivision", status="-", percent=0.0, value="не определено"
        )
    status = "+" if extracted == matched else "!"
    percent = round(similarity * 100, 2)
    return AttributeStatus(label="subdivision", status=status, percent=percent, value=extracted)


def rule_two_of_three(time_match: bool, subdivision_match: bool, offenders_match: bool) -> bool:
    return sum([time_match, subdivision_match, offenders_match]) >= 2


def build_result(
    extracted: ExtractedEvent,
    matched: PortalEvent | None,
    time_status: AttributeStatus,
    subdivision_status: AttributeStatus,
    offenders_status: AttributeStatus,
    found: bool,
) -> MatchResult:
    return MatchResult(
        extracted=extracted,
        matches=[matched] if matched else [],
        attributes={
            "timestamp": time_status,
            "subdivision": subdivision_status,
            "offenders": offenders_status,
        },
        found=found,
    )


def serialize_match(result: MatchResult) -> dict:
    return {
        "extracted": {
            "paragraph_index": result.extracted.paragraph_index,
            "raw_text": result.extracted.raw_text,
            "timestamp": result.extracted.timestamp.isoformat()
            if result.extracted.timestamp
            else None,
            "subdivision": result.extracted.subdivision,
            "offenders": result.extracted.offenders,
        },
        "matches": [
            {
                "event_id": match.event_id,
                "date_detection": match.date_detection.isoformat()
                if match.date_detection
                else None,
                "subdivision_name": match.subdivision_name,
                "offenders": match.offenders,
            }
            for match in result.matches
        ],
        "attributes": {key: asdict(value) for key, value in result.attributes.items()},
        "found": result.found,
        "message": result.message,
    }
