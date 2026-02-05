from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.db import connections, transaction

from apps.core.management.portal_seed import build_local_portal_seed, build_subdivision_uuid


class Command(BaseCommand):
    help = "Bootstrap test data in the local portal database."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Удалить тестовые записи (без drop таблиц) и пересоздать их.",
        )
        parser.add_argument(
            "--scale",
            type=int,
            default=10,
            help="Количество событий (минимум 6, базовые кейсы всегда включены).",
        )

    @transaction.atomic(using="portal")
    def handle(self, *args, **options) -> None:
        reset = options["reset"]
        scale = options["scale"]
        with connections["portal"].cursor() as cursor:
            self._ensure_schema(cursor)
            if reset:
                self._reset_test_data(cursor)
            self._seed_data(cursor, scale)
        self.stdout.write(self.style.SUCCESS("Портальная тестовая БД готова."))

    def _ensure_schema(self, cursor) -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS portal_events (
                id UUID PRIMARY KEY,
                detected_at TIMESTAMP NOT NULL,
                subdivision_id UUID NOT NULL,
                subdivision_fullname TEXT NOT NULL,
                event_type_id UUID NULL,
                event_type_name TEXT NULL,
                raw_text TEXT NOT NULL,
                offenders JSONB NOT NULL DEFAULT '[]',
                is_test BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_portal_events_detected_at ON portal_events (detected_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_portal_events_subdivision_id ON portal_events (subdivision_id)"
        )

    def _reset_test_data(self, cursor) -> None:
        cursor.execute("DELETE FROM portal_events WHERE is_test = true")

    def _seed_data(self, cursor, scale: int) -> None:
        _subdivisions, events, _docx_events = build_local_portal_seed(scale)

        for event in events:
            cursor.execute(
                """
                INSERT INTO portal_events (
                    id,
                    detected_at,
                    subdivision_id,
                    subdivision_fullname,
                    event_type_id,
                    event_type_name,
                    raw_text,
                    offenders,
                    is_test
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, true)
                ON CONFLICT (id)
                DO UPDATE SET
                    detected_at = EXCLUDED.detected_at,
                    subdivision_id = EXCLUDED.subdivision_id,
                    subdivision_fullname = EXCLUDED.subdivision_fullname,
                    event_type_id = EXCLUDED.event_type_id,
                    event_type_name = EXCLUDED.event_type_name,
                    raw_text = EXCLUDED.raw_text,
                    offenders = EXCLUDED.offenders,
                    is_test = EXCLUDED.is_test
                """,
                [
                    event.id,
                    event.date_detection,
                    build_subdivision_uuid(event.subdivision_id),
                    event.subdivision_fullname,
                    event.event_type_id,
                    event.event_type_name,
                    event.raw_text,
                    json.dumps(_serialize_offenders(event.offenders), ensure_ascii=False),
                ],
            )


def _serialize_offenders(offenders) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for offender in offenders:
        payload: dict[str, object] = {
            "last_name": offender.last_name,
            "first_name": offender.first_name,
            "middle_name": offender.middle_name,
        }
        if offender.date_of_birth:
            payload["birth_date"] = offender.date_of_birth.isoformat()
        if offender.birth_year:
            payload["birth_year"] = offender.birth_year
        payloads.append(payload)
    return payloads
