from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import html

from apps.analysis.dto import AttributeStatus, ExtractedEvent, MatchResult, Offender, PortalEvent


def normalize_name(value: str) -> str:
    cleaned = " ".join(value.lower().strip().split())
    return cleaned.replace("ё", "е")


def offender_name(offender: Offender) -> str:
    parts = [offender.last_name, offender.first_name, offender.middle_name]
    return " ".join(part for part in parts if part)


def offender_dob(offender: Offender) -> str | None:
    if offender.date_of_birth:
        return offender.date_of_birth.isoformat()
    if offender.birth_year:
        return str(offender.birth_year)
    return None


def offender_key(offender: Offender) -> str:
    name = normalize_name(offender_name(offender))
    dob = offender_dob(offender)
    return f"{name}|{dob}" if dob else name


def normalize_offenders(values: list[Offender]) -> set[str]:
    return {offender_key(value) for value in values if offender_name(value)}


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
    has_time: bool,
) -> AttributeStatus:
    if extracted is None:
        return AttributeStatus(label="timestamp", status=None, percent=None, value=None)
    value = extracted.isoformat(sep=" ", timespec="minutes")
    if not has_time:
        return AttributeStatus(
            label="timestamp",
            status="!",
            percent=0.0,
            value=f"{value} (время отсутствует)",
        )
    if candidate is None:
        return AttributeStatus(label="timestamp", status="-", percent=0.0, value=value)
    if extracted == candidate:
        return AttributeStatus(label="timestamp", status="+", percent=100.0, value=value)
    delta = (candidate - extracted).total_seconds() / 60
    if abs(delta) <= window_minutes:
        percent = time_window_percent(delta, window_minutes)
        return AttributeStatus(label="timestamp", status="!", percent=percent, value=value)
    return AttributeStatus(label="timestamp", status="-", percent=0.0, value=value)


def offenders_diff(extracted: list[Offender], matched: list[Offender]) -> dict[str, list[str]]:
    extracted_keys = {offender_key(offender): offender for offender in extracted}
    matched_keys = {offender_key(offender): offender for offender in matched}
    missing = [
        offender.display_name()
        for key, offender in matched_keys.items()
        if key not in extracted_keys
    ]
    extra = [
        offender.display_name()
        for key, offender in extracted_keys.items()
        if key not in matched_keys
    ]
    mismatch: list[str] = []
    extracted_by_name: dict[str, set[str]] = {}
    matched_by_name: dict[str, set[str]] = {}
    for offender in extracted:
        name = normalize_name(offender_name(offender))
        extracted_by_name.setdefault(name, set()).add(offender_dob(offender) or "-")
    for offender in matched:
        name = normalize_name(offender_name(offender))
        matched_by_name.setdefault(name, set()).add(offender_dob(offender) or "-")
    for name in sorted(set(extracted_by_name) & set(matched_by_name)):
        if extracted_by_name[name] != matched_by_name[name]:
            mismatch.append(
                f"{name}: извлечено {sorted(extracted_by_name[name])}, "
                f"в БД {sorted(matched_by_name[name])}"
            )
    return {
        "missing": sorted(missing),
        "extra": sorted(extra),
        "mismatch": mismatch,
    }


def evaluate_offenders(extracted: list[Offender], matched: list[Offender]) -> AttributeStatus:
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
        value=", ".join(offender.display_name() for offender in extracted),
        diff=offenders_diff(extracted, matched),
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
        return AttributeStatus(label="subdivision", status="-", percent=0.0, value="не определено")
    status = "+" if matched and extracted == matched else "!"
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
            "subdivision": result.extracted.subdivision_name,
            "offenders": [offender.display_name() for offender in result.extracted.offenders],
        },
        "matches": [
            {
                "event_id": match.event_id,
                "date_detection": match.date_detection.isoformat()
                if match.date_detection
                else None,
                "subdivision_name": match.subdivision_name,
                "offenders": [offender.display_name() for offender in match.offenders],
            }
            for match in result.matches
        ],
        "attributes": {key: asdict(value) for key, value in result.attributes.items()},
        "found": result.found,
        "message": result.message,
    }


