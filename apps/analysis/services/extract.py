from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re

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
        self._name_pattern = re.compile(
            r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2}\b"
        )
        self._birth_date_pattern = re.compile(
            r"(?P<date>\d{2}\.\d{2}\.\d{4})\s*(?:г\.?р\.?|род\.?)",
            re.IGNORECASE,
        )
        self._birth_date_parentheses_pattern = re.compile(
            r"\(\s*(?P<date>\d{2}\.\d{2}\.\d{4})\s*(?:г\.?р\.?|род\.?)?\s*\)",
            re.IGNORECASE,
        )
        self._birth_year_pattern = re.compile(
            r"(?P<year>\d{4})\s*(?:г\.?р\.?|род\.?)",
            re.IGNORECASE,
        )
        self._time_pattern = re.compile(r"\b(?:[01]?\d|2[0-3])[.:][0-5]\d\b")
        self._date_pattern = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")
        self._time_then_date_pattern = re.compile(
            rf"(?:\b[Вв]\s+)?(?P<time>{self._time_pattern.pattern})\s+(?P<date>{self._date_pattern.pattern})"
        )
        self._date_then_time_pattern = re.compile(
            rf"(?P<date>{self._date_pattern.pattern})\s+(?P<time>{self._time_pattern.pattern})"
        )

    def extract(self, text: str) -> ExtractedAttributes:
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_ner(self.tagger)
        offenders = self._extract_offenders(text)
        subdivision_text = self._extract_subdivision(doc)
        timestamp, timestamp_has_time, timestamp_text = self._extract_timestamp(text)

        return ExtractedAttributes(
            timestamp=timestamp,
            timestamp_has_time=timestamp_has_time,
            timestamp_text=timestamp_text,
            subdivision_text=subdivision_text,
            offenders=offenders,
        )

    def _extract_subdivision(self, doc: Doc) -> str | None:
        subdivision_text = self._extract_subdivision_text(doc.text)
        if subdivision_text:
            return subdivision_text
        for span in doc.spans:
            if span.type == "ORG":
                return span.text
        return None

    def _extract_timestamp(self, text: str) -> tuple[datetime | None, bool, str | None]:
        candidates = self._extract_datetime_candidates(text)
        if candidates:
            candidate = candidates[0]
            return candidate["timestamp"], True, candidate["raw"]

        date_only = self._extract_date_only(text)
        if date_only:
            return date_only["timestamp"], False, date_only["raw"]

        return None, False, None

    def _extract_offenders(self, text: str) -> list[Offender]:
        offenders: list[Offender] = []
        name_matches = list(self._name_pattern.finditer(text))
        birth_date_matches = self._extract_birth_date_matches(text)
        birth_year_matches = self._extract_birth_year_matches(text)
        for index, match in enumerate(name_matches):
            raw = match.group(0)
            parts = raw.split()
            if len(parts) not in (2, 3):
                continue
            last_name, first_name = parts[0], parts[1]
            middle_name = parts[2] if len(parts) == 3 else None
            name_end = match.end()
            next_name_start = (
                name_matches[index + 1].start() if index + 1 < len(name_matches) else len(text) + 1
            )
            birth_date = self._birth_date_for_name(name_end, next_name_start, birth_date_matches)
            birth_year = None
            if birth_date is None:
                birth_year = self._birth_year_for_name(
                    name_end, next_name_start, birth_year_matches
                )
            offenders.append(
                Offender(
                    first_name=first_name,
                    middle_name=middle_name,
                    last_name=last_name,
                    date_of_birth=birth_date,
                    birth_year=birth_year,
                    raw=raw,
                )
            )
        return offenders

    def _match_to_span(self, text: str, match: object) -> tuple[int, int, str]:
        start_fn = getattr(match, "start", None)
        end_fn = getattr(match, "end", None)
        if callable(start_fn) and callable(end_fn):
            start = start_fn()
            end = end_fn()
            return start, end, text[start:end]

        if isinstance(getattr(match, "start", None), int) and isinstance(getattr(match, "stop", None), int):
            start = match.start
            end = match.stop
            return start, end, text[start:end]

        span_fn = getattr(match, "span", None)
        if callable(span_fn):
            start, end = span_fn()
            group_fn = getattr(match, "group", None)
            raw = group_fn(0) if callable(group_fn) else text[start:end]
            return start, end, raw

        span_attr = getattr(match, "span", None)
        if span_attr is not None and hasattr(span_attr, "start") and hasattr(span_attr, "stop"):
            start = span_attr.start
            end = span_attr.stop
            return start, end, text[start:end]

        return -1, -1, str(match)

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
        month = getattr(fact, "month", None) or 1
        day = getattr(fact, "day", None) or 1
        hour = getattr(fact, "hour", None) or 0
        minute = getattr(fact, "minute", None) or 0
        try:
            return datetime(fact.year, month, day, hour, minute)
        except ValueError:
            return None

    def _has_time(self, fact) -> bool:
        return bool(getattr(fact, "hour", None) or getattr(fact, "minute", None))

    def _overlaps(self, start: int, stop: int, span: tuple[int, int]) -> bool:
        return not (stop <= span[0] or start >= span[1])

    def _extract_subdivision_text(self, text: str) -> str | None:
        window = self.extract_subdivision_window(text)
        if window:
            return window
        marker_groups: list[list[str]] = [
            [r"\bслужбой\b"],
            [r"\bна посту\b"],
            [r"\bна участке\b"],
            [r"\bподразделени[ея]\b"],
            [r"\bпограничная\s+застава\b", r"\bпз\b"],
            [
                r"\bотделени[ея]\s+пограничного\s+контроля\b",
                r"\bпограничного\s+контроля\b",
                r"\bопк\b",
                r"\bоп\b",
            ],
        ]
        window_length = 160
        for patterns in marker_groups:
            best_match = None
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match and (best_match is None or match.start() < best_match.start()):
                    best_match = match
            if best_match:
                window_end = min(len(text), best_match.end() + window_length)
                window = text[best_match.end():window_end]
                cutoff_match = re.search(r"[.;\n]", window)
                if cutoff_match:
                    window = window[:cutoff_match.start()]
                candidate = window.strip(" ,:\t")
                if candidate:
                    return candidate
        return None

    def extract_subdivision_window(self, full_text: str) -> str | None:
        markers = ["ПОГЗ", "ПЗ", "ОПК", "ОП", "ПОГК", "ПОГО"]
        marker_pattern = re.compile(r"\b(" + "|".join(markers) + r")\b", re.IGNORECASE)
        match = marker_pattern.search(full_text)
        if not match:
            return None
        left_window = 10
        right_window = 80
        start = max(0, match.start() - left_window)
        end = min(len(full_text), match.end() + right_window)
        window = full_text[start:end]
        window = re.sub(r"^[\d\s:.,-]+", "", window)
        split_pattern = re.compile(
            r"(?:[.,;]|\bг\.?\s*р\.?\b|\bрод\.?\b|\bпаспорт\b|\bграждан\w*\b|\bвыявлен\w*\b)",
            re.IGNORECASE,
        )
        parts = re.split(split_pattern, window, maxsplit=1)
        candidate = parts[0].strip(" ,:\t\n")
        return candidate or None

    def _extract_birth_date_matches(self, text: str) -> list[dict[str, object]]:
        matches: list[dict[str, object]] = []
        for pattern in (self._birth_date_pattern, self._birth_date_parentheses_pattern):
            for match in pattern.finditer(text):
                try:
                    parsed = datetime.strptime(match.group("date"), "%d.%m.%Y").date()
                except ValueError:
                    continue
                matches.append({"start": match.start(), "end": match.end(), "date": parsed})
        matches.sort(key=lambda item: item["start"])
        return matches

    def _extract_birth_year_matches(self, text: str) -> list[dict[str, object]]:
        matches: list[dict[str, object]] = []
        for match in self._birth_year_pattern.finditer(text):
            matches.append(
                {"start": match.start(), "end": match.end(), "year": int(match.group("year"))}
            )
        matches.sort(key=lambda item: item["start"])
        return matches

    def _birth_date_for_name(
        self, name_end: int, next_name_start: int, matches: list[dict[str, object]]
    ) -> date | None:
        for match in matches:
            if name_end < match["start"] < next_name_start:
                return match["date"]
        return None

    def _birth_year_for_name(
        self, name_end: int, next_name_start: int, matches: list[dict[str, object]]
    ) -> int | None:
        for match in matches:
            if name_end < match["start"] < next_name_start:
                return match["year"]
        return None

    def _extract_datetime_candidates(self, text: str) -> list[dict[str, object]]:
        candidates: list[dict[str, object]] = []
        for pattern in (self._time_then_date_pattern, self._date_then_time_pattern):
            for match in pattern.finditer(text):
                date_text = match.group("date")
                if self._is_birth_context(text, match.start("date"), match.end("date")):
                    continue
                time_text = match.group("time").replace(".", ":")
                try:
                    timestamp = datetime.strptime(f"{date_text} {time_text}", "%d.%m.%Y %H:%M")
                except ValueError:
                    continue
                candidates.append(
                    {
                        "start": match.start(),
                        "timestamp": timestamp,
                        "raw": match.group(0),
                    }
                )
        candidates.sort(key=lambda item: item["start"])
        return candidates

    def _extract_date_only(self, text: str) -> dict[str, object] | None:
        for match in self._date_pattern.finditer(text):
            if self._is_birth_context(text, match.start(), match.end()):
                continue
            try:
                timestamp = datetime.strptime(match.group(0), "%d.%m.%Y")
            except ValueError:
                continue
            return {"timestamp": timestamp, "raw": match.group(0)}
        return None

    def _is_birth_context(self, text: str, start: int, end: int) -> bool:
        window_start = max(0, start - 10)
        window_end = min(len(text), end + 10)
        window = text[window_start:window_end]
        return bool(re.search(r"(г\.?р\.?|род\.?)", window, re.IGNORECASE))
