from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Setting


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
        Setting.objects.update_or_create(
            key="semantic_threshold_subdivision",
            defaults={"value": 0.80},
        )
        Setting.objects.update_or_create(
            key="time_window_minutes",
            defaults={"value": 30},
        )

        call_command("sync_divisions", file="configs/divisions.yaml")

        self.stdout.write(self.style.SUCCESS("Локальные тестовые данные приложения готовы."))
