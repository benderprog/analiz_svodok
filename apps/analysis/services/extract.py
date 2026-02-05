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
from pymorphy2 import MorphAnalyzer

from apps.analysis.dto import Offender
from apps.reference.models import SubdivisionRef


@dataclass
class ExtractedAttributes:
    timestamp: datetime | None
    timestamp_has_time: bool
    timestamp_text: str | None
    subdivision_text: str | None
    offenders: list[Offender]


class ExtractService:
    _morph_analyzer: MorphAnalyzer | None = None
    _subdivision_token_stoplist: set[str] | None = None

    def __init__(self) -> None:
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.embedding = NewsEmbedding()
        self.tagger = NewsNERTagger(self.embedding)
        self.date_extractor = DatesExtractor(self.morph_vocab)
        self.name_extractor = NamesExtractor(self.morph_vocab)
        self._birth_date_context_pattern = re.compile(
            r"[\(,]?\s*(?P<date>\d{2}[.\-]\d{2}[.\-]\d{4})\s*[\),]?",
        )
        self._birth_year_pattern = re.compile(r"\b(?P<year>\d{4})\b")
        self._initials_pattern = re.compile(
            r"\b(?P<last>[А-ЯЁ][а-яё]+)\s*(?P<first>[А-ЯЁ])\.?\s*(?P<middle>[А-ЯЁ])\.?\b"
        )
        self._year_markers = {
            "г",
            "гр",
            "год",
            "года",
            "годарождения",
            "годрождения",
        }
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
        offenders = self._extract_offenders(text, doc)
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

    def _extract_offenders(self, text: str, doc: Doc) -> list[Offender]:
        offenders: list[Offender] = []
        per_spans = sorted([span for span in doc.spans if span.type == "PER"], key=lambda s: s.start)
        for index, span in enumerate(per_spans):
            name_match = self._match_name(span.text)
            if not name_match:
                continue
            last_name, first_name, middle_name, start, end, raw_name = name_match
            name_end = span.start + end
            next_name_start = (
                per_spans[index + 1].start if index + 1 < len(per_spans) else len(text)
            )
            context = text[name_end: min(next_name_start, name_end + 80)]
            birth_date, birth_year = self._extract_birth_from_context(context)
            offenders.append(
                Offender(
                    first_name=first_name,
                    middle_name=middle_name,
                    last_name=last_name,
                    date_of_birth=birth_date,
                    birth_year=birth_year,
                    raw=raw_name,
                )
            )

        offenders.extend(self._extract_initials_fallback(text, per_spans))
        return self._filter_false_offenders(offenders)

    def _match_name(
        self, text: str
    ) -> tuple[str, str | None, str | None, int, int, str] | None:
        matches = list(self.name_extractor(text))
        if matches:
            match = matches[0]
            fact = match.fact
            if fact.last:
                start, end, raw = self._match_to_span(text, match)
                return fact.last, fact.first, fact.middle, start, end, raw
        parts = [part for part in text.split() if part]
        if len(parts) >= 2:
            last_name = parts[0]
            first_name = parts[1]
            middle_name = parts[2] if len(parts) > 2 else None
            raw = " ".join(parts[:3]) if middle_name else " ".join(parts[:2])
            return last_name, first_name, middle_name, 0, len(raw), raw
        return None

    def _extract_initials_fallback(
        self, text: str, per_spans: list
    ) -> list[Offender]:
        offenders: list[Offender] = []
        for match in self._initials_pattern.finditer(text):
            if any(self._overlaps(match.start(), match.end(), (span.start, span.stop)) for span in per_spans):
                continue
            last_name = match.group("last")
            first_initial = match.group("first")
            middle_initial = match.group("middle")
            name_end = match.end()
            context = text[name_end: min(len(text), name_end + 80)]
            birth_date, birth_year = self._extract_birth_from_context(context)
            offenders.append(
                Offender(
                    first_name=first_initial,
                    middle_name=middle_initial,
                    last_name=last_name,
                    date_of_birth=birth_date,
                    birth_year=birth_year,
                    raw=match.group(0),
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

    def _extract_birth_from_context(self, context: str) -> tuple[date | None, int | None]:
        birth_date = None
        for match in self._birth_date_context_pattern.finditer(context):
            date_text = match.group("date").replace("-", ".")
            try:
                birth_date = datetime.strptime(date_text, "%d.%m.%Y").date()
                break
            except ValueError:
                continue
        if birth_date:
            return birth_date, None

        year_only = self._extract_birth_year_immediate(context)
        if year_only is not None:
            return None, year_only

        tokens = self._tokenize_context(context)
        for match in self._birth_year_pattern.finditer(context):
            year = int(match.group("year"))
            token_index = self._token_index(tokens, match.start(), match.end())
            if token_index is None:
                continue
            if self._has_year_marker(tokens, token_index):
                return None, year
        return None, None

    def _extract_birth_year_immediate(self, context: str) -> int | None:
        match = re.match(r"^[\s,\(\[]*(?P<year>\d{4})\b", context)
        if not match:
            return None
        if match.start("year") > 5:
            return None
        year = int(match.group("year"))
        if not self._is_birth_year_in_range(year):
            return None
        return year

    def _is_birth_year_in_range(self, year: int) -> bool:
        current_year = datetime.now().year
        return 1900 <= year <= current_year - 10

    def _filter_false_offenders(self, offenders: list[Offender]) -> list[Offender]:
        filtered: list[Offender] = []
        for offender in offenders:
            token = self._single_word_offender(offender)
            if not token:
                filtered.append(offender)
                continue
            cleaned = self._normalize_stoplist_token(token)
            if not cleaned:
                filtered.append(offender)
                continue
            if self._is_adjective(cleaned):
                continue
            stoplist = self._get_subdivision_token_stoplist()
            if stoplist and cleaned.lower() in stoplist:
                continue
            filtered.append(offender)
        return filtered

    def _single_word_offender(self, offender: Offender) -> str | None:
        parts = [offender.last_name, offender.first_name, offender.middle_name]
        present = [part for part in parts if part]
        if len(present) != 1:
            return None
        token = present[0]
        if " " in token:
            return None
        return token

    def _normalize_stoplist_token(self, token: str) -> str:
        return token.strip(".,;:()[]{}\"'«»")

    def _is_adjective(self, token: str) -> bool:
        analyzer = self._get_morph_analyzer()
        for parsed in analyzer.parse(token):
            if parsed.tag.POS in {"ADJF", "ADJS"}:
                return True
        return False

    def _get_morph_analyzer(self) -> MorphAnalyzer:
        if self.__class__._morph_analyzer is None:
            self.__class__._morph_analyzer = MorphAnalyzer()
        return self.__class__._morph_analyzer

    def _get_subdivision_token_stoplist(self) -> set[str]:
        cached = self.__class__._subdivision_token_stoplist
        if cached is not None:
            return cached
        try:
            subdivisions = SubdivisionRef.objects.all()
        except Exception:
            return set()
        stoplist: set[str] = set()
        for subdivision in subdivisions:
            values = [subdivision.full_name] + list(subdivision.aliases or [])
            for value in values:
                if not value:
                    continue
                for token in value.split():
                    cleaned = self._normalize_stoplist_token(token)
                    if len(cleaned) < 4:
                        continue
                    if any(char.isdigit() for char in cleaned):
                        continue
                    stoplist.add(cleaned.lower())
        self.__class__._subdivision_token_stoplist = stoplist
        return stoplist

    def _tokenize_context(self, text: str) -> list[dict[str, object]]:
        tokens: list[dict[str, object]] = []
        for match in re.finditer(r"[0-9A-Za-zА-Яа-яЁё\.]+", text):
            token = match.group(0)
            tokens.append(
                {
                    "start": match.start(),
                    "end": match.end(),
                    "text": token,
                    "norm": self._normalize_token(token),
                }
            )
        return tokens

    def _token_index(
        self, tokens: list[dict[str, object]], start: int, end: int
    ) -> int | None:
        for idx, token in enumerate(tokens):
            if token["start"] <= start < token["end"] or token["start"] < end <= token["end"]:
                return idx
        return None

    def _normalize_token(self, token: str) -> str:
        return token.lower().replace(".", "")

    def _has_year_marker(self, tokens: list[dict[str, object]], index: int) -> bool:
        start = max(0, index - 2)
        end = min(len(tokens), index + 3)
        window = tokens[start:end]
        norms = [token["norm"] for token in window]
        if any(norm in self._year_markers for norm in norms):
            return True
        for idx in range(len(window) - 1):
            if window[idx]["norm"] == "г" and window[idx + 1]["norm"] == "р":
                return True
        if "года" in norms and "рождения" in norms:
            return True
        return False

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
        return bool(
            re.search(
                r"(г\.?\s*р\.?|род\.?|года рождения|год рождения)",
                window,
                re.IGNORECASE,
            )
        )
