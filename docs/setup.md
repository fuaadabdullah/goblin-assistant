# Setup & Configuration

This guide covers installation, configuration, and environment setup for GoblinOS Assistant.

## Quick Start

### Prerequisites

- Python 3.11+
- pip (Python package manager)

### Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/fuaadabdullah/forgemono.git
   cd forgemono/apps/goblin-assistant
   ```

2. **Install dependencies**:

   ```bash
   pip install fastapi uvicorn httpx pytest
   ```

3. **Configure environment**:

   **Option A: Bitwarden Vault (Recommended)**

   ```bash
   # Install Bitwarden CLI
   npm install -g @bitwarden/cli

   # Login and setup vault (one-time)
   bw login YOUR_EMAIL
   export BW_SESSION=$(bw unlock --raw)

   # Load development secrets
   source scripts/load_env.sh

   # Verify secrets loaded
   echo $FASTAPI_SECRET
   ```

   See [Bitwarden Vault Setup](./BITWARDEN_VAULT_SETUP.md) for complete vault configuration.

   **Option B: Manual .env (Development Only)**

   ```bash
   cp backend/.env.example backend/.env.local
   # Edit .env.local with your actual values
   ```

4. **Run the server**:

   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

5. **Verify installation**:

   ```bash
   curl http://localhost:8000/health
   ```

## API Documentation

### Core Endpoints

### Health & Monitoring Endpoints

The assistant provides comprehensive health monitoring and system status endpoints.

#### Basic Health Check

```http
GET /health
```

Response:

```json
{
  "status": "healthy"
}
```

#### Comprehensive Health Check

```http
GET /v1/health/
```

Returns detailed system health including database connectivity, service availability, and performance metrics.

#### All Services Health

```http
GET /v1/health/all
```

Returns health status for all system components and dependencies.

#### Component-Specific Health Checks

- `GET /v1/health/chroma/status` - Vector database health
- `GET /v1/health/mcp/status` - MCP (Model Context Protocol) service health
- `GET /v1/health/raptor/status` - Raptor monitoring system health
- `GET /v1/health/sandbox/status` - Sandbox environment health
- `GET /v1/health/scheduler/status` - Background task scheduler health

#### Cost Tracking

```http
GET /v1/health/cost-tracking
```

Returns API usage costs and budget tracking information.

#### Latency History

```http
GET /v1/health/latency-history/{service}
```

Returns historical latency data for specified services.

#### Service Error Analysis

```http
GET /v1/health/service-errors/{service}
```

Returns error analysis and failure patterns for specified services.

#### Service Retesting

```http
POST /v1/health/retest/{service}
```

Triggers retesting of a specific service and returns updated health status.

## Configuration

### Environment Variables

The application uses environment variables for configuration. Create the appropriate `.env` files in the respective directories.

#### Frontend Environment Variables (`.env.local` in project root)

**Required:**

- `VITE_API_BASE_URL` - Base URL for the API (e.g., `https://goblin-assistant-backend.onrender.com`)

**Optional:**

- `VITE_BACKEND_URL` - Backend API URL (default: `http://localhost:8000`)
- `VITE_FASTAPI_URL` - FastAPI backend URL (default: `http://localhost:8001`)
- `VITE_ENABLE_DEBUG` - Enable debug mode (`true`/`false`, default: `false`)
- `VITE_MOCK_API` - Use mock API for development (`true`/`false`, default: `false`)

**Feature Flags:**

- `VITE_FEATURE_RAG_ENABLED` - Enable RAG functionality (`true`/`false`, default: `false`)
- `VITE_FEATURE_MULTI_PROVIDER` - Enable multi-provider routing (`true`/`false`, default: `false`)
- `VITE_FEATURE_PASSKEY_AUTH` - Enable passkey authentication (`true`/`false`, default: `false`)
- `VITE_FEATURE_GOOGLE_AUTH` - Enable Google OAuth (`true`/`false`, default: `false`)
- `VITE_FEATURE_ORCHESTRATION` - Enable task orchestration (`true`/`false`, default: `false`)
- `VITE_FEATURE_SANDBOX` - Enable sandbox mode (`true`/`false`, default: `false`)
- `VITE_ENABLE_ANALYTICS` - Enable analytics tracking (`true`/`false`, default: `false`)
- `VITE_DEBUG_MODE` - Enable debug features (`true`/`false`, default: `false`)

