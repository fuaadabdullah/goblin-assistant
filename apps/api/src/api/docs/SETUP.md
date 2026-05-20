# Setup & Configuration Guide

This guide covers installation, configuration, and environment setup for the Goblin Assistant Backend API.

## Prerequisites

### System Requirements

- **Python**: 3.11 or higher
- **pip**: Python package manager
- **Redis**: Optional, for production caching and sessions
- **Git**: For cloning the repository

### Platform-Specific Installation

#### macOS

```bash
# Install Python 3.11+
brew install python@3.11

# Install Redis (optional)
brew install redis
brew services start redis
```

#### Ubuntu/Debian

```bash
# Install Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv

# Install Redis (optional)
sudo apt install redis-server
sudo systemctl start redis-server
```

#### Windows

```bash
# Download Python 3.11+ from python.org
# Install Redis from redis.io or use WSL
```

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/fuaadabdullah/forgemono.git
cd forgemono/apps/goblin-assistant/api
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### 4. Environment Configuration

#### Development Setup

Create a `.env` file in the `api/` directory:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Core Configuration
ENVIRONMENT=development
DATABASE_URL=sqlite:///./goblin_assistant.db
LOG_LEVEL=INFO
PORT=8000

# AI Provider API Keys (at least one required)
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key
DEEPSEEK_API_KEY=your-deepseek-key

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key
ROUTING_ENCRYPTION_KEY=your-32-byte-encryption-key
SETTINGS_ENCRYPTION_KEY=your-32-byte-encryption-key

# Redis (for production caching)
REDIS_URL=redis://localhost:6379
USE_REDIS_CHALLENGES=false

# Frontend Integration
FRONTEND_URL=http://localhost:3000

# Development Features
DEBUG_AUTH=true
ALLOW_MEMORY_FALLBACK=true
```

#### Production Setup

For production, use environment variables instead of `.env` files:

```bash
# Set production environment variables
export ENVIRONMENT=production
export DATABASE_URL=postgresql://user:pass@localhost/goblin_prod
export JWT_SECRET_KEY=your-production-secret-key
export ROUTING_ENCRYPTION_KEY=your-production-encryption-key
# ... other production variables
```

### 5. Database Initialization

```bash
# Initialize database (SQLite for development)
python -c "from api.storage.database import init_db; init_db()"

# Or use the initialization script
python init_db.py
```

### 6. Verify Installation

```bash
# Run the development server
uvicorn main:app --reload

# In another terminal, test the health endpoint
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy"
}
```

## Configuration Details

### Environment Variables Reference

#### Core Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Environment type (development/staging/production) | development | No |
| `DATABASE_URL` | Database connection string | sqlite:///./goblin_assistant.db | Yes |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO | No |
| `PORT` | Server port | 8000 | No |
| `FRONTEND_URL` | Frontend URL for CORS | http://localhost:3000 | No |

#### AI Provider Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models | One required |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models | One required |
| `GEMINI_API_KEY` | Google Gemini API key | One required |
| `GROQ_API_KEY` | Groq API key for fast inference | One required |
| `DEEPSEEK_API_KEY` | DeepSeek API key | One required |

#### Security Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `JWT_SECRET_KEY` | Secret key for JWT token signing | Yes |
| `ROUTING_ENCRYPTION_KEY` | Encryption key for API key storage (32-byte base64) | Yes |
| `SETTINGS_ENCRYPTION_KEY` | Encryption key for settings storage (32-byte base64) | Yes |

#### Redis Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | redis://localhost:6379 |
| `USE_REDIS_CHALLENGES` | Use Redis for challenge storage | false |
| `REDIS_HOST` | Redis host | localhost |
| `REDIS_PORT` | Redis port | 6379 |
| `REDIS_DB` | Redis database number | 0 |
| `REDIS_PASSWORD` | Redis password | None |
| `REDIS_SSL` | Use SSL for Redis connection | false |

#### Feature Flags

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG_AUTH` | Enable debug authentication | false |
| `ALLOW_MEMORY_FALLBACK` | Allow memory fallback when Redis unavailable | true |
| `REQUIRE_EMAIL_VALIDATION` | Require email validation | true |
| `ALLOW_DISPOSABLE_EMAILS` | Allow disposable email addresses | false |

### Database Configuration

#### SQLite (Development)

```bash
DATABASE_URL=sqlite:///./goblin_assistant.db
```

#### PostgreSQL (Production)

```bash
DATABASE_URL=postgresql://username:password@localhost:5432/goblin_assistant
```

#### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Redis Configuration

#### Local Redis Setup

```bash
# Install Redis
brew install redis  # macOS
sudo apt install redis-server  # Ubuntu

# Start Redis
brew services start redis  # macOS
sudo systemctl start redis-server  # Ubuntu

# Test Redis connection
redis-cli ping
```

#### Redis Security

For production, configure Redis security:

