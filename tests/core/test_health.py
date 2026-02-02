import pytest

from apps.core import views


class DummyRedisClient:
    def ping(self) -> bool:
        return True


@pytest.mark.django_db
def test_health_ok(client, monkeypatch, settings) -> None:
    def dummy_from_url(*_args, **_kwargs) -> DummyRedisClient:
        return DummyRedisClient()

    monkeypatch.setattr(views.redis.Redis, "from_url", staticmethod(dummy_from_url))
    settings.DATABASES = {"default": settings.DATABASES["default"]}

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["checks"]["db_default"]["ok"] is True
