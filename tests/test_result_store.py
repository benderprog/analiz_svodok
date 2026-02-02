from __future__ import annotations

import json
from datetime import date, datetime
from uuid import UUID

from apps.analysis.services.result_store import ResultStore


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, dict[str, str]] = {}

    def hset(self, key: str, mapping: dict[str, str]) -> None:
        self.data.setdefault(key, {}).update(mapping)

    def expire(self, key: str, ttl: int) -> None:
        return None


def test_set_result_serializes_datetime_date_uuid() -> None:
    store = ResultStore()
    store.client = FakeRedis()

    payload = {
        "timestamp": datetime(2024, 1, 2, 3, 4, 5),
        "day": date(2024, 1, 2),
        "identifier": UUID("12345678-1234-5678-1234-567812345678"),
    }

    store.set_result("job-1", payload)

    stored_payload = store.client.data["job-1"]["result"]
    assert json.loads(stored_payload) == {
        "timestamp": "2024-01-02 03:04:05",
        "day": "2024-01-02",
        "identifier": "12345678-1234-5678-1234-567812345678",
    }
