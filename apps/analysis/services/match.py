from __future__ import annotations

from apps.analysis.dto import ExtractedEvent
from apps.analysis.services.compare import CompareService
from apps.analysis.services.portal_repo import PortalRepository
from django.conf import settings

from apps.analysis.services.semantic import (
    EventTypeSemanticService,
    SubdivisionSemanticService,
)


class MatchService:
    def __init__(
        self,
        semantic_service: SubdivisionSemanticService,
        portal_repo: PortalRepository,
        event_type_service: EventTypeSemanticService,
    ) -> None:
        self.semantic_service = semantic_service
        self.portal_repo = portal_repo
        self.compare_service = CompareService()
        self.event_type_service = event_type_service

    def match_event(self, extracted: ExtractedEvent) -> dict:
        settings_values = self._settings()
        threshold = settings_values["semantic_threshold_subdivision"]
        window = settings_values["time_window_minutes"]
        offenders_min_overlap = settings_values["offenders_match_min_overlap"]
        event_type_threshold = float(
            getattr(settings, "EVENT_TYPE_MATCH_THRESHOLD", 0.78)
        )
        subdivision_source = extracted.subdivision_text
        if not subdivision_source and extracted.raw_text:
            subdivision_source = extracted.raw_text[:200].strip()
        if subdivision_source:
            subdivision_match = self.semantic_service.match(subdivision_source)
            extracted.subdivision_name = (
                subdivision_match.subdivision.full_name
                if subdivision_match.subdivision
                else subdivision_source
            )
            extracted.subdivision_similarity = subdivision_match.similarity
        else:
            extracted.subdivision_name = None
            extracted.subdivision_similarity = None

        candidates = self.portal_repo.fetch_candidates(extracted.timestamp, window)
        result = self.compare_service.compare(
            extracted,
            candidates,
            threshold,
            window,
            offenders_min_overlap=offenders_min_overlap,
        )
        event_type_result = self._match_event_type(
            extracted.raw_text, candidates, result.get("primary_match_id"), event_type_threshold
        )
        result["event_type"] = event_type_result
        if result["duplicates_count"] > 1:
            result["message"] = f"Найдено несколько записей: {result['duplicates_count']}"
        return result

    def _settings(self) -> dict[str, float]:
        from apps.core.models import Setting

        defaults = {
            "semantic_threshold_subdivision": 0.78,
            "time_window_minutes": 10,
            "offenders_match_min_overlap": 0.5,
        }
        values = defaults.copy()
        for key, default in defaults.items():
            try:
                values[key] = float(Setting.objects.get(key=key).value)
            except Setting.DoesNotExist:
                values[key] = default
        return values

    def _match_event_type(
        self,
        text: str,
        candidates: list,
        primary_match_id: str | None,
        threshold: float,
    ) -> dict:
        match = self.event_type_service.match(text or "")
        detected = None
        detected_score = None
        if match.event_type and match.similarity >= threshold:
            detected = match.event_type.name
            detected_score = round(match.similarity, 4)

        stored = None
        if primary_match_id:
            stored = next(
                (
                    candidate.event_type_name
                    for candidate in candidates
                    if candidate.event_id == primary_match_id
                ),
                None,
            )

        if detected and stored:
            if detected == stored:
                message = "Совпадает с записью в БД"
                status = "match"
            else:
                message = "Несовпадение: в БД указан другой тип события"
                status = "mismatch"
        elif detected and not stored:
            message = "В БД не задан, определен автоматически"
            status = "detected_only"
        elif stored and not detected:
            message = "В БД задан, но не подтверждён автоматически"
            status = "stored_only"
        else:
            message = "Не удалось идентифицировать"
            status = "none"

        return {
            "detected": detected,
            "detected_score": detected_score,
            "stored": stored,
            "status": status,
            "message": message,
        }
