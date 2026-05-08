# Dockerfile
FROM python:3.11-slim

# Avoid Python buffering problems and keep the runtime image leaner.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory where app will live inside the container
WORKDIR /app

# Copy requirements file for dependency installation
COPY requirements.txt /app/

# Install build deps only for the pip step, then remove them to keep the image smaller.
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  gcc \
  git \
  && pip install --upgrade pip \
  && pip install -r requirements.txt \
  && apt-get purge -y --auto-remove build-essential gcc git \
  && rm -rf /var/lib/apt/lists/* /root/.cache/pip

# Copy app source into container
COPY . /app

# Ensure backend is importable: make sure /app on PYTHONPATH and workdir is /app
ENV PYTHONPATH=/app

# Make sure api is a package (helpful if missing __init__.py)
# Note: This will create an empty __init__.py if it doesn't exist
RUN if [ -d /app/api ] && [ ! -f /app/api/__init__.py ]; then touch /app/api/__init__.py; fi || true

# Expose the app port
ENV PORT=8001
EXPOSE 8001

# Default command - will be overridden by render.yaml startCommand
# render.yaml specifies: uvicorn api.main:app --host 0.0.0.0 --port $PORT
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
