FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements.torch-cpu.txt /app/
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    -r requirements.torch-cpu.txt && \
    pip install --no-cache-dir -r requirements.txt

COPY . /app/

ARG SEMANTIC_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
ARG PREWARM=false
ARG MODEL_CACHE_MODE=download

COPY models/hf/ /models/hf/
RUN mkdir -p /models/hf

RUN if [ "$PREWARM" = "true" ] && [ "$MODEL_CACHE_MODE" = "download" ]; then \
      pip install --no-cache-dir huggingface_hub >/dev/null && \
      MODEL_NAME="$SEMANTIC_MODEL_NAME" \
      MODEL_CACHE_MODE="$MODEL_CACHE_MODE" \
      CACHE_DIR="/models/hf" \
      LOCK_FILE="/app/models/model_lock.json" \
      python /app/scripts/models/ensure_model_cache.py; \
    fi

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/models/hf \
    TRANSFORMERS_CACHE=/models/hf \
    SENTENCE_TRANSFORMERS_HOME=/models/hf \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    SEMANTIC_MODEL_LOCAL_ONLY=true \
    SEMANTIC_MODEL_CACHE_DIR=/models/hf

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
