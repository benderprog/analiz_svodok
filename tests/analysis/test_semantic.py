import numpy as np
from apps.analysis.services import semantic


class DummyModel:
    def encode(self, text, **kwargs):
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
            self.aliases = []

    sub_one = DummySubdivision("A", "A full")
    sub_two = DummySubdivision("B", "B full")

    semantic.SubdivisionSemanticService._cached_subdivisions = [sub_one, sub_two]
    semantic.SubdivisionSemanticService._cached_embeddings = np.zeros((2, 3))
    semantic.SubdivisionSemanticService._cached_embedding_entries = [sub_one, sub_two]
    semantic.SubdivisionSemanticService._cached_embedding_texts = ["A", "B"]

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
            self.aliases = []

    sub = DummySubdivision("ПЗ-1", "Пограничная застава №1")
    semantic.SubdivisionSemanticService._cached_subdivisions = [sub]
    semantic.SubdivisionSemanticService._cached_embeddings = []
    semantic.SubdivisionSemanticService._cached_embedding_entries = []
    semantic.SubdivisionSemanticService._cached_embedding_texts = []

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
            self.aliases = []

    sub = DummySubdivision("ПЗ-1", "Пограничная застава №1")
    semantic.SubdivisionSemanticService._cached_subdivisions = [sub]
    semantic.SubdivisionSemanticService._cached_embeddings = []
    semantic.SubdivisionSemanticService._cached_embedding_entries = []
    semantic.SubdivisionSemanticService._cached_embedding_texts = []

    service = semantic.SubdivisionSemanticService("dummy-model")
    result = service.match("Пограничная застава №1")

    assert result.subdivision is sub
    assert result.similarity == 1.0


def test_normalize_subdivision_keeps_number():
    normalized = semantic.normalize_subdivision("ПЗ №2")

    assert "2" in normalized
    assert normalized == "пз-2"


def test_match_subdivision_with_noise_words(monkeypatch):
    class NumberModel:
        def encode(self, text, **kwargs):
            if isinstance(text, list):
                return np.array([[0.0] for _ in text])
            return np.array([0.0])

    monkeypatch.setattr(semantic, "SentenceTransformer", lambda _: NumberModel())
    monkeypatch.setattr(semantic.util, "cos_sim", lambda _, embedding: float(embedding[0]))

    class DummySubdivision:
        def __init__(self, short_name: str, full_name: str) -> None:
            self.short_name = short_name
            self.full_name = full_name
            self.aliases = []

    sub_one = DummySubdivision("ПЗ-1", "Пограничная застава №1")
    sub_two = DummySubdivision("ПЗ-2", "Пограничная застава №2")

    semantic.SubdivisionSemanticService._cached_subdivisions = [sub_one, sub_two]
    semantic.SubdivisionSemanticService._cached_embeddings = np.array([[0.1], [0.9]])
    semantic.SubdivisionSemanticService._cached_embedding_entries = [sub_one, sub_two]
    semantic.SubdivisionSemanticService._cached_embedding_texts = [
        "Пограничная застава №1",
        "Пограничная застава №2",
    ]
    semantic.SubdivisionSemanticService._cached_normalized_entries = []

    service = semantic.SubdivisionSemanticService("dummy-model")
    result = service.match("В 12.40 02.02.2026 службой ПЗ-2 выявлены граждане РФ ...")

    assert result.subdivision is sub_two
    assert result.similarity == 0.9


def test_match_filters_candidates_by_number(monkeypatch):
    class NumberModel:
        def encode(self, text, **kwargs):
            if isinstance(text, list):
                return np.array([[0.0] for _ in text])
            return np.array([0.0])

    monkeypatch.setattr(semantic, "SentenceTransformer", lambda _: NumberModel())
    monkeypatch.setattr(semantic.util, "cos_sim", lambda _, embedding: float(embedding[0]))

    class DummySubdivision:
        def __init__(self, short_name: str, full_name: str) -> None:
            self.short_name = short_name
            self.full_name = full_name
            self.aliases = []

    sub_one = DummySubdivision("ПЗ-1", "Пограничная застава №1")
    sub_two = DummySubdivision("ПЗ-2", "Пограничная застава №2")

    semantic.SubdivisionSemanticService._cached_subdivisions = [sub_one, sub_two]
    semantic.SubdivisionSemanticService._cached_embeddings = np.array([[0.9], [0.1]])
    semantic.SubdivisionSemanticService._cached_embedding_entries = [sub_one, sub_two]
    semantic.SubdivisionSemanticService._cached_embedding_texts = [
        "Пограничная застава №1",
        "Пограничная застава №2",
    ]
    semantic.SubdivisionSemanticService._cached_normalized_entries = []

    service = semantic.SubdivisionSemanticService("dummy-model")
    result = service.match("ПЗ №2")

    assert result.subdivision is sub_two


def test_generate_candidates_splits_letter_digit():
    candidates = semantic.generate_candidates("службой ПЗ1 при патрулировании выявлен ...")

    assert "ПЗ-1" in candidates


def test_match_glued_subdivision_code(monkeypatch):
    class CandidateModel:
        def encode(self, text, **kwargs):
            if isinstance(text, list):
                return np.array(
                    [[1.0] if "ПЗ-1" in item else [0.0] for item in text]
                )
            return np.array([0.0])

    monkeypatch.setattr(semantic, "SentenceTransformer", lambda _: CandidateModel())
    monkeypatch.setattr(
        semantic.util,
        "cos_sim",
        lambda candidate_embedding, entry_embedding: float(
            candidate_embedding[0] * entry_embedding[0]
        ),
    )

    class DummySubdivision:
        def __init__(self, short_name: str, full_name: str) -> None:
            self.short_name = short_name
            self.full_name = full_name
            self.aliases = []

    sub_one = DummySubdivision("ПЗ-1", "Пограничная застава №1")
    sub_two = DummySubdivision("ПЗ-2", "Пограничная застава №2")

    semantic.SubdivisionSemanticService._cached_subdivisions = [sub_one, sub_two]
    semantic.SubdivisionSemanticService._cached_embeddings = np.array([[1.0], [0.5]])
    semantic.SubdivisionSemanticService._cached_embedding_entries = [sub_one, sub_two]
    semantic.SubdivisionSemanticService._cached_embedding_texts = [
        "Пограничная застава №1",
        "Пограничная застава №2",
    ]
    semantic.SubdivisionSemanticService._cached_normalized_entries = []

    service = semantic.SubdivisionSemanticService("dummy-model")
    result = service.match("службой ПЗ1 при патрулировании выявлен ...")

    assert result.subdivision is sub_one
