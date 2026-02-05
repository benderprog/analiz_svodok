from datetime import date, datetime, timedelta

from apps.analysis.services.compare import (
    CompareService,
    dedupe_offenders,
    evaluate_time,
    jaccard_similarity,
    normalize_name,
    normalize_offenders,
    rule_two_of_three,
)
from apps.analysis.dto import ExtractedEvent, Offender, PortalEvent


def test_normalize_name_replaces_yo():
    assert normalize_name("  Иванов   Пётр ") == "иванов петр"


def test_normalize_offenders_set():
    offenders = [
        Offender(first_name="Иван", middle_name=None, last_name="Иванов"),
        Offender(first_name="Петр", middle_name=None, last_name="Петров"),
    ]
    result = normalize_offenders(offenders)
    assert result == {"иванов иван", "петров петр"}


def test_jaccard_similarity():
    assert jaccard_similarity({"a", "b"}, {"b", "c"}) == 1 / 3


def test_rule_two_of_three():
    assert rule_two_of_three(True, False, True) is True
    assert rule_two_of_three(False, False, True) is False


def test_evaluate_time_window():
    base = datetime(2024, 1, 1, 12, 0)
    candidate = base + timedelta(minutes=10)
    result = evaluate_time(base, candidate, 30, has_time=True)
    assert result.status == "!"
    assert result.percent is None
    assert result.timestamp_delta_minutes == -10
    assert result.timestamp_delta_human == "-10 мин"


def test_jaccard_offenders_diff():
    extracted = [
        Offender(first_name="Иван", middle_name=None, last_name="Иванов"),
        Offender(first_name="Петр", middle_name=None, last_name="Петров"),
    ]
    matched = [
        Offender(first_name="Иван", middle_name=None, last_name="Иванов"),
        Offender(first_name="Анна", middle_name=None, last_name="Сидорова"),
    ]
    similarity = jaccard_similarity(normalize_offenders(extracted), normalize_offenders(matched))
    assert similarity == 1 / 3


def test_compare_offenders_diff_and_status():
    extracted_event = ExtractedEvent(
        paragraph_index=0,
        raw_text="Текст",
        timestamp=datetime(2024, 1, 1, 12, 0),
        timestamp_has_time=True,
        timestamp_text="01.01.2024 12:00",
        subdivision_text="Отдел А",
        subdivision_name="Отдел А",
        subdivision_similarity=0.9,
        offenders=[
            Offender(first_name="Иван", middle_name=None, last_name="Иванов", birth_year=1991),
            Offender(first_name="Петр", middle_name=None, last_name="Петров"),
        ],
    )
    portal_event = PortalEvent(
        event_id="1",
        date_detection=datetime(2024, 1, 1, 12, 0),
        subdivision_name="Отдел А",
        subdivision_short_name="Отдел А",
        subdivision_full_name="Отдел А",
        offenders=[
            Offender(
                first_name="Иван", middle_name=None, last_name="Иванов", date_of_birth=date(1992, 1, 1)
            ),
            Offender(first_name="Петр", middle_name=None, last_name="Петров"),
        ],
    )
    result = CompareService().compare(extracted_event, [portal_event], 0.8, 30)
    offenders_status = result["attributes"]["offenders"]
    assert offenders_status["status"] == "!"
    assert "Несовпадение ДР" in " ".join(result["explanation"])


def test_dedupe_offenders_in_output():
    duplicate = Offender(first_name="Иван", middle_name=None, last_name="Иванов", birth_year=1991)
    extracted_event = ExtractedEvent(
        paragraph_index=0,
        raw_text="Текст",
        timestamp=datetime(2024, 1, 1, 12, 0),
        timestamp_has_time=True,
        timestamp_text="01.01.2024 12:00",
        subdivision_text="Отдел А",
        subdivision_name="Отдел А",
        subdivision_similarity=0.9,
        offenders=[duplicate, duplicate],
    )
    portal_event = PortalEvent(
        event_id="1",
        date_detection=datetime(2024, 1, 1, 12, 0),
        subdivision_name="Отдел А",
        subdivision_short_name="Отдел А",
        subdivision_full_name="Отдел А",
        offenders=[duplicate],
    )
    assert len(dedupe_offenders(extracted_event.offenders)) == 1
    result = CompareService().compare(extracted_event, [portal_event], 0.8, 30)
    offenders_status = result["attributes"]["offenders"]
    assert offenders_status["value"].count("Иванов") == 1
