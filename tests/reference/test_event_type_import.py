from openpyxl import Workbook

from apps.reference.models import EventType, EventTypePattern
from apps.reference.services.event_type_import import import_event_types_from_xlsx


def _write_workbook(tmp_path, rows):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    path = tmp_path / "event_types.xlsx"
    workbook.save(path)
    return path


def test_import_event_types_allows_type_only_and_ignores_empty_rows(db, tmp_path):
    path = _write_workbook(
        tmp_path,
        [
            ["Тип A", "паттерн A", "12.1"],
            ["Тип B", "", ""],
            [None, None, None],
        ],
    )

    report = import_event_types_from_xlsx(path)

    assert report.types_created == 2
    assert report.patterns_created == 1
    assert report.ignored_rows == 1
    assert EventType.objects.count() == 2
    assert EventTypePattern.objects.count() == 1


def test_import_event_types_errors_when_type_missing(db, tmp_path):
    path = _write_workbook(tmp_path, [[None, "паттерн", "12.1"]])

    report = import_event_types_from_xlsx(path)

    assert report.errors == ["row 1: пустой тип события при заполненных данных"]
    assert EventType.objects.count() == 0


def test_import_event_type_patterns_upsert_without_duplicates(db, tmp_path):
    path = _write_workbook(tmp_path, [["Тип A", "паттерн A", "12.1"]])

    report_first = import_event_types_from_xlsx(path)
    report_second = import_event_types_from_xlsx(path)

    assert report_first.types_created == 1
    assert report_second.types_updated == 1
    assert report_second.patterns_updated == 1
    assert EventTypePattern.objects.count() == 1


def test_import_event_type_allows_long_pattern_text(db, tmp_path):
    long_pattern = "длинный паттерн " + ("x" * 2000)
    path = _write_workbook(tmp_path, [["Тип A", long_pattern, "12.1"]])

    report = import_event_types_from_xlsx(path)

    assert report.patterns_created == 1
    assert EventTypePattern.objects.get().pattern_text == long_pattern


def test_import_event_type_rejects_long_koap_article(db, tmp_path):
    path = _write_workbook(tmp_path, [["Тип A", "паттерн", "1" * 65]])

    report = import_event_types_from_xlsx(path)

    assert report.errors == ["row 1: слишком длинная статья КОАП (>64)"]
    assert EventType.objects.count() == 0
    assert EventTypePattern.objects.count() == 0