```bash
# Set Redis password
redis-cli CONFIG SET requirepass your-redis-password

# Configure Redis bind (only localhost in production)
redis-cli CONFIG SET bind 127.0.0.1
```

### SSL/TLS Configuration

#### Development (Self-signed certificates)

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Run with HTTPS
uvicorn main:app --reload --ssl-keyfile key.pem --ssl-certfile cert.pem
```

#### Production (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Configure nginx/load balancer to handle SSL
```

## Development Setup

### IDE Configuration

#### Visual Studio Code

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm

1. Open project in PyCharm
2. Configure Python interpreter to use `./venv/bin/python`
3. Enable code inspection and formatting
4. Configure test runner to use pytest

### Development Tools

#### Code Formatting

```bash
# Install black and isort
pip install black isort

# Format code
black .
isort .

# Check formatting
black --check .
isort --check-only .
```

#### Linting

```bash
# Install pylint
pip install pylint

# Run linting
pylint api/
```

#### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=api tests/

# Run specific test
pytest tests/test_health.py -v
```

### Hot Reloading

```bash
# Development server with auto-reload
uvicorn main:app --reload --log-level debug

# Alternative using the startup script
python start_server.py
```

## Production Deployment

### Environment Hardening

#### Security Checklist

- [ ] Use strong, unique secrets for all keys
- [ ] Enable SSL/TLS in production
- [ ] Configure proper CORS origins (not `*`)
- [ ] Set up proper authentication
- [ ] Enable rate limiting
- [ ] Configure monitoring and logging
- [ ] Set up backup strategy
- [ ] Enable database connection pooling
- [ ] Configure Redis for production
- [ ] Set up health checks and alerts

#### Production Environment Variables

```bash
# Production settings
ENVIRONMENT=production
DATABASE_URL=postgresql://prod_user:secure_password@prod-db:5432/goblin_prod
REDIS_URL=redis://prod-redis:6379
FRONTEND_URL=https://your-frontend-domain.com

# Security
JWT_SECRET_KEY=super-secure-production-jwt-secret-256-bits
ROUTING_ENCRYPTION_KEY=super-secure-production-encryption-key-32-bytes
SETTINGS_ENCRYPTION_KEY=super-secure-production-settings-key-32-bytes

# Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
DATADOG_API_KEY=your-datadog-api-key

# Features
USE_REDIS_CHALLENGES=true
ALLOW_MEMORY_FALLBACK=false
DEBUG_AUTH=false
```

### Container Deployment

#### Docker Setup

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
# Build image
docker build -t goblin-assistant-api .

# Run container
docker run -p 8000:8000 --env-file .env goblin-assistant-api
```

#### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/goblin_assistant
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=goblin_assistant
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

Run with Docker Compose:

```bash
docker-compose up -d
```

### Cloud Deployment

#### AWS/GCP/Azure Deployment

Use the deployment guide in [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed cloud deployment instructions.

#### Serverless Deployment

The API can be deployed to serverless platforms like AWS Lambda, Google Cloud Functions, or Vercel Functions with appropriate configuration.

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn main:app --reload --port 8001
```

#### Database Connection Issues

```bash
# Check database file permissions
ls -la goblin_assistant.db

# Check database URL format
echo $DATABASE_URL

# Test database connection
python -c "import sqlite3; sqlite3.connect('goblin_assistant.db').execute('SELECT 1')"
```

#### Redis Connection Issues

```bash
# Test Redis connection
redis-cli ping

# Check Redis logs
redis-cli --latency-history

# Test from Python
python -c "import redis; r = redis.from_url('redis://localhost:6379'); print(r.ping())"
```

#### Import Errors

```bash
# Check Python path
echo $PYTHONPATH

# Run from correct directory
cd apps/goblin-assistant/api

# Install in development mode
pip install -e .
```

#### Environment Variable Issues

```bash
# Check if .env file exists
ls -la .env

# Load environment variables
source .env

# Debug environment variables
python -c "import os; print([k for k in os.environ if 'API' in k or 'SECRET' in k])"
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
export LOG_LEVEL=DEBUG
export PYTHONPATH=/path/to/forgemono/apps/goblin-assistant
uvicorn main:app --reload --log-level debug
```

### Health Check Endpoints

Use these endpoints to verify system health:

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/v1/health/

# All services health
curl http://localhost:8000/v1/health/all

# Component-specific health
curl http://localhost:8000/v1/health/chroma/status
```

## Next Steps

After successful setup:

1. **Read the [Architecture Guide](./ARCHITECTURE.md)** to understand system design
2. **Review [Router Documentation](./ROUTERS.md)** for API endpoint details
3. **Set up [Integrations](./INTEGRATIONS.md)** for monitoring and external services
4. **Configure [Deployment](./DEPLOYMENT.md)** for production use
5. **Check [Troubleshooting Guide](./TROUBLESHOOTING.md)** for common issues

---

**Last Updated**: December 17, 2025  
**Version**: 1.0.0
