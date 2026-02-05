from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import importlib.util
from typing import Iterable, TextIO

from django.db import transaction

from apps.reference.models import EventType, EventTypePattern


@dataclass
class EventTypeImportReport:
    types_created: int = 0
    types_updated: int = 0
    patterns_created: int = 0
    patterns_updated: int = 0
    ignored_rows: int = 0
    errors: list[str] = field(default_factory=list)

    def add_error(self, row_number: int, reason: str) -> None:
        self.errors.append(f"row {row_number}: {reason}")


def _normalize_cell(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _iter_rows(values: Iterable[tuple[object | None, ...]]) -> Iterable[tuple[str, str, str]]:
    for row in values:
        if not row:
            yield "", "", ""
            continue
        col_a = _normalize_cell(row[0]) if len(row) > 0 else ""
        col_b = _normalize_cell(row[1]) if len(row) > 1 else ""
        col_c = _normalize_cell(row[2]) if len(row) > 2 else ""
        yield col_a, col_b, col_c


def import_event_types_from_xlsx(
    source: str | TextIO, *, dry_run: bool = False
) -> EventTypeImportReport:
    if importlib.util.find_spec("openpyxl") is None:
        raise RuntimeError(
            "Для импорта XLSX требуется пакет openpyxl. "
            "Установите зависимости: pip install -r requirements.txt"
        )
    load_workbook = importlib.import_module("openpyxl").load_workbook
    workbook = load_workbook(source, data_only=True)
    sheet = workbook.active
    report = EventTypeImportReport()

    name_max_length = EventType._meta.get_field("name").max_length or 0
    koap_max_length = EventTypePattern._meta.get_field("koap_article").max_length or 0

    with transaction.atomic():
        for row_index, (type_name, pattern_text, koap_article) in enumerate(
            _iter_rows(sheet.iter_rows(values_only=True)), start=1
        ):
            if not type_name and not pattern_text and not koap_article:
                report.ignored_rows += 1
                continue
            if not type_name and (pattern_text or koap_article):
                report.add_error(row_index, "пустой тип события при заполненных данных")
                continue
            if name_max_length and len(type_name) > name_max_length:
                report.add_error(
                    row_index,
                    f"слишком длинное имя типа события (>{name_max_length})",
                )
                continue
            if koap_max_length and len(koap_article) > koap_max_length:
                report.add_error(
                    row_index,
                    f"слишком длинная статья КОАП (>{koap_max_length})",
                )
                continue

            event_type, created = EventType.objects.update_or_create(
                name=type_name,
                defaults={"is_active": True},
            )
            if created:
                report.types_created += 1
            else:
                report.types_updated += 1

            if not pattern_text:
                continue

            pattern, created = EventTypePattern.objects.update_or_create(
                event_type=event_type,
                pattern_text=pattern_text,
                koap_article=koap_article,
                defaults={"is_active": True},
            )
            if created:
                report.patterns_created += 1
            else:
                if not pattern.is_active:
                    pattern.is_active = True
                    pattern.save(update_fields=["is_active"])
                report.patterns_updated += 1

        if dry_run:
            transaction.set_rollback(True)

    return report
