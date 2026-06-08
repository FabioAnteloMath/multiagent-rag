# syntax=docker/dockerfile:1.6
# ---- Stage 1: build wheels (only build-essential needed) ----
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps for compiling wheels (faiss-cpu, sentence-transformers, pypdf)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Build all wheels into /wheels
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ---- Stage 2: runtime (slim, no compiler, no tests) ----
FROM python:3.11-slim AS runtime

# Don't write .pyc, flush stdout for Fly logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copy prebuilt wheels and install them (fast, no compiler in this stage)
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Copy application code
COPY app ./app
COPY run_server.py ./

# Persistent data directory (mounted as Fly volume in production)
RUN mkdir -p /data/db /data/faiss
ENV DATA_DIR=/data

# Expose the port Fly will route to
EXPOSE 8011

# Run as non-root for safety
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app /data
USER appuser

# Healthcheck: hit /api/info
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request, sys; \
        sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8011/api/info', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011", "--workers", "1", "--log-level", "info"]
