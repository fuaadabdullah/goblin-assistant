# syntax=docker/dockerfile:1.7-labs

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ---- Install uv for fast, reproducible installs ----
FROM base AS uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

FROM uv AS deps

COPY apps/api/pyproject.toml /app/apps/api/pyproject.toml
COPY apps/api/uv.lock /app/apps/api/uv.lock

# Install only runtime dependencies from the lockfile (no dev extras).
# uv sync creates a project .venv with exact locked versions + hashes.
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    cd /app/apps/api && uv sync --frozen --no-dev --no-install-project

FROM uv AS runtime

# Keep runtime image lean: only install minimal shared libs needed by compiled wheels.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      libstdc++6 \
      libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the synced venv from the deps stage
COPY --from=deps /app/apps/api/.venv /app/apps/api/.venv
RUN groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/apps/api /app/config /app/packages /app/logs /app/chroma_db /app/state \
    && chown -R appuser:appuser /app

COPY --chown=appuser:appuser apps/api/src /app/apps/api/src
COPY --chown=appuser:appuser apps/api/alembic /app/apps/api/alembic
COPY --chown=appuser:appuser apps/api/alembic.ini /app/apps/api/alembic.ini
COPY --chown=appuser:appuser apps/api/pyproject.toml /app/apps/api/pyproject.toml
COPY --chown=appuser:appuser config /app/config
COPY --chown=appuser:appuser packages/shared /app/packages/shared

ENV PYTHONPATH=/app/apps/api/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/apps/api/.venv/bin:$PATH"
ENV PORT=8080
EXPOSE 8080

# Keep compatibility with current runtime assumptions.
RUN if [ -d /app/apps/api/src/api ] && [ ! -f /app/apps/api/src/api/__init__.py ]; then touch /app/apps/api/src/api/__init__.py; fi || true

USER appuser

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]