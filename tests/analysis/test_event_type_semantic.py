import numpy as np

from apps.analysis.services import semantic
from apps.analysis.services.semantic import EventTypeSemanticService
from apps.reference.models import EventType, EventTypePattern


class DummyModel:
    def encode(self, texts, normalize_embeddings=False):
        if isinstance(texts, str):
            vector = self._vector(texts)
            return self._normalize(vector) if normalize_embeddings else vector
        vectors = np.stack([self._vector(text) for text in texts])
        if normalize_embeddings:
            vectors = np.stack([self._normalize(vector) for vector in vectors])
        return vectors

    def _vector(self, text: str) -> np.ndarray:
        return np.array([len(text), sum(ord(ch) for ch in text) % 17], dtype=float)

    @staticmethod
    def _normalize(vector: np.ndarray) -> np.ndarray:
        denom = np.linalg.norm(vector)
        if denom == 0:
            return vector
        return vector / denom


def _dummy_cos_sim(a, b):
    a_vec = np.array(a, dtype=float).flatten()
    b_vec = np.array(b, dtype=float).flatten()
    denom = np.linalg.norm(a_vec) * np.linalg.norm(b_vec)
    if denom == 0:
        return 0.0
    return float(np.dot(a_vec, b_vec) / denom)


def test_event_type_semantic_match_smoke(db, monkeypatch):
    monkeypatch.setattr(semantic, "load_semantic_model", lambda _: DummyModel())
    monkeypatch.setattr(semantic.util, "cos_sim", _dummy_cos_sim)
    EventTypeSemanticService._cached_patterns = None
    EventTypeSemanticService._cached_embeddings = None
    EventTypeSemanticService._cached_embedding_patterns = None
    EventTypeSemanticService._cached_embedding_texts = None

    type_a = EventType.objects.create(name="Тип A")
    type_b = EventType.objects.create(name="Тип B")
    EventTypePattern.objects.create(event_type=type_a, pattern_text="пример A")
    EventTypePattern.objects.create(event_type=type_b, pattern_text="пример B")

    service = EventTypeSemanticService("dummy")

    match = service.match("пример A")
    assert match.event_type == type_a

    weak_match = service.match("совсем другое")
    threshold = 0.99
    detected = weak_match.event_type if weak_match.similarity >= threshold else None
    assert detected is None
