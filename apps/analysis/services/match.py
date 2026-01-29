from __future__ import annotations

from apps.analysis.dto import ExtractedEvent
from apps.analysis.services.compare import CompareService
from apps.analysis.services.portal_repo import PortalRepository
from apps.analysis.services.semantic import SubdivisionSemanticService


class MatchService:
    def __init__(
        self, semantic_service: SubdivisionSemanticService, portal_repo: PortalRepository
    ) -> None:
        self.semantic_service = semantic_service
        self.portal_repo = portal_repo
        self.compare_service = CompareService()

    def match_event(self, extracted: ExtractedEvent) -> dict:
        settings_values = self._settings()
        threshold = settings_values["semantic_threshold_subdivision"]
        window = settings_values["time_window_minutes"]
        if extracted.subdivision_text:
            subdivision_match = self.semantic_service.match(extracted.subdivision_text)
            extracted.subdivision_name = (
                subdivision_match.subdivision.full_name
                if subdivision_match.subdivision
                else extracted.subdivision_text
            )
            extracted.subdivision_similarity = subdivision_match.similarity
        else:
            extracted.subdivision_name = None
            extracted.subdivision_similarity = None

        candidates = self.portal_repo.fetch_candidates(extracted.timestamp, window)
        result = self.compare_service.compare(extracted, candidates, threshold, window)
        if result["duplicates_count"] > 1:
            result["message"] = f"Найдено несколько записей: {result['duplicates_count']}"
        return result

    def _settings(self) -> dict[str, float]:
        from apps.core.models import Setting

        defaults = {"semantic_threshold_subdivision": 0.8, "time_window_minutes": 30}
        values = defaults.copy()
        for key, default in defaults.items():
            try:
                values[key] = float(Setting.objects.get(key=key).value)
            except Setting.DoesNotExist:
                values[key] = default
        return values