**Turnstile (Bot Protection):**

- `VITE_TURNSTILE_SITE_KEY_CHAT` - Turnstile site key for chat forms
- `VITE_TURNSTILE_SITE_KEY_LOGIN` - Turnstile site key for login forms
- `VITE_TURNSTILE_SITE_KEY_SEARCH` - Turnstile site key for search forms

**Monitoring:**

- `VITE_SENTRY_DSN` - Sentry DSN for error tracking and performance monitoring

#### Backend Environment Variables (`.env` in `backend/` directory)

**Required:**

- `DATABASE_URL` - Database connection string (e.g., `postgresql://user:pass@localhost/db` or `sqlite:///./goblin_assistant.db`)
- `JWT_SECRET_KEY` - Secret key for JWT token signing (use strong random string)
- `ROUTING_ENCRYPTION_KEY` - Encryption key for API key storage (32-byte base64)
- `SETTINGS_ENCRYPTION_KEY` - Encryption key for settings storage (32-byte base64)

**AI Provider API Keys (at least one required):**

- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `DEEPSEEK_API_KEY` - DeepSeek API key
- `GEMINI_API_KEY` - Google Gemini API key
- `GROK_API_KEY` - Grok API key

**Optional:**

- `ENVIRONMENT` - Environment type (`development`/`staging`/`production`, default: `development`)
- `INSTANCE_COUNT` - Number of application instances (default: `1`)
- `LOG_LEVEL` - Logging level (`DEBUG`/`INFO`/`WARNING`/`ERROR`, default: `INFO`)
- `PORT` - Server port (default: `8001`)

**Redis Configuration (for production/scaling):**

- `REDIS_URL` - Redis connection URL (e.g., `redis://localhost:6379`)
- `USE_REDIS_CHALLENGES` - Use Redis for challenge storage (`true`/`false`, default: `false`)
- `REDIS_HOST` - Redis host (default: `localhost`)
- `REDIS_PORT` - Redis port (default: `6379`)
- `REDIS_DB` - Redis database number (default: `0`)
- `REDIS_PASSWORD` - Redis password
- `REDIS_SSL` - Use SSL for Redis connection (`true`/`false`, default: `false`)
- `REDIS_TIMEOUT` - Redis connection timeout in seconds (default: `5`)

**Authentication:**

- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `FRONTEND_URL` - Frontend URL for CORS (default: `http://localhost:5173`)
- `DEBUG_AUTH` - Enable debug authentication (`true`/`false`, default: `false`)

**Raptor Integration (for quick debug tasks):**

- `RAPTOR_URL` - Raptor API endpoint URL
- `RAPTOR_API_KEY` - Raptor API key

**Monitoring & Analytics:**

- `SENTRY_DSN` - Sentry DSN for error tracking and performance monitoring
- `POSTHOG_API_KEY` - PostHog API key for user analytics (optional)
- `POSTHOG_HOST` - PostHog host URL (optional, defaults to PostHog Cloud)

**Email Validation:**

- `REQUIRE_EMAIL_VALIDATION` - Require email validation (`true`/`false`, default: `true`)
- `ALLOW_DISPOSABLE_EMAILS` - Allow disposable email addresses (`true`/`false`, default: `false`)

**Development Fallbacks:**

- `ALLOW_MEMORY_FALLBACK` - Allow memory fallback when Redis unavailable (`true`/`false`, default: `true`)

#### Example `.env.local` (Frontend)

