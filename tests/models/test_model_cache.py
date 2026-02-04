from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.models import ensure_model_cache


def test_ensure_cache_local_uses_lock_revision(tmp_path: Path) -> None:
    cache_dir = tmp_path / "models" / "hf"
    repo_id = "sentence-transformers/example-model"
    revision = "abc123"
    snapshot = (
        cache_dir
        / f"models--{repo_id.replace('/', '--')}"
        / "snapshots"
        / revision
    )
    snapshot.mkdir(parents=True)
    (snapshot / "modules.json").write_text("{}", encoding="utf-8")

    lock_file = tmp_path / "models" / "model_lock.json"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "repo_id": repo_id,
                        "revision": revision,
                        "cache_dir": "models/hf",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    resolved = ensure_model_cache.ensure_cache_local(cache_dir, repo_id, lock_file)
    assert resolved == snapshot


def test_ensure_cache_download_writes_lock(tmp_path: Path, monkeypatch) -> None:
    cache_dir = tmp_path / "models" / "hf"
    lock_file = tmp_path / "models" / "model_lock.json"
    repo_id = "sentence-transformers/example-model"
    revision = "rev-download"

    class FakeInfo:
        sha = revision

    class FakeApi:
        def model_info(self, _repo_id: str, revision: str = "main") -> FakeInfo:
            return FakeInfo()

    def fake_snapshot_download(repo_id: str, revision: str, cache_dir: str, **_kwargs) -> str:
        snapshot = (
            Path(cache_dir)
            / f"models--{repo_id.replace('/', '--')}"
            / "snapshots"
            / revision
        )
        snapshot.mkdir(parents=True, exist_ok=True)
        (snapshot / "modules.json").write_text("{}", encoding="utf-8")
        return str(snapshot)

    fake_module = type(
        "fake_hf", (), {"HfApi": FakeApi, "snapshot_download": fake_snapshot_download}
    )
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_module)

    resolved = ensure_model_cache.ensure_cache_download(
        cache_dir=cache_dir,
        repo_id=repo_id,
        lock_file=lock_file,
        refresh=True,
    )

    lock_data = json.loads(lock_file.read_text(encoding="utf-8"))
    entry = ensure_model_cache.get_lock_entry(lock_data, repo_id)
    assert entry is not None
    assert entry.revision == revision
    assert (resolved / "modules.json").exists()
