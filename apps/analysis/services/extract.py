from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from natasha import (
    DatesExtractor,
    Doc,
    MorphVocab,
    NewsEmbedding,
    NewsNERTagger,
    Segmenter,
)


@dataclass
class ExtractedAttributes:
    timestamp: datetime | None
    offenders: list[str]


class ExtractService:
    def __init__(self) -> None:
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.embedding = NewsEmbedding()
        self.tagger = NewsNERTagger(self.embedding)
        self.date_extractor = DatesExtractor(self.morph_vocab)

    def extract(self, text: str) -> ExtractedAttributes:
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_ner(self.tagger)
        offenders: list[str] = []
        for span in doc.spans:
            if span.type == "PER":
                span.normalize(self.morph_vocab)
                offenders.append(span.normal)

        timestamp = None
        date_matches = list(self.date_extractor(text))
        if date_matches:
            timestamp = date_matches[0].fact.as_datetime()

        return ExtractedAttributes(timestamp=timestamp, offenders=offenders)
