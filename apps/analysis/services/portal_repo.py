from __future__ import annotations

from datetime import datetime, timedelta

from django.db import connections

from apps.analysis.dto import Offender, PortalEvent
from apps.analysis.services.portal_queries import get_portal_query
from apps.analysis.models import Event


class PortalRepository:
    def fetch_candidates(
        self, timestamp: datetime | None, window_minutes: int
    ) -> list[PortalEvent]:
        events: dict[str, PortalEvent] = {}
        subdivision_lookup: dict[str, str | None] = {}
        with connections["portal"].cursor() as cursor:
            find_candidates_query = get_portal_query("find_candidates")
            if timestamp is None:
                ts_exact = datetime.utcnow()
                window_start = datetime(1970, 1, 1)
                window_end = datetime(2100, 1, 1)
            else:
                ts_exact = timestamp
                window_start = timestamp - timedelta(minutes=window_minutes)
                window_end = timestamp + timedelta(minutes=window_minutes)

            cursor.execute(
                find_candidates_query,
                {
                    "ts_from": window_start,
                    "ts_to": window_end,
                    "ts_exact": ts_exact,
                    "limit": 200,
                },
            )
            for event_id, date_detection, subdivision_id in cursor.fetchall():
                event_key = str(event_id)
                subdivision_lookup[event_key] = (
                    str(subdivision_id) if subdivision_id is not None else None
                )
                events[event_key] = PortalEvent(
                    event_id=event_key,
                    date_detection=date_detection,
                    subdivision_name=None,
                    subdivision_short_name=None,
                    subdivision_full_name=None,
                    offenders=[],
                )
        if not events:
            return []
        subdivisions = self._fetch_subdivisions(
            {sid for sid in subdivision_lookup.values() if sid}
        )
        for event_id, subdivision_id in subdivision_lookup.items():
            if subdivision_id and subdivision_id in subdivisions:
                fullname = subdivisions[subdivision_id]
                events[event_id].subdivision_name = fullname
                events[event_id].subdivision_short_name = fullname
                events[event_id].subdivision_full_name = fullname

        for event_id in events:
            offenders = self._fetch_offenders(event_id)
            events[event_id].offenders.extend(offenders)
        event_types = self._fetch_event_types(set(events.keys()))
        for event_id, event_type_name in event_types.items():
            if event_id in events:
                events[event_id].event_type_name = event_type_name
        return list(events.values())

    def _fetch_subdivisions(self, subdivision_ids: set[str]) -> dict[str, str]:
        if not subdivision_ids:
            return {}
        fetch_subdivision_query = get_portal_query("fetch_subdivision")
        result: dict[str, str] = {}
        with connections["portal"].cursor() as cursor:
            for subdivision_id in subdivision_ids:
                cursor.execute(fetch_subdivision_query, {"id": subdivision_id})
                row = cursor.fetchone()
                if row:
                    row_id, fullname = row
                    result[str(row_id)] = fullname
        return result

    def _fetch_offenders(self, event_id: str) -> list[Offender]:
        fetch_offenders_query = get_portal_query("fetch_offenders")
        with connections["portal"].cursor() as cursor:
            cursor.execute(fetch_offenders_query, {"event_id": event_id})
            return [
                Offender(
                    first_name=first,
                    middle_name=middle,
                    last_name=last,
                    date_of_birth=dob,
                )
                for first, middle, last, dob in cursor.fetchall()
            ]

    def _fetch_event_types(self, event_ids: set[str]) -> dict[str, str | None]:
        if not event_ids:
            return {}
        events = (
            Event.objects.select_related("event_type")
            .filter(id__in=event_ids)
        )
        return {
            str(event.id): event.event_type.name if event.event_type else None
            for event in events
        }
