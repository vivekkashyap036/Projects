# One image, two processes: the API (default CMD) and the Streamlit UI (override the command).
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FASTEMBED_CACHE_PATH=/opt/models

WORKDIR /app

# Install dependencies first: this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the embedding model into the image so pods don't download it at start-up
# (best-effort: skipped if the build machine has no internet).
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')" || echo "model download skipped"

COPY app ./app
COPY ui ./ui
COPY eval ./eval
COPY data ./data

# Run as a non-root user (also required by many Kubernetes security policies).
RUN useradd --uid 10001 --create-home appuser && mkdir -p /app/storage && chown -R appuser /app /opt/models
USER 10001

EXPOSE 8000 8501
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
