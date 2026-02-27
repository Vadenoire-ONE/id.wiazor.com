# ══════════════════════════════════════════════════════════════════════════
# Identity Backend — Multi-stage Dockerfile (P0: non-root user)
# ══════════════════════════════════════════════════════════════════════════
# Build context: . (standalone repo root)
# Source code: src/identity/
# Entrypoint: python -m identity.main
# Port: 8200

# ── Stage 1: Builder ─────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

# System deps for building native extensions (asyncpg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 2: Production ─────────────────────────────────────────────────
FROM python:3.13-slim

# Runtime deps only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 && \
    rm -rf /var/lib/apt/lists/*

# P0 SECURITY: Non-root user
RUN groupadd -r identity && useradd -r -g identity -d /app -s /sbin/nologin identity

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy Identity application source ONLY
COPY src/identity/ /app/src/identity/

# Ensure proper ownership
RUN chown -R identity:identity /app

# Python path so identity package is importable
ENV PYTHONPATH=/app/src

# Switch to non-root user
USER identity

EXPOSE 8200

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8200/api/v1/health')" || exit 1

# Exec-form ENTRYPOINT (PID 1 = python, not shell)
ENTRYPOINT ["python", "-m", "identity.main"]
