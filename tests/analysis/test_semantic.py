import numpy as np
from apps.analysis.services import semantic


class DummyModel:
    def encode(self, text):
        if isinstance(text, list):
            return np.zeros((len(text), 3))
        return np.zeros(3)


def test_match_uses_cached_embeddings(monkeypatch):
    monkeypatch.setattr(semantic, "SentenceTransformer", lambda _: DummyModel())
    monkeypatch.setattr(semantic.util, "cos_sim", lambda *_: 0.5)

    class DummySubdivision:
        def __init__(self, short_name: str, full_name: str) -> None:
            self.short_name = short_name
            self.full_name = full_name

    sub_one = DummySubdivision("A", "A full")
    sub_two = DummySubdivision("B", "B full")

    semantic.SubdivisionSemanticService._cached_subdivisions = [sub_one, sub_two]
    semantic.SubdivisionSemanticService._cached_embeddings = np.zeros((2, 3))
    semantic.SubdivisionSemanticService._cached_embedding_entries = [sub_one, sub_two]

    service = semantic.SubdivisionSemanticService("dummy-model")
    result = service.match("some text")

    assert result.subdivision in (sub_one, sub_two)
    assert result.similarity == 0.5


def test_match_exact_short_name(monkeypatch):
    monkeypatch.setattr(semantic, "SentenceTransformer", lambda _: DummyModel())
    class DummySubdivision:
        def __init__(self, short_name: str, full_name: str) -> None:
            self.short_name = short_name
            self.full_name = full_name

    sub = DummySubdivision("ПЗ-1", "Пограничная застава №1")
    semantic.SubdivisionSemanticService._cached_subdivisions = [sub]
    semantic.SubdivisionSemanticService._cached_embeddings = []
    semantic.SubdivisionSemanticService._cached_embedding_entries = []

    service = semantic.SubdivisionSemanticService("dummy-model")
    result = service.match("ПЗ-1")

    assert result.subdivision is sub
    assert result.similarity == 1.0


def test_match_exact_full_name(monkeypatch):
    monkeypatch.setattr(semantic, "SentenceTransformer", lambda _: DummyModel())
    class DummySubdivision:
        def __init__(self, short_name: str, full_name: str) -> None:
            self.short_name = short_name
            self.full_name = full_name

    sub = DummySubdivision("ПЗ-1", "Пограничная застава №1")
    semantic.SubdivisionSemanticService._cached_subdivisions = [sub]
    semantic.SubdivisionSemanticService._cached_embeddings = []
    semantic.SubdivisionSemanticService._cached_embedding_entries = []

    service = semantic.SubdivisionSemanticService("dummy-model")
    result = service.match("Пограничная застава №1")

    assert result.subdivision is sub
    assert result.similarity == 1.0
