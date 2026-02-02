from __future__ import annotations

from datetime import datetime, timedelta

from django.db import connections

from apps.analysis.dto import Offender, PortalEvent


class PortalRepository:
    def fetch_candidates(
        self, timestamp: datetime | None, window_minutes: int
    ) -> list[PortalEvent]:
        events: dict[str, PortalEvent] = {}
        with connections["portal"].cursor() as cursor:
            if timestamp:
                window_start = timestamp - timedelta(minutes=window_minutes)
                window_end = timestamp + timedelta(minutes=window_minutes)
                cursor.execute(
                    """
                    SELECT events.id,
                           events.date_detection,
                           subdivision.fullname
                    FROM events
                    LEFT JOIN subdivision ON events.find_subdivision_unit_id = subdivision.id
                    WHERE events.date_detection BETWEEN %s AND %s
                    """,
                    [window_start, window_end],
                )
            else:
                cursor.execute(
                    """
                    SELECT events.id,
                           events.date_detection,
                           subdivision.fullname
                    FROM events
                    LEFT JOIN subdivision ON events.find_subdivision_unit_id = subdivision.id
                    """
                )
            for event_id, date_detection, fullname in cursor.fetchall():
                events[str(event_id)] = PortalEvent(
                    event_id=str(event_id),
                    date_detection=date_detection,
                    subdivision_name=fullname,
                    subdivision_short_name=fullname,
                    subdivision_full_name=fullname,
                    offenders=[],
                )
        if not events:
            return []
        with connections["portal"].cursor() as cursor:
            cursor.execute(
                """
                SELECT event_id, first_name, middle_name, last_name, date_of_birth
                FROM offenders
                WHERE event_id IN %s
                """,
                [tuple(events.keys())],
            )
            for event_id, first, middle, last, dob in cursor.fetchall():
                events[str(event_id)].offenders.append(
                    Offender(
                        first_name=first,
                        middle_name=middle,
                        last_name=last,
                        date_of_birth=dob,
                    )
                )
        return list(events.values())
