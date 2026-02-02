from __future__ import annotations

from dataclasses import dataclass
import re
import string

from sentence_transformers import SentenceTransformer, util

from apps.reference.models import SubdivisionRef


@dataclass
class SemanticMatch:
    subdivision: SubdivisionRef | None
    similarity: float


class SubdivisionSemanticService:
    _cached_subdivisions: list[SubdivisionRef] | None = None
    _cached_embeddings: object | None = None
    _cached_embedding_entries: list[SubdivisionRef] | None = None

    def __init__(self, model_name: str) -> None:
        self.model = SentenceTransformer(model_name)
        if self.__class__._cached_subdivisions is None:
            self.__class__._cached_subdivisions = list(SubdivisionRef.objects.all())
            texts: list[str] = []
            entries: list[SubdivisionRef] = []
            for subdivision in self.__class__._cached_subdivisions:
                if subdivision.short_name:
                    texts.append(subdivision.short_name)
                    entries.append(subdivision)
                if subdivision.full_name:
                    texts.append(subdivision.full_name)
                    entries.append(subdivision)
            if texts:
                self.__class__._cached_embeddings = self.model.encode(texts)
                self.__class__._cached_embedding_entries = entries
            else:
                self.__class__._cached_embeddings = []
                self.__class__._cached_embedding_entries = []

    @staticmethod
    def _normalize(value: str) -> str:
        lowered = value.lower().replace("ё", "е")
        lowered = re.sub(r"[‐‑‒–—―−]", "-", lowered)
        punctuation = string.punctuation.replace("-", "")
        cleaned = lowered.translate(str.maketrans("", "", punctuation))
        cleaned = re.sub(r"\s+", "", cleaned)
        cleaned = re.sub(r"[^\w-]", "", cleaned)
        return cleaned.strip("-")

    @staticmethod
    def _pz_pattern(value: str) -> tuple[str | None, str | None]:
        short_match = re.match(r"^пз-?(\d+)$", value)
        if short_match:
            return short_match.group(1), "short"
        full_match = re.match(r"^пограничнаязастава(\d+)$", value)
        if full_match:
            return full_match.group(1), "full"
        return None, None

    def match(self, text: str) -> SemanticMatch:
        cached_subdivisions = self.__class__._cached_subdivisions
        cached_embeddings = self.__class__._cached_embeddings
        cached_entries = self.__class__._cached_embedding_entries
        subdivisions = cached_subdivisions if cached_subdivisions is not None else []
        embeddings = cached_embeddings if cached_embeddings is not None else []
        entries = cached_entries if cached_entries is not None else []
        if not subdivisions:
            return SemanticMatch(subdivision=None, similarity=0.0)
        normalized_text = self._normalize(text)
        for subdivision in subdivisions:
            if normalized_text == self._normalize(subdivision.short_name):
                return SemanticMatch(subdivision=subdivision, similarity=1.0)
            if normalized_text == self._normalize(subdivision.full_name):
                return SemanticMatch(subdivision=subdivision, similarity=1.0)
        extracted_number, extracted_form = self._pz_pattern(normalized_text)
        if extracted_number:
            for subdivision in subdivisions:
                short_number, short_form = self._pz_pattern(
                    self._normalize(subdivision.short_name)
                )
                full_number, full_form = self._pz_pattern(
                    self._normalize(subdivision.full_name)
                )
                if (
                    short_number == extracted_number
                    and extracted_form != short_form
                    and short_number is not None
                ) or (
                    full_number == extracted_number
                    and extracted_form != full_form
                    and full_number is not None
                ):
                    return SemanticMatch(subdivision=subdivision, similarity=0.99)
        if len(embeddings) == 0:
            return SemanticMatch(subdivision=None, similarity=0.0)
        text_embedding = self.model.encode(text)
        best_match = None
        best_score = -1.0
        for subdivision, embedding in zip(entries, embeddings):
            score = float(util.cos_sim(text_embedding, embedding))
            if score > best_score:
                best_score = score
                best_match = subdivision
        return SemanticMatch(subdivision=best_match, similarity=best_score)
