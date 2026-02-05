from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import hashlib
import re
import uuid
from typing import Iterable

from docx import Document
import yaml

from apps.core.management.portal_seed import (
    EventSeed,
    OffenderSeed,
    SubdivisionSeed,
    _build_full_name,
    _build_short_name,
)

DEFAULT_SUBDIVISION_NAME = "Не определено (тест)"
DEFAULT_EVENT_START = datetime(2024, 1, 1, 0, 0)
MAX_DOCX_EVENTS = 15

_DATE_RE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b")
_YEAR_RE = re.compile(
    r"\b(19\d{2}|20\d{2})\s*(?:г\.?р\.?|г\.?|г р|года рождения|года)\b",
    re.IGNORECASE,
)
_FULL_NAME_RE = re.compile(
    r"\b([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)\b"
)
_INITIALS_RE = re.compile(r"\b([А-ЯЁ][а-яё]+)\s+([А-ЯЁ])\.([А-ЯЁ])\.")
_DATE_TIME_RE = re.compile(r"\b(?P<date>\d{2}\.\d{2}\.\d{4})\s*(?P<time>\d{1,2}[.:]\d{2})\b")
_TIME_DATE_RE = re.compile(
    r"\b(?:[Вв]\s*)?(?P<time>\d{1,2}[.:]\d{2})\s*(?P<date>\d{2}\.\d{2}\.\d{4})\b"
)


@dataclass(frozen=True)
class DivisionAlias:
    alias_normalized: str
    subdivision: SubdivisionSeed


def read_docx_paragraphs(path: Path, *, allow_missing: bool = False, limit: int = MAX_DOCX_EVENTS) -> list[str]:
    if not path.exists():
        if allow_missing:
            return []
        raise FileNotFoundError(f"DOCX not found: {path}")
    document = Document(str(path))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return paragraphs[:limit]


def parse_timestamp(text: str) -> datetime | None:
    for pattern in (_DATE_TIME_RE, _TIME_DATE_RE):
        match = pattern.search(text)
        if not match:
            continue
        date_text = match.group("date")
        time_text = match.group("time").replace(".", ":")
        try:
            return datetime.strptime(f"{date_text} {time_text}", "%d.%m.%Y %H:%M")
        except ValueError:
            continue
    return None


