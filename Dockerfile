FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

ARG SEMANTIC_MODEL_NAME=intfloat/multilingual-e5-large

RUN mkdir -p /models/hf && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${SEMANTIC_MODEL_NAME}', cache_folder='/models/hf')"

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/models/hf \
    TRANSFORMERS_CACHE=/models/hf \
    SENTENCE_TRANSFORMERS_HOME=/models/hf \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    SEMANTIC_MODEL_LOCAL_ONLY=true \
    SEMANTIC_MODEL_CACHE_DIR=/models/hf

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