```bash
VITE_API_BASE_URL=https://goblin-assistant-backend.onrender.com
VITE_ENABLE_DEBUG=false
VITE_MOCK_API=false
VITE_FEATURE_RAG_ENABLED=true
VITE_FEATURE_MULTI_PROVIDER=true
VITE_FEATURE_PASSKEY_AUTH=true
VITE_TURNSTILE_SITE_KEY_CHAT=0x4AAAAAACEUKA3R8flZ2Ig0
VITE_TURNSTILE_SITE_KEY_LOGIN=0x4AAAAAACEUKak3TnCntrFv
VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

#### Example `.env` (Backend)

```bash
ENVIRONMENT=development
DATABASE_URL=sqlite:///./goblin_assistant.db
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
ROUTING_ENCRYPTION_KEY=R-gey0ZNSPehux88bohbsUm9My8LAd09L2CbC_MRNo4=
SETTINGS_ENCRYPTION_KEY=R-gey0ZNSPehux88bohbsUm9My8LAd09L2CbC_MRNo4=
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
LOG_LEVEL=INFO
PORT=8001
```

### Security Notes

- Never commit `.env.local` files to version control
- Use strong, unique API keys for each service
- **Recommended**: Use Bitwarden vault for secrets management (see [Bitwarden Vault Setup](./BITWARDEN_VAULT_SETUP.md))
- Consider using a secrets management service in production
- Rotate API keys regularly
- Data & Privacy: Sanitize user content before sending to external LLM providers, storing in logs, or adding to a Vector DB. Avoid persisting PII in logs/embeddings, use TTLs for context (e.g., 1h in KV), audit logs and telemetry must not contain user secrets or PII. See `backend/docs/MONITORING_IMPLEMENTATION.md` and `backend/docs/PRODUCTION_MONITORING.md` for retention and monitoring best practices.

### Production Hardening & Checklist

The following items are recommended before deploying to production. The app is usable in development without them, but production deployments should follow these steps to ensure security and reliability.

- Use a managed secrets store (Vault, AWS Secrets Manager, Azure KeyVault) for provider API keys instead of file-based storage (e.g., `backend/api_keys.json`). If you store API keys in your database, make sure they're encrypted (see `backend/services/encryption.py`) and access-controlled.
- Enable `USE_REDIS_CHALLENGES=true` and configure Redis for passkey challenge storage (recommended in `backend/PRODUCTION_DEPLOYMENT_GUIDE.md`).
- Use Redis (or similar) for rate limiting and task queues (RQ). The in-memory rate limiter is intended for local development and won't scale across instances.
- Ensure `ROUTING_ENCRYPTION_KEY` is configured and protected — it's used for decrypting provider API keys stored in DB.
- Run `ProviderProbeWorker` (or enable routing probe worker) in a background worker to continuously monitor provider health and gather metrics.
- Disable any debug endpoints or routes (e.g., local-llm-proxy admin endpoints) in production and ensure proper API key validation for local proxies.
- Configure Sentry error tracking and set up alerts on error rates and performance issues.
- Set up a log aggregation pipeline (CloudWatch/ELK) and ensure logs do not capture raw secret values. Configure structured logging (`X-Correlation-ID`) for traceability.
- Use a distributed session/store for `task_queue` (Redis) and ensure backups for persistent data (Postgres or backups of SQLite if used temporarily).
- Implement a secrets rotation policy and an automated process for rotating encryption keys and API keys.

### Frontend Security Checklist

- ✅ **Environment Validation**: CI/CD validates that no sensitive environment variables are exposed via `VITE_` prefixes
- ✅ **Authentication Security**: HttpOnly, Secure cookies used for session tokens instead of localStorage
- ✅ **Bot Protection**: Cloudflare Turnstile integration with runtime key validation
- ✅ **XSS Prevention**: Replaced dangerous `innerHTML` with safe React error boundaries
- ✅ **Pre-commit Hooks**: Automatic security validation on every commit
- Ensure no secrets are exposed via `VITE_` variables (client `VITE_` envs are public). Move secrets to the backend / secrets manager.
- Use HttpOnly, Secure cookies for session/JWT tokens instead of localStorage to reduce XSS risks.
- Authenticate streaming endpoints using cookies or short-lived signed stream tokens; do not put secrets into URL query strings.
- Add a CSP and sanitize any HTML rendered from model output to prevent XSS.
- Configure CORS to allow only the specific production frontend domains (do not use `*` in production).