def normalize_text(value: str) -> str:
    normalized = value.lower().replace("№", "no")
    normalized = re.sub(r"[–—-]+", " ", normalized)
    normalized = re.sub(r"[^0-9a-zа-яё]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def build_division_aliases(config_path: Path) -> tuple[list[DivisionAlias], list[SubdivisionSeed]]:
    if not config_path.exists():
        return [], []

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    aliases: list[DivisionAlias] = []
    subdivisions: list[SubdivisionSeed] = []
    seen_ids: set[int] = set()
    for pu_entry in data.get("pus") or []:
        for subdivision in pu_entry.get("subdivisions") or []:
            subdivision_id = subdivision.get("id")
            if subdivision_id is None:
                continue
            subdivision_id = int(subdivision_id)
            fullname = subdivision.get("fullname") or subdivision.get("full_name")
            if not fullname:
                fullname = _build_full_name(
                    subdivision.get("type"),
                    subdivision.get("number"),
                    subdivision.get("name"),
                    subdivision.get("locality"),
                )
            subdivision_seed = SubdivisionSeed(id=subdivision_id, fullname=str(fullname))
            if subdivision_id not in seen_ids:
                subdivisions.append(subdivision_seed)
                seen_ids.add(subdivision_id)
            raw_aliases = list(subdivision.get("aliases") or [])
            short_name = _build_short_name(subdivision.get("type"), subdivision.get("number"), subdivision.get("name"))
            if short_name:
                raw_aliases.append(short_name)
            raw_aliases.append(str(fullname))
            for alias in raw_aliases:
                alias_normalized = normalize_text(str(alias))
                if alias_normalized:
                    aliases.append(DivisionAlias(alias_normalized, subdivision_seed))

    aliases.sort(key=lambda entry: len(entry.alias_normalized), reverse=True)
    return aliases, subdivisions


def match_subdivision(text: str, aliases: Iterable[DivisionAlias]) -> SubdivisionSeed | None:
    normalized_text = normalize_text(text)
    for entry in aliases:
        if entry.alias_normalized and entry.alias_normalized in normalized_text:
            return entry.subdivision
    return None


def extract_offenders(text: str) -> list[OffenderSeed]:
    offenders: list[OffenderSeed] = []
    spans: list[tuple[int, int]] = []
    for match in _FULL_NAME_RE.finditer(text):
        last_name, first_name, middle_name = match.groups()
        date_of_birth = _extract_birth_date(text, match.end())
        offenders.append(
            OffenderSeed(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
            )
        )
        spans.append((match.start(), match.end()))

    for match in _INITIALS_RE.finditer(text):
        if any(start <= match.start() <= end for start, end in spans):
            continue
        last_name, first_initial, middle_initial = match.groups()
        date_of_birth = _extract_birth_date(text, match.end())
        offenders.append(
            OffenderSeed(
                first_name=first_initial,
                middle_name=middle_initial,
                last_name=last_name,
                date_of_birth=date_of_birth,
            )
        )
    return offenders


def _extract_birth_date(text: str, start: int, window: int = 60) -> date | None:
    fragment = text[start : start + window]
    date_match = _DATE_RE.search(fragment)
    if date_match:
        try:
            return datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
        except ValueError:
            return None
    if _YEAR_RE.search(fragment):
        return None
    return None


def case_for_index(index: int) -> str:
    if index % 5 == 0:
        return "BAD"
    if index % 3 == 0:
        return "PARTIAL"
    return "OK"


def build_seed_data(
    docx_path: Path,
    divisions_path: Path,
    *,
    limit: int = MAX_DOCX_EVENTS,
) -> tuple[dict[int, str], list[EventSeed]]:
    paragraphs = read_docx_paragraphs(docx_path, limit=limit)
    aliases, known_subdivisions = build_division_aliases(divisions_path)
    used_subdivisions: dict[int, str] = {}
    events: list[EventSeed] = []
    fallback_id = build_stable_subdivision_id(DEFAULT_SUBDIVISION_NAME)

    for index, paragraph in enumerate(paragraphs, start=1):
        timestamp = parse_timestamp(paragraph) or (DEFAULT_EVENT_START + timedelta(minutes=index))
        subdivision = match_subdivision(paragraph, aliases) or SubdivisionSeed(
            id=fallback_id,
            fullname=DEFAULT_SUBDIVISION_NAME,
        )
        offenders = extract_offenders(paragraph)
        event_id = build_event_uuid(timestamp, subdivision.fullname, index)

        case = case_for_index(index)
        event_timestamp = timestamp
        event_subdivision = subdivision
        if case == "PARTIAL":
            offenders = apply_partial_case(offenders, index)
        elif case == "BAD":
            if index % 2 == 0:
                event_timestamp = timestamp + timedelta(minutes=60)
            else:
                alternative = pick_alternative_subdivision(subdivision, known_subdivisions, index)
                if alternative:
                    event_subdivision = alternative

        used_subdivisions[event_subdivision.id] = event_subdivision.fullname
        events.append(
            EventSeed(
                id=event_id,
                subdivision_id=event_subdivision.id,
                date_detection=event_timestamp,
                offenders=offenders,
                event_type_name=None,
            )
        )

    return used_subdivisions, events


def apply_partial_case(offenders: list[OffenderSeed], index: int) -> list[OffenderSeed]:
    if not offenders:
        return offenders
    if len(offenders) > 1 and index % 2 == 0:
        return offenders[:-1]
    updated: list[OffenderSeed] = []
    for offender in offenders:
        updated.append(
            OffenderSeed(
                first_name=offender.first_name,
                middle_name=offender.middle_name,
                last_name=offender.last_name,
                date_of_birth=None,
            )
        )
    return updated


def pick_alternative_subdivision(
    current: SubdivisionSeed,
    subdivisions: list[SubdivisionSeed],
    index: int,
) -> SubdivisionSeed | None:
    if not subdivisions:
        return None
    candidate = subdivisions[index % len(subdivisions)]
    if candidate.id != current.id:
        return candidate
    fallback_index = (index + 1) % len(subdivisions)
    fallback = subdivisions[fallback_index]
    return fallback if fallback.id != current.id else None


def build_event_uuid(timestamp: datetime, subdivision_fullname: str, index: int) -> str:
    timestamp_iso = timestamp.isoformat(timespec="seconds")
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"portal:{timestamp_iso}:{subdivision_fullname}:{index}"))


