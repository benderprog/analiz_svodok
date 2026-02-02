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
    _cached_normalized_entries: list[tuple[str, SubdivisionRef]] | None = None

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
            normalized_entries: list[tuple[str, SubdivisionRef]] = []
            for subdivision in self.__class__._cached_subdivisions:
                candidates = [subdivision.short_name, subdivision.full_name]
                candidates.extend(self._generate_aliases(subdivision.full_name))
                for candidate in candidates:
                    normalized = self._normalize(candidate)
                    if normalized:
                        normalized_entries.append((normalized, subdivision))
            self.__class__._cached_normalized_entries = normalized_entries

    @staticmethod
    def _pre_normalize(value: str) -> str:
        lowered = value.lower().replace("ё", "е")
        lowered = re.sub(r"[‐‑‒–—―−]", "-", lowered)
        cleaned = re.sub(r"[\"'«»()\\[\\]{}]", "", lowered)
        cleaned = cleaned.replace(".", "")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    @classmethod
    def _normalize(cls, value: str | None) -> str:
        if not value:
            return ""
        cleaned = cls._pre_normalize(value)
        cleaned = cleaned.replace(" ", "")
        cleaned = cleaned.replace("-", "")
        punctuation = string.punctuation.replace("-", "")
        cleaned = cleaned.translate(str.maketrans("", "", punctuation))
        cleaned = re.sub(r"[^\w-]", "", cleaned)
        return cleaned.strip("-")

    @classmethod
    def _generate_aliases(cls, full_name: str | None) -> list[str]:
        if not full_name:
            return []
        normalized = cls._pre_normalize(full_name)
        aliases: list[str] = []
        pz_match = re.search(
            r"пограничная\s+застава\s*№?\s*(\d+)", normalized, re.IGNORECASE
        )
        if pz_match:
            number = pz_match.group(1)
            aliases.extend(
                [
                    f"пз-{number}",
                    f"пз {number}",
                    f"пз№{number}",
                    f"пз №{number}",
                    f"пз{number}",
                    f"пз- {number}",
                    f"погран застава №{number}",
                ]
            )
        opk_match = re.search(
            r"отделение\s+пограничного\s+контроля\s+(.+)",
            normalized,
            re.IGNORECASE,
        )
        if opk_match:
            name_part = opk_match.group(1).strip()
            aliases.extend(
                [
                    f"оп-{name_part}",
                    f"оп {name_part}",
                    f"опк {name_part}",
                    f"опк «{name_part}»",
                    f"отделение пограничного контроля {name_part}",
                ]
            )
        return aliases

    def match(self, text: str) -> SemanticMatch:
        cached_subdivisions = self.__class__._cached_subdivisions
        cached_embeddings = self.__class__._cached_embeddings
        cached_entries = self.__class__._cached_embedding_entries
        normalized_entries = self.__class__._cached_normalized_entries
        subdivisions = cached_subdivisions if cached_subdivisions is not None else []
        embeddings = cached_embeddings if cached_embeddings is not None else []
        entries = cached_entries if cached_entries is not None else []
        normalized_entries = normalized_entries if normalized_entries is not None else []
        if not subdivisions:
            return SemanticMatch(subdivision=None, similarity=0.0)
        normalized_text = self._normalize(text)
        for normalized_candidate, subdivision in normalized_entries:
            if normalized_text == normalized_candidate:
                return SemanticMatch(subdivision=subdivision, similarity=1.0)
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
