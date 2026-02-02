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


def dedupe_offenders(values: list[Offender]) -> list[Offender]:
    seen: set[str] = set()
    deduped: list[Offender] = []
    for offender in values:
        if not offender_name(offender):
            continue
        key = offender_key(offender)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(offender)
    return deduped


def normalize_offenders(values: list[Offender]) -> set[str]:
    return {offender_key(value) for value in dedupe_offenders(values)}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def format_delta_minutes(delta_minutes: int) -> str:
    if delta_minutes == 0:
        return "0 мин"
    sign = "+" if delta_minutes > 0 else "-"
    minutes = abs(delta_minutes)
    hours = minutes // 60
    remainder = minutes % 60
    if hours and remainder:
        return f"{sign}{hours} ч {remainder} мин"
    if hours:
        return f"{sign}{hours} ч"
    return f"{sign}{remainder} мин"


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
            percent=None,
            value=f"{value} (время отсутствует)",
        )
    if candidate is None:
        return AttributeStatus(label="timestamp", status="-", percent=None, value=value)
    if extracted == candidate:
        return AttributeStatus(
            label="timestamp",
            status="+",
            percent=None,
            value=value,
            timestamp_delta_minutes=0,
            timestamp_delta_human="0 мин",
        )
    delta_minutes = int(round((extracted - candidate).total_seconds() / 60))
    if abs(delta_minutes) <= window_minutes:
        return AttributeStatus(
            label="timestamp",
            status="!",
            percent=None,
            value=value,
            timestamp_delta_minutes=delta_minutes,
            timestamp_delta_human=format_delta_minutes(delta_minutes),
        )
    return AttributeStatus(label="timestamp", status="-", percent=None, value=value)


def offenders_diff(extracted: list[Offender], matched: list[Offender]) -> dict[str, list[str]]:
    extracted_keys = {offender_key(offender): offender for offender in dedupe_offenders(extracted)}
    matched_keys = {offender_key(offender): offender for offender in dedupe_offenders(matched)}
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
    extracted_deduped = dedupe_offenders(extracted)
    matched_deduped = dedupe_offenders(matched)
    extracted_set = normalize_offenders(extracted_deduped)
    matched_set = normalize_offenders(matched_deduped)
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
        value=", ".join(offender.display_name() for offender in extracted_deduped),
        diff=offenders_diff(extracted_deduped, matched_deduped),
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
    extracted_offenders = dedupe_offenders(result.extracted.offenders)
    return {
        "extracted": {
            "paragraph_index": result.extracted.paragraph_index,
            "raw_text": result.extracted.raw_text,
            "timestamp": result.extracted.timestamp.isoformat()
            if result.extracted.timestamp
            else None,
            "subdivision": result.extracted.subdivision_name,
            "offenders": [offender.display_name() for offender in extracted_offenders],
        },
        "matches": [
            {
                "event_id": match.event_id,
                "date_detection": match.date_detection.isoformat()
                if match.date_detection
                else None,
                "subdivision_name": match.subdivision_name,
                "subdivision_short_name": match.subdivision_short_name,
                "subdivision_full_name": match.subdivision_full_name,
                "offenders": [
                    offender.display_name()
                    for offender in dedupe_offenders(match.offenders)
                ],
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
        extracted_offenders = dedupe_offenders(extracted.offenders)
        extracted_offenders_norm = normalize_offenders(extracted_offenders)

        matches: list[PortalEvent] = []
        for candidate in candidates:
            candidate_offenders = dedupe_offenders(candidate.offenders)
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
                extracted_offenders_norm == normalize_offenders(candidate_offenders)
            )
            if rule_two_of_three(time_match, subdivision_match, offenders_match):
                candidate.offenders = candidate_offenders
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
            extracted_offenders, primary_match.offenders if primary_match else []
        )

        highlights: list[tuple[str, str | None]] = []
        if extracted.timestamp_text:
            highlights.append((extracted.timestamp_text, time_status.status))
        if extracted.subdivision_text:
            highlights.append((extracted.subdivision_text, subdivision_status.status))
        for offender in extracted_offenders:
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
                    "subdivision_short_name": match.subdivision_short_name,
                    "subdivision_full_name": match.subdivision_full_name,
                    "offenders": [
                        offender.display_name()
                        for offender in dedupe_offenders(match.offenders)
                    ],
                }
                for match in (matches if matches else [])
            ],
            "explanation": explanation,
        }