def highlight_text(raw_text: str, highlights: list[tuple[str, str | None]]) -> str:
    escaped = html.escape(raw_text)
    ordered = sorted(
        [(text, status) for text, status in highlights if text],
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for text, status in ordered:
        if not status:
            continue
        class_name = {
            "+": "highlight-plus",
            "!": "highlight-warn",
            "-": "highlight-fail",
        }.get(status, "highlight-none")
        escaped_text = html.escape(text)
        escaped = escaped.replace(
            escaped_text, f'<span class="highlight {class_name}">{escaped_text}</span>'
        )
    return escaped


class CompareService:
    def compare(
        self,
        extracted: ExtractedEvent,
        candidates: list[PortalEvent],
        threshold: float,
        window_minutes: int,
    ) -> dict:
        valid_subdivision = (
            extracted.subdivision_similarity is not None
            and extracted.subdivision_similarity >= threshold
        )
        extracted_subdivision = extracted.subdivision_name if valid_subdivision else None
        extracted_offenders = extracted.offenders
        extracted_offenders_norm = normalize_offenders(extracted_offenders)

        matches: list[PortalEvent] = []
        for candidate in candidates:
            time_match = (
                extracted.timestamp_has_time
                and extracted.timestamp
                and candidate.date_detection == extracted.timestamp
            )
            subdivision_match = bool(
                extracted_subdivision
                and candidate.subdivision_name == extracted_subdivision
            )
            offenders_match = (
                extracted_offenders_norm == normalize_offenders(candidate.offenders)
            )
            if rule_two_of_three(time_match, subdivision_match, offenders_match):
                matches.append(candidate)

        found = bool(matches)
        primary_match = matches[0] if matches else None
        duplicates_count = len(matches)

        time_candidate = None
        if extracted.timestamp and extracted.timestamp_has_time and candidates:
            time_candidate = min(
                candidates,
                key=lambda candidate: abs(
                    (candidate.date_detection - extracted.timestamp).total_seconds()
                )
                if candidate.date_detection
                else float("inf"),
            )
            if (
                time_candidate
                and time_candidate.date_detection
                and abs(
                    (time_candidate.date_detection - extracted.timestamp).total_seconds()
                )
                / 60
                > window_minutes
            ):
                time_candidate = None

        time_status = evaluate_time(
            extracted.timestamp, time_candidate.date_detection if time_candidate else None, window_minutes, extracted.timestamp_has_time
        )
        subdivision_status = evaluate_subdivision(
            extracted.subdivision_name,
            primary_match.subdivision_name if primary_match else None,
            extracted.subdivision_similarity,
            threshold,
        )
        offenders_status = evaluate_offenders(
            extracted.offenders, primary_match.offenders if primary_match else []
        )

        highlights: list[tuple[str, str | None]] = []
        if extracted.timestamp_text:
            highlights.append((extracted.timestamp_text, time_status.status))
        if extracted.subdivision_text:
            highlights.append((extracted.subdivision_text, subdivision_status.status))
        for offender in extracted.offenders:
            if offender.raw:
                highlights.append((offender.raw, offenders_status.status))
        highlighted_text = highlight_text(extracted.raw_text, highlights)

        explanation: list[str] = []
        if (
            extracted.subdivision_text
            and extracted.subdivision_similarity is not None
            and extracted.subdivision_similarity < threshold
        ):
            explanation.append("Подразделение не удалось определить (ниже порога)")
        if offenders_status.diff:
            diff = offenders_status.diff
            if diff.get("missing"):
                explanation.append(f"Отсутствуют в извлечении: {', '.join(diff['missing'])}")
            if diff.get("extra"):
                explanation.append(f"Лишние в извлечении: {', '.join(diff['extra'])}")
            if diff.get("mismatch"):
                explanation.append("Несовпадения по ДР: " + "; ".join(diff["mismatch"]))

        return {
            "extracted": {
                "paragraph_index": extracted.paragraph_index,
                "raw_text": extracted.raw_text,
            },
            "highlighted_text": highlighted_text,
            "attributes": {
                "timestamp": asdict(time_status),
                "subdivision": asdict(subdivision_status),
                "offenders": asdict(offenders_status),
            },
            "event_found": found,
            "duplicates_count": duplicates_count,
            "matches": [
                {
                    "date_detection": match.date_detection,
                    "subdivision_name": match.subdivision_name,
                    "offenders": [offender.display_name() for offender in match.offenders],
                }
                for match in (matches if matches else [])
            ],
            "explanation": explanation,
        }
