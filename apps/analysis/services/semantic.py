from __future__ import annotations

from dataclasses import dataclass

from sentence_transformers import SentenceTransformer, util

from apps.reference.models import SubdivisionRef


@dataclass
class SemanticMatch:
    subdivision: SubdivisionRef | None
    similarity: float


class SubdivisionSemanticService:
    _cached_subdivisions: list[SubdivisionRef] | None = None
    _cached_embeddings: list[list[float]] | None = None

    def __init__(self, model_name: str) -> None:
        self.model = SentenceTransformer(model_name)
        if self.__class__._cached_subdivisions is None:
            self.__class__._cached_subdivisions = list(SubdivisionRef.objects.all())
            texts = [
                f"{subdivision.short_name} {subdivision.full_name}"
                for subdivision in self.__class__._cached_subdivisions
            ]
            if texts:
                self.__class__._cached_embeddings = self.model.encode(texts)
            else:
                self.__class__._cached_embeddings = []

    def match(self, text: str) -> SemanticMatch:
        subdivisions = self.__class__._cached_subdivisions or []
        embeddings = self.__class__._cached_embeddings or []
        if not subdivisions or not embeddings:
            return SemanticMatch(subdivision=None, similarity=0.0)
        text_embedding = self.model.encode(text)
        best_match = None
        best_score = -1.0
        for subdivision, embedding in zip(subdivisions, embeddings):
            score = float(util.cos_sim(text_embedding, embedding))
            if score > best_score:
                best_score = score
                best_match = subdivision
        return SemanticMatch(subdivision=best_match, similarity=best_score)
