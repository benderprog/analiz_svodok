from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from natasha import (
    DatesExtractor,
    Doc,
    MorphVocab,
    NamesExtractor,
    NewsEmbedding,
    NewsNERTagger,
    Segmenter,
)

from apps.analysis.dto import Offender


@dataclass
class ExtractedAttributes:
    timestamp: datetime | None
    timestamp_has_time: bool
    timestamp_text: str | None
    subdivision_text: str | None
    offenders: list[Offender]


class ExtractService:
    def __init__(self) -> None:
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.embedding = NewsEmbedding()
        self.tagger = NewsNERTagger(self.embedding)
        self.date_extractor = DatesExtractor(self.morph_vocab)
        self.name_extractor = NamesExtractor(self.morph_vocab)

    def extract(self, text: str) -> ExtractedAttributes:
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_ner(self.tagger)
        offenders = self._extract_offenders(text)
        subdivision_text = self._extract_subdivision(doc)
        timestamp, timestamp_has_time, timestamp_text = self._extract_timestamp(text, offenders)

        return ExtractedAttributes(
            timestamp=timestamp,
            timestamp_has_time=timestamp_has_time,
            timestamp_text=timestamp_text,
            subdivision_text=subdivision_text,
            offenders=offenders,
        )

    def _extract_subdivision(self, doc: Doc) -> str | None:
        for span in doc.spans:
            if span.type == "ORG":
                return span.text
        return None

    def _extract_timestamp(
        self, text: str, offenders: list[Offender]
    ) -> tuple[datetime | None, bool, str | None]:
        date_matches = list(self.date_extractor(text))
        if not date_matches:
            return None, False, None

        offender_spans: set[tuple[int, int]] = {
            (span.start, span.stop)
            for span in self.name_extractor(text)
            if span.fact
        }
        candidate = None
        for match in date_matches:
            if any(self._overlaps(match.start, match.stop, span) for span in offender_spans):
                continue
            candidate = match
            if self._has_time(match.fact):
                break
        if candidate is None:
            candidate = date_matches[0]
        dt = self._datetime_from_fact(candidate.fact)
        has_time = self._has_time(candidate.fact)
        return dt, has_time, candidate.text

    def _extract_offenders(self, text: str) -> list[Offender]:
        date_matches = list(self.date_extractor(text))
        offenders: list[Offender] = []
        for match in self.name_extractor(text):
            if not match.fact:
                continue
            birth_fact = self._nearest_birth_date(match.start, match.stop, date_matches)
            birth_date, birth_year = self._birth_date_from_fact(birth_fact.fact) if birth_fact else (None, None)
            offender = Offender(
                first_name=match.fact.first,
                middle_name=match.fact.middle,
                last_name=match.fact.last,
                date_of_birth=birth_date,
                birth_year=birth_year,
                raw=match.span.text if match.span else None,
            )
            offenders.append(offender)
        return offenders

    def _nearest_birth_date(self, start: int, stop: int, matches) -> object | None:
        closest = None
        closest_distance = None
        for match in matches:
            distance = min(abs(match.start - stop), abs(match.stop - start))
            if distance > 40:
                continue
            if closest_distance is None or distance < closest_distance:
                closest = match
                closest_distance = distance
        return closest

    def _birth_date_from_fact(self, fact) -> tuple[date | None, int | None]:
        if fact is None or not getattr(fact, "year", None):
            return None, None
        if getattr(fact, "day", None) and getattr(fact, "month", None):
            try:
                return date(fact.year, fact.month, fact.day), None
            except ValueError:
                return None, None
        return None, fact.year

    def _datetime_from_fact(self, fact) -> datetime | None:
        if fact is None or not getattr(fact, "year", None):
            return None
        month = fact.month or 1
        day = fact.day or 1
        hour = fact.hour or 0
        minute = fact.minute or 0
        try:
            return datetime(fact.year, month, day, hour, minute)
        except ValueError:
            return None

    def _has_time(self, fact) -> bool:
        return bool(getattr(fact, "hour", None) or getattr(fact, "minute", None))

    def _overlaps(self, start: int, stop: int, span: tuple[int, int]) -> bool:
        return not (stop <= span[0] or start >= span[1])
