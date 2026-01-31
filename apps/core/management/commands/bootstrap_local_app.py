from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Setting
from apps.reference.models import Pu, SubdivisionRef


TEST_PU = {
    "short_name": "Тестовое ПУ",
    "full_name": "Тестовое подразделение управления",
}

TEST_SUBDIVISIONS = [
    {"short_name": "Отдел 1", "full_name": "Тестовый отдел 1"},
    {"short_name": "Отдел 2", "full_name": "Тестовый отдел 2"},
    {"short_name": "Отдел 3", "full_name": "Тестовый отдел 3"},
    {"short_name": "Отдел 4", "full_name": "Тестовый отдел 4"},
    {"short_name": "Отдел 5", "full_name": "Тестовый отдел 5"},
    {"short_name": "Отдел 6", "full_name": "Тестовый отдел 6"},
]


class Command(BaseCommand):
    help = "Bootstrap test settings, PU and subdivisions for local development."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Удалить тестовые записи (без drop таблиц) и пересоздать их.",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        reset = options["reset"]

        if reset:
            self._reset_test_data()

        Setting.objects.update_or_create(
            key="semantic_threshold_subdivision",
            defaults={"value": 0.80},
        )
        Setting.objects.update_or_create(
            key="time_window_minutes",
            defaults={"value": 30},
        )

        pu, _ = Pu.objects.get_or_create(
            short_name=TEST_PU["short_name"],
            full_name=TEST_PU["full_name"],
        )

        for subdivision in TEST_SUBDIVISIONS:
            SubdivisionRef.objects.get_or_create(
                pu=pu,
                short_name=subdivision["short_name"],
                full_name=subdivision["full_name"],
            )

        self.stdout.write(self.style.SUCCESS("Локальные тестовые данные приложения готовы."))

    def _reset_test_data(self) -> None:
        pu = Pu.objects.filter(
            short_name=TEST_PU["short_name"],
            full_name=TEST_PU["full_name"],
        ).first()
        if not pu:
            return

        subdivision_names = [item["short_name"] for item in TEST_SUBDIVISIONS]
        SubdivisionRef.objects.filter(pu=pu, short_name__in=subdivision_names).delete()
        if not SubdivisionRef.objects.filter(pu=pu).exists():
            pu.delete()
