FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

FROM base AS deps

COPY apps/api/requirements.txt /app/apps/api/requirements.txt
COPY apps/api/requirements-vector.txt /app/apps/api/requirements-vector.txt

# Default to lean (0) so direct `docker build .` does not pull PyTorch (906 MB).
# Set INSTALL_VECTOR_DEPS=1 only when vector-store / embedding features are needed.
ARG INSTALL_VECTOR_DEPS=0

# Install build-time dependencies and Python packages with BuildKit caches for faster rebuilds.
# When INSTALL_VECTOR_DEPS=0 (lean), requirements-vector.txt is skipped entirely,
# which means torch (906 MB), transformers, sentence-transformers, and chromadb
# are NOT installed. An explicit guard below verifies torch is absent.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    if [ "$INSTALL_VECTOR_DEPS" = "1" ]; then \
        apt-get update && apt-get install -y --no-install-recommends build-essential gcc git; \
    fi \
    && python -m pip install --upgrade pip \
    && python -m pip install -r /app/apps/api/requirements.txt \
    && if [ "$INSTALL_VECTOR_DEPS" = "1" ]; then \
           python -m pip install -r /app/apps/api/requirements-vector.txt; \
       else \
           echo "Skipping requirements-vector.txt (torch 906 MB) for lean local runtime"; \
       fi \
    && if [ "$INSTALL_VECTOR_DEPS" = "0" ]; then \
           echo "Verifying torch is NOT installed in lean mode..." \
           && ! python -c "import torch" 2>/dev/null \
           && echo "  torch absent - lean mode confirmed" \
           || { echo "  torch found in lean mode - removing"; python -m pip uninstall -y torch 2>/dev/null || true; }; \
       fi \
    && if [ "$INSTALL_VECTOR_DEPS" = "1" ]; then \
           apt-get purge -y --auto-remove build-essential gcc git; \
       fi

FROM deps AS runtime

# Keep runtime image lean: only install minimal shared libs needed by compiled wheels.
# When INSTALL_VECTOR_DEPS=0, skip libgomp1 (only needed by PyTorch).
ARG INSTALL_VECTOR_DEPS=0

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    if [ "$INSTALL_VECTOR_DEPS" = "1" ]; then \
        apt-get update \
        && apt-get install -y --no-install-recommends libstdc++6 libgomp1; \
    else \
        echo "Skipping runtime apt dependencies for lean local runtime"; \
    fi

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

ENV PYTHONPATH=/app/apps/api/src
ENV PORT=8080
EXPOSE 8080

# Keep compatibility with current runtime assumptions.
RUN if [ -d /app/apps/api/src/api ] && [ ! -f /app/apps/api/src/api/__init__.py ]; then touch /app/apps/api/src/api/__init__.py; fi || true

USER appuser

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