def build_stable_subdivision_id(fullname: str) -> int:
    digest = hashlib.md5(fullname.encode("utf-8")).hexdigest()
    base = int(digest[:8], 16)
    return 2000 + (base % 8000)


def render_seed_sql(subdivisions: dict[int, str], events: list[EventSeed]) -> str:
    lines: list[str] = []
    if subdivisions:
        lines.append("INSERT INTO subdivision (id, fullname, is_test)")
        lines.append("VALUES")
        lines.extend(
            _render_values(
                [
                    (subdivision_id, subdivision_name, True)
                    for subdivision_id, subdivision_name in subdivisions.items()
                ]
            )
        )
        lines.append("ON CONFLICT (id) DO UPDATE")
        lines.append("SET fullname = EXCLUDED.fullname,")
        lines.append("    is_test = EXCLUDED.is_test;")
        lines.append("")

    if events:
        lines.append(
            "INSERT INTO events (id, date_detection, find_subdivision_unit_id, event_type_name, is_test)"
        )
        lines.append("VALUES")
        lines.extend(
            _render_values(
                [
                    (
                        event.id,
                        event.date_detection.strftime("%Y-%m-%d %H:%M:%S"),
                        event.subdivision_id,
                        event.event_type_name,
                        True,
                    )
                    for event in events
                ]
            )
        )
        lines.append("ON CONFLICT (id) DO UPDATE")
        lines.append("SET date_detection = EXCLUDED.date_detection,")
        lines.append("    find_subdivision_unit_id = EXCLUDED.find_subdivision_unit_id,")
        lines.append("    event_type_name = EXCLUDED.event_type_name,")
        lines.append("    is_test = EXCLUDED.is_test;")
        lines.append("")

        offenders_rows: list[tuple[str, str, str | None, str, date | None, bool]] = []
        seen: set[tuple[str, str, str | None, str, date | None]] = set()
        for event in events:
            for offender in event.offenders:
                key = (
                    event.id,
                    offender.first_name,
                    offender.middle_name,
                    offender.last_name,
                    offender.date_of_birth,
                )
                if key in seen:
                    continue
                seen.add(key)
                offenders_rows.append(
                    (
                        event.id,
                        offender.first_name,
                        offender.middle_name,
                        offender.last_name,
                        offender.date_of_birth,
                        True,
                    )
                )

        if offenders_rows:
            lines.append("INSERT INTO offenders (event_id, first_name, middle_name, last_name, date_of_birth, is_test)")
            lines.append("VALUES")
            lines.extend(_render_values(offenders_rows))
            lines.append(
                "ON CONFLICT (event_id, first_name, middle_name, last_name, date_of_birth)"
            )
            lines.append("DO NOTHING;")
    if not lines:
        lines.append("-- No events found in DOCX.")
    return "\n".join(lines).strip() + "\n"


def _render_values(rows: list[tuple[object, ...]]) -> list[str]:
    rendered = []
    for index, row in enumerate(rows):
        suffix = "," if index < len(rows) - 1 else ""
        rendered.append(f"    ({', '.join(_sql_literal(value) for value in row)}){suffix}")
    return rendered


def _sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date):
        return f"'{value.isoformat()}'"
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    return str(value)


def generate_portal_seed_from_docx(docx_path: Path, output_path: Path, divisions_path: Path) -> None:
    subdivisions, events = build_seed_data(docx_path, divisions_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_seed_sql(subdivisions, events), encoding="utf-8")
