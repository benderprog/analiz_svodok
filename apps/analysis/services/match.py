from __future__ import annotations

from apps.analysis.dto import ExtractedEvent, MatchResult, PortalEvent
from apps.analysis.services.compare import (
    build_result,
    evaluate_offenders,
    evaluate_subdivision,
    evaluate_time,
    normalize_offenders,
    rule_two_of_three,
)
from apps.analysis.services.semantic import SubdivisionSemanticService


class MatchService:
    def __init__(self, semantic_service: SubdivisionSemanticService) -> None:
        self.semantic_service = semantic_service

    def match_event(self, extracted: ExtractedEvent, portal_events: list[PortalEvent]) -> MatchResult:
        settings_values = self._settings()
        threshold = settings_values["semantic_threshold_subdivision"]
        window = settings_values["time_window_minutes"]
        subdivision_match = self.semantic_service.match(extracted.subdivision or "")
        extracted_subdivision = (
            subdivision_match.subdivision.full_name if subdivision_match.subdivision else None
        )
        time_status = evaluate_time(extracted.timestamp, None, window, exact=False, allow_near=False)
        offenders_status = evaluate_offenders(extracted.offenders, [])
        subdivision_status = evaluate_subdivision(
            extracted_subdivision, None, subdivision_match.similarity, threshold
        )

        best: PortalEvent | None = None
        best_matches: list[PortalEvent] = []
        for event in portal_events:
            time_exact = extracted.timestamp and event.date_detection == extracted.timestamp
            time_match = bool(time_exact)
            subdivision_match_flag = (
                extracted_subdivision and event.subdivision_name == extracted_subdivision
            )
            offenders_match_flag = bool(
                normalize_offenders(extracted.offenders)
                == normalize_offenders(event.offenders)
            )
            if rule_two_of_three(time_match, subdivision_match_flag, offenders_match_flag):
                best_matches.append(event)
                if best is None:
                    best = event
        if best:
            subdivision_match_flag = (
                extracted_subdivision and best.subdivision_name == extracted_subdivision
            )
            offenders_match_flag = bool(
                normalize_offenders(extracted.offenders)
                == normalize_offenders(best.offenders)
            )
            allow_near_time = subdivision_match_flag and offenders_match_flag
            time_status = evaluate_time(
                extracted.timestamp,
                best.date_detection,
                window,
                exact=bool(extracted.timestamp and best.date_detection == extracted.timestamp),
                allow_near=allow_near_time,
            )
            offenders_status = evaluate_offenders(extracted.offenders, best.offenders)
            subdivision_status = evaluate_subdivision(
                extracted_subdivision,
                best.subdivision_name,
                subdivision_match.similarity,
                threshold,
            )
        found = best is not None
        result = build_result(extracted, best, time_status, subdivision_status, offenders_status, found)
        if len(best_matches) > 1:
            result.message = f"Найдено несколько записей: {len(best_matches)}"
            result.matches = best_matches
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
