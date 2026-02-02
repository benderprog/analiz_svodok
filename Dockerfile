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

RUN mkdir -p /models/hf && \
    if [ "$PREWARM" = "true" ]; then \
      HF_HOME=/models/hf TRANSFORMERS_CACHE=/models/hf SENTENCE_TRANSFORMERS_HOME=/models/hf \
      python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${SEMANTIC_MODEL_NAME:-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2}')"; \
    else \
      echo "Skipping semantic model prewarm (PREWARM=$PREWARM)"; \
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
