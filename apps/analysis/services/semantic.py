from __future__ import annotations

from dataclasses import dataclass

from sentence_transformers import SentenceTransformer, util

from apps.reference.models import SubdivisionRef


@dataclass
class SemanticMatch:
    subdivision: SubdivisionRef | None
    similarity: float


class SubdivisionSemanticService:
    def __init__(self, model_name: str) -> None:
        self.model = SentenceTransformer(model_name)
        self._cache: dict[int, list[float]] = {}

    def _embedding_for(self, subdivision: SubdivisionRef) -> list[float]:
        if subdivision.id in self._cache:
            return self._cache[subdivision.id]
        embedding = self.model.encode(subdivision.full_name)
        self._cache[subdivision.id] = embedding
        return embedding

    def match(self, text: str) -> SemanticMatch:
        subdivisions = list(SubdivisionRef.objects.all())
        if not subdivisions:
            return SemanticMatch(subdivision=None, similarity=0.0)
        text_embedding = self.model.encode(text)
        best_match = None
        best_score = -1.0
        for subdivision in subdivisions:
            score = float(util.cos_sim(text_embedding, self._embedding_for(subdivision)))
            if score > best_score:
                best_score = score
                best_match = subdivision
        return SemanticMatch(subdivision=best_match, similarity=best_score)
