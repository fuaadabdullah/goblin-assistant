# Goblin Assistant - Multi-stage Docker Build
# Supports both development and production deployments

# ================================
# Frontend Build Stage
# ================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy package files
COPY package*.json pnpm-lock.yaml ./

# Install pnpm
RUN npm install -g pnpm

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build the frontend
RUN pnpm build

# ================================
# Backend Build Stage
# ================================
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY api/fastapi/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ================================
# Production Stage
# ================================
FROM python:3.11-slim AS production

# Install nginx and supervisor
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set up directories
WORKDIR /app
RUN mkdir -p /app/static /app/logs /var/log/supervisor

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/dist /app/static

# Copy Python backend and dependencies
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend source code
COPY api/fastapi /app/api

# Copy nginx configuration
COPY infra/nginx/goblin-assistant.conf /etc/nginx/sites-available/goblin-assistant
RUN ln -s /etc/nginx/sites-available/goblin-assistant /etc/nginx/sites-enabled/ \
    && rm /etc/nginx/sites-enabled/default

# Copy supervisor configuration
COPY <<EOF /etc/supervisor/conf.d/goblin-assistant.conf
[program:fastapi]
command=/usr/local/bin/uvicorn api.main:app --host 0.0.0.0 --port 3001 --workers 4
directory=/app
user=app
autostart=true
autorestart=true
stdout_logfile=/app/logs/fastapi.out.log
stderr_logfile=/app/logs/fastapi.err.log

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
user=root
autostart=true
autorestart=true
stdout_logfile=/app/logs/nginx.out.log
stderr_logfile=/app/logs/nginx.err.log
EOF

# Set permissions
RUN chown -R app:app /app \
    && chmod +x /app/api/*.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/api/health || exit 1

# Expose ports
EXPOSE 80 3001

# Start supervisor
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
