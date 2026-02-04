from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ModelLockEntry:
    repo_id: str
    revision: str
    cache_dir: str


def load_lock(lock_file: Path) -> dict:
    if not lock_file.exists():
        return {"models": []}
    with lock_file.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_lock(lock_file: Path, data: dict) -> None:
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    data["generated_at"] = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    with lock_file.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def get_lock_entry(data: dict, repo_id: str) -> ModelLockEntry | None:
    for entry in data.get("models", []):
        if entry.get("repo_id") == repo_id:
            revision = entry.get("revision")
            cache_dir = entry.get("cache_dir", "models/hf")
            if revision:
                return ModelLockEntry(repo_id=repo_id, revision=revision, cache_dir=cache_dir)
    return None


def update_lock(data: dict, repo_id: str, revision: str, cache_dir: str) -> dict:
    models = [m for m in data.get("models", []) if m.get("repo_id") != repo_id]
    models.append(
        {
            "repo_id": repo_id,
            "revision": revision,
            "cache_dir": cache_dir,
        }
    )
    data["models"] = sorted(models, key=lambda item: item.get("repo_id", ""))
    return data


def snapshot_dir(cache_dir: Path, repo_id: str) -> Path:
    return cache_dir / f"models--{repo_id.replace('/', '--')}" / "snapshots"


def resolve_snapshot_path(
    cache_dir: Path, repo_id: str, revision: str | None = None
) -> Path | None:
    snapshots_root = snapshot_dir(cache_dir, repo_id)
    if not snapshots_root.exists():
        return None
    if revision:
        candidate = snapshots_root / revision
        if (candidate / "modules.json").exists():
            return candidate
        return None
    for entry in sorted(snapshots_root.iterdir()):
        if entry.is_dir() and (entry / "modules.json").exists():
            return entry
    return None


def ensure_cache_local(cache_dir: Path, repo_id: str, lock_file: Path) -> Path:
    lock_data = load_lock(lock_file)
    entry = get_lock_entry(lock_data, repo_id)
    revision = entry.revision if entry else None
    snapshot = resolve_snapshot_path(cache_dir, repo_id, revision)
    if snapshot is None:
        snapshot = resolve_snapshot_path(cache_dir, repo_id)
    if snapshot is None:
        raise ValueError(
            "Local model cache not found. "
            "Expected modules.json under models/hf/models--<repo>/snapshots/<rev>."
        )
    return snapshot


def ensure_cache_download(
    cache_dir: Path,
    repo_id: str,
    lock_file: Path,
    refresh: bool,
) -> Path:
    lock_data = load_lock(lock_file)
    entry = get_lock_entry(lock_data, repo_id)
    revision = entry.revision if entry else None

    if not revision or refresh:
        from huggingface_hub import HfApi

        info = HfApi().model_info(repo_id, revision="main")
        revision = info.sha
        lock_data = update_lock(lock_data, repo_id, revision, "models/hf")
        write_lock(lock_file, lock_data)

    from huggingface_hub import snapshot_download

    cache_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repo_id,
        revision=revision,
        cache_dir=str(cache_dir),
        local_dir_use_symlinks=False,
    )

    snapshot = resolve_snapshot_path(cache_dir, repo_id, revision)
    if snapshot is None:
        raise ValueError("Downloaded cache missing modules.json.")
    return snapshot


def run() -> int:
    repo_id = os.environ.get(
        "MODEL_NAME",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    cache_dir = Path(os.environ.get("CACHE_DIR", "models/hf")).resolve()
    lock_file = Path(os.environ.get("LOCK_FILE", "models/model_lock.json")).resolve()
    mode = os.environ.get("MODEL_CACHE_MODE", "download").strip().lower()
    refresh = os.environ.get("REFRESH") == "1"

    if mode == "local":
        snapshot = ensure_cache_local(cache_dir, repo_id, lock_file)
        print(f"Model cache ready (local): {snapshot}")
        return 0
    if mode == "download":
        snapshot = ensure_cache_download(cache_dir, repo_id, lock_file, refresh)
        print(f"Model cache ready (download): {snapshot}")
        return 0

    raise SystemExit(f"Unknown MODEL_CACHE_MODE: {mode}")


if __name__ == "__main__":
    raise SystemExit(run())
