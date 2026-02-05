from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings

REQUIRED_QUERY_KEYS = {"find_candidates", "fetch_offenders", "fetch_subdivision"}


def _resolve_config_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return Path(settings.BASE_DIR) / path


@lru_cache(maxsize=1)
def load_portal_queries() -> dict[str, str]:
    config_path = _resolve_config_path(settings.PORTAL_QUERY_CONFIG_PATH)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Portal query config not found at {config_path}. "
            "Set PORTAL_QUERY_CONFIG_PATH to a valid YAML file."
        )

    with config_path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}

    queries = data.get("queries") or {}
    missing = REQUIRED_QUERY_KEYS - set(queries.keys())
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(
            f"Portal query config is missing required queries: {missing_list}."
        )

    return {key: str(value) for key, value in queries.items()}


def get_portal_query(name: str) -> str:
    queries = load_portal_queries()
    if name not in queries:
        raise KeyError(f"Portal query '{name}' is not defined in config.")
    return queries[name]
