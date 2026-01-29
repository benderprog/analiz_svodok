from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ExtractedEvent:
    paragraph_index: int
    raw_text: str
    timestamp: datetime | None
    subdivision: str | None
    offenders: list[str]


@dataclass
class PortalEvent:
    event_id: str
    date_detection: datetime | None
    subdivision_name: str | None
    offenders: list[str]


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
