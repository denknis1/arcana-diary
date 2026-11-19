# Build context: the repository root (see deploy/docker-compose.yml and .dockerignore).
FROM python:3.12-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY content/cards ./content/cards
COPY tools/cards/banned_terms.json ./tools/cards/banned_terms.json
COPY api/app ./app
COPY api/migrations ./migrations
ENV CONTENT_DIR=/srv/content/cards \
    BANNED_TERMS_PATH=/srv/tools/cards/banned_terms.json \
    MIGRATIONS_DIR=/srv/migrations \
    PYTHONDONTWRITEBYTECODE=1
RUN python -c "import zoneinfo; zoneinfo.ZoneInfo('America/Mexico_City'); zoneinfo.ZoneInfo('America/Argentina/Buenos_Aires')"
USER nobody
# One process: the IP salt and the burst counters live in memory. No access log: it would keep reading ids.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
