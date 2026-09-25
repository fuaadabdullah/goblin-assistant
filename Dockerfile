# syntax=docker/dockerfile:1.7-labs

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

FROM base AS deps

COPY apps/api/requirements.txt /app/apps/api/requirements.txt
COPY apps/api/requirements-vector.txt /app/apps/api/requirements-vector.txt
COPY apps/api/requirements.lock.txt /app/apps/api/requirements.lock.txt

# Install build-time dependencies and Python packages with BuildKit caches for faster rebuilds.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      build-essential \
      gcc \
      git \
    && python -m pip install --upgrade pip 'setuptools>=84.0.0' \
    && python -m pip install -r /app/apps/api/requirements.lock.txt \
    && python -m pip uninstall --yes jaraco.context wheel \
    && python -m pip install 'jaraco.context>=6.1.0' 'wheel>=0.46.2' \
    && python -m pip check

FROM base AS runtime

# Keep runtime image lean: only install minimal shared libs needed by compiled wheels.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
      libstdc++6 \
      libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=deps /usr/local /usr/local
# Stable v1.102.4 predates the patched x/crypto and x/image releases. Pin the
# upstream multi-arch build by digest until the next stable Tailscale release.
COPY --from=docker.io/tailscale/tailscale:unstable@sha256:610baa0bc75f851648863d37159b7ed7cd6f296bb8c46c2cc4a1666d267db63f /usr/local/bin/tailscaled /usr/local/bin/tailscale /usr/local/bin/
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
COPY --chown=appuser:appuser --chmod=755 infra/render/start.sh /app/start.sh

ENV PYTHONPATH=/app/apps/api/src \
    PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/v1/health', timeout=4)"

# Keep compatibility with current runtime assumptions.
RUN if [ -d /app/apps/api/src/api ] && [ ! -f /app/apps/api/src/api/__init__.py ]; then touch /app/apps/api/src/api/__init__.py; fi || true

USER appuser

CMD ["/app/start.sh"]
