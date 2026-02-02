from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class Offender:
    first_name: str | None
    middle_name: str | None
    last_name: str | None
    date_of_birth: date | None = None
    birth_year: int | None = None
    raw: str | None = None

    def display_name(self) -> str:
        parts = [self.last_name, self.first_name, self.middle_name]
        name = " ".join(part for part in parts if part)
        if self.date_of_birth:
            return f"{name} ({self.date_of_birth.isoformat()})"
        if self.birth_year:
            return f"{name} ({self.birth_year})"
        return name


@dataclass
class ExtractedEvent:
    paragraph_index: int
    raw_text: str
    timestamp: datetime | None
    timestamp_has_time: bool
    timestamp_text: str | None
    subdivision_text: str | None
    subdivision_name: str | None
    subdivision_similarity: float | None
    offenders: list[Offender]


@dataclass
class PortalEvent:
    event_id: str
    date_detection: datetime | None
    subdivision_name: str | None
    subdivision_short_name: str | None
    subdivision_full_name: str | None
    offenders: list[Offender]


@dataclass
class AttributeStatus:
    label: str
    status: str | None
    percent: float | None
    value: str | None
    diff: dict[str, Any] | None = None


@dataclass
class MatchResult:
    extracted: ExtractedEvent
    matches: list[PortalEvent]
    attributes: dict[str, AttributeStatus]
    found: bool
    message: str | None = None
