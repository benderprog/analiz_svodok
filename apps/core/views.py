from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from markdown import markdown


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
