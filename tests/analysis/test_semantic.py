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

    service = semantic.SubdivisionSemanticService("dummy-model")
    result = service.match("some text")

    assert result.subdivision in (sub_one, sub_two)
    assert result.similarity == 0.5
