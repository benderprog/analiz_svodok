import re

from apps.analysis.services.extract import ExtractService
from datetime import datetime


def test_match_to_span_with_re_match():
    service = ExtractService()
    text = "Иванов Иван Иванович"
    match = re.search(r"Иванов", text)
    assert match is not None

    start, end, raw = service._match_to_span(text, match)

    assert (start, end) == (0, 6)
    assert raw == "Иванов"


def test_extract_offenders_does_not_crash():
    service = ExtractService()
    text = "Иванов Иван Иванович 01.01.1990 совершил событие."
    result = service.extract(text)

    assert result.offenders
    offender = result.offenders[0]
    assert offender.raw is None or offender.raw in text


def test_extract_birth_date_from_full_name():
    service = ExtractService()
    text = "Иванов Иван Иванович 05.05.1990"

    result = service.extract(text)

    assert result.offenders
    offender = result.offenders[0]
    assert offender.date_of_birth == datetime(1990, 5, 5).date()
    assert offender.birth_year is None


def test_extract_birth_year_after_name_without_marker():
    service = ExtractService()
    text = "Иванова Мария Ивановна 1990"

    result = service.extract(text)

    assert result.offenders
    offender = result.offenders[0]
    assert offender.birth_year == 1990


def test_extract_birth_year_after_name_with_comma():
    service = ExtractService()
    text = "Иванова Мария Ивановна, 1990"

    result = service.extract(text)

    assert result.offenders
    offender = result.offenders[0]
    assert offender.birth_year == 1990


def test_extract_birth_year_after_name_with_parenthesis():
    service = ExtractService()
    text = "Иванова Мария Ивановна (1990)"

    result = service.extract(text)

    assert result.offenders
    offender = result.offenders[0]
    assert offender.birth_year == 1990


def test_extract_birth_year_with_marker():
    service = ExtractService()
    text = "Иванова Мария Ивановна 1990 г.р."

    result = service.extract(text)

    assert result.offenders
    offender = result.offenders[0]
    assert offender.birth_year == 1990
    assert offender.date_of_birth is None


def test_extract_birth_year_not_immediate():
    service = ExtractService()
    text = "Иванова Мария Ивановна задержана. Номер дела 1990."

    result = service.extract(text)

    assert result.offenders
    offender = result.offenders[0]
    assert offender.birth_year is None


def test_extract_initials_with_birth_year():
    service = ExtractService()
    text = "Иванов И.И. 1991 г.р."

    result = service.extract(text)

    assert result.offenders
    offender = result.offenders[0]
    assert offender.last_name == "Иванов"
    assert offender.birth_year == 1991


def test_extract_event_datetime_subdivision_offenders():
    service = ExtractService()
    text = (
        "В 10.00 31.01.2026 произошло происшествие подразделения ПЗ-1 "
        "при участии Иванов Иван Иванович, 10.05.1991 г.р., по адресу."
    )

    result = service.extract(text)

    assert result.timestamp == datetime(2026, 1, 31, 10, 0)
    assert result.timestamp_has_time is True
    assert result.subdivision_text is not None
    assert "ПЗ-1" in result.subdivision_text
    assert len(result.offenders) == 1
    offender = result.offenders[0]
    assert offender.last_name == "Иванов"
    assert offender.first_name == "Иван"
    assert offender.middle_name == "Иванович"
    assert offender.date_of_birth == datetime(1991, 5, 10).date()
    assert offender.birth_year is None
    assert all(
        word not in (offender.raw or "")
        for word in ("В", "при", "по")
    )


def test_extract_multiple_offenders_birth_dates():
    service = ExtractService()
    text = (
        "К ответственности привлечены Иванов Иван Иванович, 10.05.1991 г.р., "
        "Петров Петр Петрович (05.05.1996), и Сидоров Сидор Сидорович, 1990 г.р."
    )

    result = service.extract(text)

    assert len(result.offenders) == 3
    assert result.offenders[0].date_of_birth == datetime(1991, 5, 10).date()
    assert result.offenders[1].date_of_birth == datetime(1996, 5, 5).date()
    assert result.offenders[2].date_of_birth is None
    assert result.offenders[2].birth_year == 1990


def test_extract_subdivision_text_from_opk_marker():
    service = ExtractService()
    text = (
        "В 09.25 сотрудниками отделения пограничного контроля Центральное "
        "осуществлены мероприятия."
    )

    result = service.extract(text)

    assert result.subdivision_text is not None
    assert "централь" in result.subdivision_text.lower()


def test_extract_subdivision_text_from_pz_marker():
    service = ExtractService()
    text = "В 10.35 на участке ПЗ №2 выявлено событие."

    result = service.extract(text)

    assert result.subdivision_text is not None
    assert "пз" in result.subdivision_text.lower()
    assert "2" in result.subdivision_text


def test_extract_subdivision_window_trims_noise():
    service = ExtractService()
    text = "В 12.40 02.02.2026 службой ПЗ-2 выявлены граждане РФ и составлен акт."

    result = service.extract(text)

    assert result.subdivision_text is not None
    assert result.subdivision_text == "службой ПЗ-2"
