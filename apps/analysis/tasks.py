from __future__ import annotations

from celery import shared_task
from django.conf import settings

from apps.analysis.dto import ExtractedEvent
from apps.analysis.services.docx_ingest import DocxIngestService
from apps.analysis.services.extract import ExtractService
from apps.analysis.services.match import MatchService
from apps.analysis.services.portal_repo import PortalRepository
from apps.analysis.services.result_store import ResultStore
from apps.analysis.services.semantic import (
    EventTypeSemanticService,
    SubdivisionSemanticService,
)


@shared_task(bind=True)
def analyze_docx(self, job_id: str, file_path: str) -> None:
    store = ResultStore()
    store.update_progress(job_id, "started", 5)

    ingest = DocxIngestService()
    extract_service = ExtractService()
    semantic_service = SubdivisionSemanticService(settings.SEMANTIC_MODEL_NAME)
    portal_repo = PortalRepository()
    event_type_service = EventTypeSemanticService(settings.SEMANTIC_MODEL_NAME)
    match_service = MatchService(semantic_service, portal_repo, event_type_service)

    paragraphs = ingest.read_paragraphs(file_path)
    results = []
    total = max(len(paragraphs), 1)
    for index, paragraph in enumerate(paragraphs):
        attrs = extract_service.extract(paragraph)
        extracted = ExtractedEvent(
            paragraph_index=index,
            raw_text=paragraph,
            timestamp=attrs.timestamp,
            timestamp_has_time=attrs.timestamp_has_time,
            timestamp_text=attrs.timestamp_text,
            subdivision_text=attrs.subdivision_text,
            subdivision_name=None,
            subdivision_similarity=None,
            offenders=attrs.offenders,
        )
        match = match_service.match_event(extracted)
        results.append(match)
        progress = int(((index + 1) / total) * 90) + 5
        store.update_progress(job_id, "processing", progress)

    store.set_result(job_id, {"items": results})
