from __future__ import annotations

from datetime import date, datetime, timedelta
import json

from django.db import connections

from apps.analysis.dto import Offender, PortalEvent
from apps.analysis.services.portal_queries import get_portal_query


class PortalRepository:
    def fetch_candidates(
        self, timestamp: datetime | None, window_minutes: int
    ) -> list[PortalEvent]:
        events: list[PortalEvent] = []
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
            for (
                event_id,
                detected_at,
                _subdivision_id,
                subdivision_fullname,
                offenders_payload,
                event_type_name,
            ) in cursor.fetchall():
                event_key = str(event_id)
                offenders = self._parse_offenders(offenders_payload)
                events.append(
                    PortalEvent(
                        event_id=event_key,
                        date_detection=detected_at,
                        subdivision_name=subdivision_fullname,
                        subdivision_short_name=subdivision_fullname,
                        subdivision_full_name=subdivision_fullname,
                        offenders=offenders,
                        event_type_name=event_type_name,
                    )
                )
        return events

    def _parse_offenders(self, payload) -> list[Offender]:
        offenders: list[Offender] = []
        if not payload:
            return offenders
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return offenders
        for item in payload:
            if not isinstance(item, dict):
                continue
            date_of_birth = self._parse_birth_date(item.get("birth_date"))
            birth_year = self._parse_birth_year(item.get("birth_year"))
            offenders.append(
                Offender(
                    first_name=item.get("first_name"),
                    middle_name=item.get("middle_name"),
                    last_name=item.get("last_name"),
                    date_of_birth=date_of_birth,
                    birth_year=birth_year,
                )
            )
        return offenders

    def _parse_birth_date(self, value: object) -> date | None:
        if not value:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
        return None

    def _parse_birth_year(self, value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None
