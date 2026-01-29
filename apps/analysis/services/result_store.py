from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

import redis
from django.conf import settings


class ResultStore:
    def __init__(self) -> None:
        self.client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.ttl = settings.RESULT_TTL_SECONDS

    def create_job(self, job_id: str) -> None:
        self.client.hset(job_id, mapping={"status": "pending", "progress": 0})
        self.client.expire(job_id, self.ttl)

    def update_progress(self, job_id: str, status: str, progress: int) -> None:
        self.client.hset(job_id, mapping={"status": status, "progress": progress})
        self.client.expire(job_id, self.ttl)

    def set_result(self, job_id: str, result: dict[str, Any]) -> None:
        payload = json.dumps(result, ensure_ascii=False)
        self.client.hset(job_id, mapping={"status": "done", "progress": 100, "result": payload})
        self.client.expire(job_id, self.ttl)

    def get(self, job_id: str) -> dict[str, Any]:
        data = self.client.hgetall(job_id)
        result = data.get("result")
        return {
            "status": data.get("status"),
            "progress": int(data.get("progress", 0)),
            "result": json.loads(result) if result else None,
        }

    def clear(self, job_id: str) -> None:
        self.client.delete(job_id)
