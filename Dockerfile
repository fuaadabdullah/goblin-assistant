# syntax=docker/dockerfile:1.7-labs

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

FROM base AS deps

COPY apps/api/requirements.txt /app/apps/api/requirements.txt
COPY apps/api/requirements-vector.txt /app/apps/api/requirements-vector.txt

# Install build-time dependencies and Python packages with BuildKit caches for faster rebuilds.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      build-essential \
      gcc \
      git \
    && python -m pip install --upgrade pip \
    && python -m pip install -r /app/apps/api/requirements.txt -r /app/apps/api/requirements-vector.txt

FROM base AS runtime

# Keep runtime image lean: only install minimal shared libs needed by compiled wheels.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      libstdc++6 \
      libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=deps /usr/local /usr/local
COPY . /app

ENV PYTHONPATH=/app/apps/api/src
ENV PORT=8080
EXPOSE 8080

# Keep compatibility with current runtime assumptions.
RUN if [ -d /app/apps/api/src/api ] && [ ! -f /app/apps/api/src/api/__init__.py ]; then touch /app/apps/api/src/api/__init__.py; fi || true

CMD ["sh", "-c", "ddtrace-run uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
