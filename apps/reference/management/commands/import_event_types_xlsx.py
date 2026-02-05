from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.reference.services.event_type_import import import_event_types_from_xlsx


class Command(BaseCommand):
    help = "Импортировать типы событий и паттерны из XLSX."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--path",
            required=True,
            help="Путь к XLSX файлу.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Проверить файл без сохранения изменений.",
        )

    def handle(self, *args, **options) -> None:
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"Файл не найден: {path}")

        report = import_event_types_from_xlsx(path, dry_run=options["dry_run"])
        self.stdout.write(
            self.style.SUCCESS(
                "Импорт завершен: типов создано "
                f"{report.types_created}, обновлено {report.types_updated}; "
                "паттернов создано "
                f"{report.patterns_created}, обновлено {report.patterns_updated}; "
                f"пустых строк пропущено {report.ignored_rows}."
            )
        )
        if report.errors:
            for error in report.errors:
                self.stdout.write(self.style.ERROR(error))
