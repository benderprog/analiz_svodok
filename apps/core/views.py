from __future__ import annotations

from pathlib import Path
import os
import time
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import connections
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from markdown import markdown
import redis


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        login_value = request.POST.get("login", "")
        password = request.POST.get("password", "")
        user = authenticate(request, login=login_value, password=password)
        if user:
            login(request, user)
            return redirect("upload")
        messages.error(request, "Неверный логин или пароль")
    return render(request, "login.html")


def root(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("upload")
    return redirect("login")


@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("login")


@login_required
def help_view(request: HttpRequest) -> HttpResponse:
    docs_dir = Path(settings.DOCS_DIR)
    page = request.GET.get("page", "00_overview.md")
    docs_files = sorted(path.name for path in docs_dir.glob("*.md"))
    if page not in docs_files:
        page = "00_overview.md"
    content = (docs_dir / page).read_text(encoding="utf-8")
    html = markdown(content)
    return render(
        request,
        "help.html",
        {
            "docs_files": docs_files,
            "active_page": page,
            "content": html,
        },
    )


logger = logging.getLogger(__name__)


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _check_db(alias: str) -> None:
    connection = connections[alias]
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


@require_http_methods(["GET"])
def health_view(request: HttpRequest) -> JsonResponse:
    start = time.monotonic()
    checks: dict[str, dict[str, object]] = {}

    def record(name: str, action: callable) -> None:
        try:
            extra = action() or {}
            checks[name] = {"ok": True, **extra}
        except Exception as exc:  # noqa: BLE001
            checks[name] = {"ok": False, "error": str(exc)}
            logger.exception("Healthcheck failed for %s", name)

    record("db_default", lambda: _check_db("default"))

    portal_configured = (
        "portal" in settings.DATABASES
        and bool(settings.DATABASES["portal"].get("NAME"))
        and "portal" in connections
    )
    if portal_configured:
        record("db_portal", lambda: _check_db("portal"))
    else:
        checks["db_portal"] = {"ok": True, "skipped": True}

    def check_redis() -> None:
        redis_url = (
            os.environ.get("REDIS_URL")
            or os.environ.get("CELERY_BROKER_URL")
            or settings.REDIS_URL
            or settings.CELERY_BROKER_URL
        )
        client = redis.Redis.from_url(redis_url)
        client.ping()

    record("redis", check_redis)

    def semantic_info() -> dict[str, object]:
        offline = _is_truthy(os.environ.get("HF_HUB_OFFLINE")) or _is_truthy(
            os.environ.get("TRANSFORMERS_OFFLINE")
        )
        return {
            "model_name": settings.SEMANTIC_MODEL_NAME,
            "offline": offline,
        }

    record("semantic_model", semantic_info)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    ok = all(
        check.get("ok", False)
        for check in checks.values()
        if not check.get("skipped")
    )
    payload = {
        "ok": ok,
        "timestamp": timezone.now().isoformat(),
        "version": os.environ.get("APP_VERSION", "dev"),
        "checks": checks,
        "elapsed_ms": elapsed_ms,
    }
    status = 200 if ok else 503
    return JsonResponse(payload, status=status)
