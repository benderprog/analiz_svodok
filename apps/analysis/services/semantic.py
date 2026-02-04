from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import re
import string

from sentence_transformers import SentenceTransformer, util

from apps.reference.models import SubdivisionRef

logger = logging.getLogger(__name__)


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_model_path(
    model_name: str, cache_dir: str | None, lock_file: str | None
) -> str | None:
    if not cache_dir or not lock_file:
        return None
    lock_path = Path(lock_file)
    if not lock_path.exists():
        return None
    try:
        data = lock_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        lock = json.loads(data)
    except ValueError:
        return None
    revision = None
    for entry in lock.get("models", []):
        if entry.get("repo_id") == model_name:
            revision = entry.get("revision")
            break
    snapshots_root = (
        Path(cache_dir)
        / f"models--{model_name.replace('/', '--')}"
        / "snapshots"
    )
    if revision:
        candidate = snapshots_root / revision
        if (candidate / "modules.json").exists():
            return str(candidate)
    if snapshots_root.exists():
        for entry in sorted(snapshots_root.iterdir()):
            if entry.is_dir() and (entry / "modules.json").exists():
                return str(entry)
    return None


@dataclass
class SemanticMatch:
    subdivision: SubdivisionRef | None
    similarity: float


def normalize_subdivision(value: str | None) -> str:
    if not value:
        return ""
    cleaned = value.lower().replace("ё", "е")
    cleaned = cleaned.replace("№", " ")
    cleaned = re.sub(r"[‐‑‒–—―−]", "-", cleaned)
    cleaned = re.sub(r"[\"'«»()\\[\\]{}]", " ", cleaned)
    cleaned = re.sub(r"[.,;:/]", " ", cleaned)
    cleaned = re.sub(
        r"\bотделени[ея]\s+пограничного\s+контроля\b",
        "оп",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\bопк\b", "оп", cleaned)
    cleaned = re.sub(r"\bпограничная\s+застава\b", "пз", cleaned)
    cleaned = cleaned.replace("-", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


class SubdivisionSemanticService:
    _cached_subdivisions: list[SubdivisionRef] | None = None
    _cached_embeddings: object | None = None
    _cached_embedding_entries: list[SubdivisionRef] | None = None
    _cached_embedding_texts: list[str] | None = None
    _cached_normalized_entries: list[tuple[str, SubdivisionRef]] | None = None

    def __init__(self, model_name: str) -> None:
        cache_dir = os.environ.get("SEMANTIC_MODEL_CACHE_DIR")
        local_only = _is_truthy(os.environ.get("SEMANTIC_MODEL_LOCAL_ONLY"))
        explicit_path = os.environ.get("SEMANTIC_MODEL_PATH")
        lock_file = os.environ.get(
            "SEMANTIC_MODEL_LOCK_FILE", "models/model_lock.json"
        )
        if explicit_path and Path(explicit_path).exists():
            model_name = explicit_path
        elif local_only:
            resolved = _resolve_model_path(model_name, cache_dir, lock_file)
            if resolved:
                model_name = resolved
        init_kwargs: dict[str, object] = {}
        if cache_dir:
            init_kwargs["cache_folder"] = cache_dir
        if local_only:
            init_kwargs["local_files_only"] = True
        try:
            self.model = SentenceTransformer(model_name, **init_kwargs)
        except OSError as exc:
            if local_only:
                message = (
                    f"Semantic model '{model_name}' is not downloaded locally. "
                    "Disable SEMANTIC_MODEL_LOCAL_ONLY or pre-download the model."
                )
                logger.error(message)
                raise ValueError(message) from exc
            raise
        if self.__class__._cached_subdivisions is None:
            self.__class__._cached_subdivisions = list(SubdivisionRef.objects.all())

        cached_subdivisions = self.__class__._cached_subdivisions

        if (
            self.__class__._cached_embeddings is None
            or self.__class__._cached_embedding_entries is None
            or self.__class__._cached_embedding_texts is None
        ):
            texts: list[str] = []
            entries: list[SubdivisionRef] = []
            for subdivision in cached_subdivisions:
                if subdivision.short_name:
                    texts.append(subdivision.short_name)
                    entries.append(subdivision)
                if subdivision.full_name:
                    texts.append(subdivision.full_name)
                    entries.append(subdivision)
            if texts:
                self.__class__._cached_embeddings = self.model.encode(texts)
                self.__class__._cached_embedding_entries = entries
                self.__class__._cached_embedding_texts = texts
            else:
                self.__class__._cached_embeddings = []
                self.__class__._cached_embedding_entries = []
                self.__class__._cached_embedding_texts = []

        normalized_entries_cached = self.__class__._cached_normalized_entries
        needs_normalized_refresh = normalized_entries_cached is None
        if (
            not needs_normalized_refresh
            and cached_subdivisions
            and normalized_entries_cached is not None
        ):
            needs_normalized_refresh = not all(
                subdivision in cached_subdivisions
                for _, subdivision in normalized_entries_cached
            )

        if needs_normalized_refresh:
            normalized_entries: list[tuple[str, SubdivisionRef]] = []
            for subdivision in cached_subdivisions:
                candidates = [subdivision.short_name, subdivision.full_name]
                candidates.extend(self._generate_aliases(subdivision.full_name))
                for candidate in candidates:
                    normalized = self._normalize(candidate)
                    if normalized:
                        normalized_entries.append((normalized, subdivision))
            self.__class__._cached_normalized_entries = normalized_entries

    @staticmethod
    def _pre_normalize(value: str) -> str:
        lowered = value.lower().replace("ё", "е")
        lowered = re.sub(r"[‐‑‒–—―−]", "-", lowered)
        cleaned = re.sub(r"[\"'«»()\\[\\]{}]", "", lowered)
        cleaned = cleaned.replace(".", "")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    @classmethod
    def _normalize(cls, value: str | None) -> str:
        if not value:
            return ""
        cleaned = cls._pre_normalize(value)
        cleaned = cleaned.replace(" ", "")
        cleaned = cleaned.replace("-", "")
        punctuation = string.punctuation.replace("-", "")
        cleaned = cleaned.translate(str.maketrans("", "", punctuation))
        cleaned = re.sub(r"[^\w-]", "", cleaned)
        return cleaned.strip("-")

    @classmethod
    def _generate_aliases(cls, full_name: str | None) -> list[str]:
        if not full_name:
            return []
        normalized = cls._pre_normalize(full_name)
        aliases: list[str] = []
        pz_match = re.search(
            r"пограничная\s+застава\s*№?\s*(\d+)", normalized, re.IGNORECASE
        )
        if pz_match:
            number = pz_match.group(1)
            aliases.extend(
                [
                    f"пз-{number}",
                    f"пз {number}",
                    f"пз№{number}",
                    f"пз №{number}",
                    f"пз{number}",
                    f"пз- {number}",
                    f"погран застава №{number}",
                ]
            )
        opk_match = re.search(
            r"отделение\s+пограничного\s+контроля\s+(.+)",
            normalized,
            re.IGNORECASE,
        )
        if opk_match:
            name_part = opk_match.group(1).strip()
            aliases.extend(
                [
                    f"оп-{name_part}",
                    f"оп {name_part}",
                    f"опк {name_part}",
                    f"опк «{name_part}»",
                    f"отделение пограничного контроля {name_part}",
                ]
            )
        return aliases

    def match(self, text: str) -> SemanticMatch:
        cached_subdivisions = self.__class__._cached_subdivisions
        cached_embeddings = self.__class__._cached_embeddings
        cached_entries = self.__class__._cached_embedding_entries
        cached_texts = self.__class__._cached_embedding_texts
        normalized_entries = self.__class__._cached_normalized_entries
        subdivisions = cached_subdivisions if cached_subdivisions is not None else []
        embeddings = cached_embeddings if cached_embeddings is not None else []
        entries = cached_entries if cached_entries is not None else []
        entry_texts = cached_texts if cached_texts is not None else []
        normalized_entries = normalized_entries if normalized_entries is not None else []
        if not subdivisions:
            return SemanticMatch(subdivision=None, similarity=0.0)
        normalized_text = self._normalize(text)
        normalized_for_numbers = normalize_subdivision(text)
        numbers = re.findall(r"\b\d+\b", normalized_for_numbers)
        for normalized_candidate, subdivision in normalized_entries:
            if normalized_text == normalized_candidate:
                return SemanticMatch(subdivision=subdivision, similarity=1.0)
        if len(embeddings) == 0:
            return SemanticMatch(subdivision=None, similarity=0.0)
        filtered_entries = entries
        filtered_embeddings = embeddings
        filtered_texts = entry_texts
        number_filtered = False
        if numbers and entries and entry_texts:
            filtered = [
                (entry, embedding, entry_text)
                for entry, embedding, entry_text in zip(entries, embeddings, entry_texts)
                if all(
                    number in normalize_subdivision(entry_text)
                    for number in numbers
                )
            ]
            if filtered:
                filtered_entries = [item[0] for item in filtered]
                filtered_embeddings = [item[1] for item in filtered]
                filtered_texts = [item[2] for item in filtered]
                number_filtered = True
        if number_filtered:
            logger.debug(
                "Subdivision match filtered by numbers %s (%s candidates)",
                numbers,
                len(filtered_entries),
            )
        text_embedding = self.model.encode(text)
        best_match = None
        best_score = -1.0
        for subdivision, embedding in zip(filtered_entries, filtered_embeddings):
            score = float(util.cos_sim(text_embedding, embedding))
            if score > best_score:
                best_score = score
                best_match = subdivision
        return SemanticMatch(subdivision=best_match, similarity=best_score)
