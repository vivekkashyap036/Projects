FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config ./config
COPY src ./src
COPY ui ./ui
COPY docs ./docs

# Build the synthetic data, model and reports at image build time (seeded, deterministic).
RUN mkdir -p data artifacts reports \
 && python -m vendorscore.data.synth \
 && python -m vendorscore.model \
 && python -m vendorscore.evaluate \
 && python -m vendorscore.agents.early_warning \
 && python -m vendorscore.agents.shadow

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
# Set AUDIT_SALT (and optionally ANTHROPIC_API_KEY) at run time, never in the image.
CMD ["python", "-m", "uvicorn", "vendorscore.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
