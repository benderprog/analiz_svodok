import re

from apps.analysis.services.extract import ExtractService


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
    text = "Иванов Иван Иванович 01.01.1990 совершил правонарушение."
    result = service.extract(text)

    assert result.offenders
    offender = result.offenders[0]
    assert offender.raw is None or offender.raw in text
