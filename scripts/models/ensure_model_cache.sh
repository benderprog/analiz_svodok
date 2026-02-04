#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

LOCK_FILE="$REPO_ROOT/models/model_revisions.json"
CACHE_DIR="$REPO_ROOT/models/hf"
DEFAULT_MODEL_NAME="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

REFRESH="0"
for arg in "$@"; do
  case "$arg" in
    --refresh)
      REFRESH="1"
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: ensure_model_cache.sh [--refresh]

Options:
  --refresh    Update model revision to the latest main commit.

Environment:
  SEMANTIC_MODEL_NAME   Hugging Face repo id (e.g. sentence-transformers/...).
  REFRESH_MODEL_LOCK    Set to 1 to refresh the lock.
USAGE
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ "${REFRESH_MODEL_LOCK:-0}" == "1" ]]; then
  REFRESH="1"
fi

MODEL_NAME="${SEMANTIC_MODEL_NAME:-}"
if [[ -z "$MODEL_NAME" && -f "$REPO_ROOT/.env.example" ]]; then
  MODEL_NAME="$(grep -E '^SEMANTIC_MODEL_NAME=' "$REPO_ROOT/.env.example" | head -n1 | cut -d= -f2-)"
fi
MODEL_NAME="${MODEL_NAME:-$DEFAULT_MODEL_NAME}"

mkdir -p "$CACHE_DIR"

docker run --rm \
  -e HF_HUB_DISABLE_TELEMETRY=1 \
  -e MODEL_NAME="$MODEL_NAME" \
  -e CACHE_DIR="/work/models/hf" \
  -e LOCK_FILE="/work/models/model_revisions.json" \
  -e REFRESH="$REFRESH" \
  -v "$REPO_ROOT:/work" \
  -w /work \
  python:3.11-slim \
  bash -c "pip install --no-cache-dir huggingface_hub >/dev/null && python - <<'PY'\nimport json\nimport os\nfrom datetime import datetime, timezone\nfrom huggingface_hub import HfApi, snapshot_download\n\nrepo_id = os.environ['MODEL_NAME']\ncache_dir = os.environ['CACHE_DIR']\nlock_file = os.environ['LOCK_FILE']\nrefresh = os.environ.get('REFRESH') == '1'\n\nrevision = None\nlock_data = None\nif os.path.exists(lock_file):\n    with open(lock_file, 'r', encoding='utf-8') as handle:\n        lock_data = json.load(handle)\n    for entry in lock_data.get('models', []):\n        if entry.get('repo_id') == repo_id:\n            revision = entry.get('revision')\n            break\n\nif not revision or refresh:\n    api = HfApi()\n    info = api.model_info(repo_id, revision='main')\n    revision = info.sha\n    lock_data = lock_data or {\"models\": []}\n    models = [m for m in lock_data.get('models', []) if m.get('repo_id') != repo_id]\n    models.append({\n        \"repo_id\": repo_id,\n        \"revision\": revision,\n        \"cache_dir\": \"models/hf\",\n    })\n    lock_data['models'] = sorted(models, key=lambda item: item.get('repo_id', ''))\n    lock_data['generated_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')\n    os.makedirs(os.path.dirname(lock_file), exist_ok=True)\n    with open(lock_file, 'w', encoding='utf-8') as handle:\n        json.dump(lock_data, handle, ensure_ascii=False, indent=2)\n\nos.makedirs(cache_dir, exist_ok=True)\n\nsnapshot_download(\n    repo_id=repo_id,\n    revision=revision,\n    cache_dir=cache_dir,\n    local_dir_use_symlinks=False,\n)\n\nexpected = os.path.join(\n    cache_dir,\n    f\"models--{repo_id.replace('/', '--')}\",\n    \"snapshots\",\n    revision,\n    \"modules.json\",\n)\n\nif not os.path.exists(expected):\n    raise SystemExit(f\"Model cache missing expected file: {expected}\")\n\nprint(f\"Model cache ready: {expected}\")\nPY"
