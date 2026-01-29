from __future__ import annotations

import uuid
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.analysis.services.result_store import ResultStore
from apps.analysis.tasks import analyze_docx


@login_required
@require_http_methods(["GET", "POST"])
def upload_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        file = request.FILES.get("docx")
        if not file:
            return render(request, "upload.html", {"error": "Файл не выбран"})
        job_id = uuid.uuid4()
        temp_path = Path("/tmp") / f"{job_id}.docx"
        with temp_path.open("wb") as handle:
            for chunk in file.chunks():
                handle.write(chunk)
        store = ResultStore()
        store.create_job(str(job_id))
        analyze_docx.delay(str(job_id), str(temp_path))
        return redirect("progress", job_id=job_id)
    return render(request, "upload.html")


@login_required
def progress_view(request: HttpRequest, job_id: uuid.UUID) -> HttpResponse:
    store = ResultStore()
    data = store.get(str(job_id))
    if request.GET.get("format") == "json":
        return JsonResponse(data)
    return render(request, "progress.html", {"job_id": job_id, "data": data})


@login_required
def result_view(request: HttpRequest, job_id: uuid.UUID) -> HttpResponse:
    store = ResultStore()
    data = store.get(str(job_id))
    return render(request, "result.html", {"job_id": job_id, "data": data})


@login_required
def clear_view(request: HttpRequest, job_id: uuid.UUID) -> HttpResponse:
    store = ResultStore()
    store.clear(str(job_id))
    return redirect("upload")
