from __future__ import annotations

from django.db import connections

from apps.analysis.dto import PortalEvent


class PortalRepository:
    def fetch_events(self) -> list[PortalEvent]:
        events: dict[str, PortalEvent] = {}
        with connections["portal"].cursor() as cursor:
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
                offender = " ".join(part for part in [last, first, middle] if part)
                if dob:
                    offender = f"{offender} ({dob})"
                events[str(event_id)].offenders.append(offender)
        return list(events.values())
