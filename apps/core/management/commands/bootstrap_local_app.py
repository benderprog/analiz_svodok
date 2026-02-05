from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Setting
from apps.analysis.models import Event
from apps.reference.models import EventType, EventTypePattern


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

        self._seed_event_types()

        self.stdout.write(self.style.SUCCESS("Локальные тестовые данные приложения готовы."))

    def _seed_event_types(self) -> None:
        detected_type, _ = EventType.objects.update_or_create(
            name="Выявление",
            defaults={"is_active": True},
        )
        detain_type, _ = EventType.objects.update_or_create(
            name="Задержание",
            defaults={"is_active": True},
        )
        inspection_type, _ = EventType.objects.update_or_create(
            name="Проверка",
            defaults={"is_active": True},
        )

        EventTypePattern.objects.update_or_create(
            event_type=detected_type,
            pattern_text="выявлены",
            koap_article="",
            defaults={"is_active": True, "priority": 50},
        )
        EventTypePattern.objects.update_or_create(
            event_type=detain_type,
            pattern_text="задержан",
            koap_article="",
            defaults={"is_active": True, "priority": 50},
        )
        EventTypePattern.objects.update_or_create(
            event_type=detain_type,
            pattern_text="задержаны",
            koap_article="",
            defaults={"is_active": True, "priority": 60},
        )
        EventTypePattern.objects.update_or_create(
            event_type=inspection_type,
            pattern_text="на посту",
            koap_article="",
            defaults={"is_active": True, "priority": 70},
        )

        Event.objects.update_or_create(
            id="11111111-1111-1111-1111-111111111111",
            defaults={"event_type": detected_type},
        )
        Event.objects.update_or_create(
            id="22222222-2222-2222-2222-222222222222",
            defaults={"event_type": inspection_type},
        )
        Event.objects.update_or_create(
            id="33333333-3333-3333-3333-333333333333",
            defaults={"event_type": detected_type},
        )
        Event.objects.update_or_create(
            id="44444444-4444-4444-4444-444444444444",
            defaults={"event_type": detain_type},
        )
