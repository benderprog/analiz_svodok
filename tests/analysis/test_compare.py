from datetime import datetime, timedelta

import pytest

from apps.analysis.services.compare import (
    evaluate_time,
    jaccard_similarity,
    normalize_name,
    normalize_offenders,
    rule_two_of_three,
    time_window_percent,
)


def test_normalize_name_replaces_yo():
    assert normalize_name("  Иванов   Пётр ") == "иванов петр"


def test_normalize_offenders_set():
    result = normalize_offenders(["Иванов Иван", "Петров  Петр"])
    assert result == {"иванов иван", "петров петр"}


def test_jaccard_similarity():
    assert jaccard_similarity({"a", "b"}, {"b", "c"}) == 1 / 3


def test_time_window_percent():
    assert time_window_percent(15, 30) == 50


def test_rule_two_of_three():
    assert rule_two_of_three(True, False, True) is True
    assert rule_two_of_three(False, False, True) is False


def test_evaluate_time_window():
    base = datetime(2024, 1, 1, 12, 0)
    candidate = base + timedelta(minutes=10)
    result = evaluate_time(base, candidate, 30, exact=False, allow_near=True)
    assert result.status == "!"
    assert result.percent == pytest.approx(66.6666667)
