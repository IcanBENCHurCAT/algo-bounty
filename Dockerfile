# ═══════════════════════════════════════════════════════════════════
# AlgoBounty Gateway — Multi-stage Docker build
# Stage 1: Build deps
# Stage 2: Production image (slim)
# ═══════════════════════════════════════════════════════════════════

# ── Stage 1: Build dependencies ──────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libpq-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Production ──────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Minimal runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source and assets
COPY gateway/ ./gateway/
COPY escrow.py ./escrow.py
COPY artifacts/ ./artifacts/
COPY gateway/alembic.ini ./gateway/alembic.ini
COPY gateway/migrations/ ./gateway/migrations/

EXPOSE 8080

CMD ["gunicorn", \
     "gateway.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8080", \
     "--timeout", "120"]
