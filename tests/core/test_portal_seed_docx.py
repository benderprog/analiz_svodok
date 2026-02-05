from __future__ import annotations

from datetime import datetime
from pathlib import Path

from apps.core.portal_seed_docx import case_for_index, parse_timestamp, read_docx_paragraphs


def test_parse_timestamp_formats() -> None:
    assert parse_timestamp("В 08.40 02.02.2026 задержан") == datetime(2026, 2, 2, 8, 40)
    assert parse_timestamp("10.01.2024 12:00 службой") == datetime(2024, 1, 10, 12, 0)
    assert parse_timestamp("09.25 02.02.2026 обнаружено") == datetime(2026, 2, 2, 9, 25)


def test_case_for_index_determinism() -> None:
    assert case_for_index(3) == "PARTIAL"
    assert case_for_index(5) == "BAD"
    assert case_for_index(15) == "BAD"


def test_read_docx_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing.docx"
    assert read_docx_paragraphs(missing, allow_missing=True) == []
