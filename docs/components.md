# Components

GoblinOS Assistant is composed of several key components that work together to provide comprehensive AI-powered development assistance.

## 🏗️ Backend API (`backend/`)

- **Framework**: FastAPI (Python)
- **Purpose**: Main API service handling AI processing and development assistance
  Note: Most backend-specific documentation has been consolidated under the canonical backend repository folder at `apps/goblin-assistant/backend/docs` (e.g. endpoint audits, monitoring, production quick-starts). See that folder for the canonical docs.

- **Features**: Intelligent model routing, debugging tools, error analysis, code suggestions

## 🎨 Frontend UI (`app/`, `src/`)

- **Framework**: Next.js 14.2.15 (App Router) + TypeScript
- **Purpose**: User interface for interacting with the AI assistant
- **Features**: Web-based interface for development tasks and AI interactions

## 🛠️ Infrastructure (`infra/`)

- **Tools**: Terraform, Cloudflare Workers, Docker
- **Primary CDN/Edge Provider**: Cloudflare (Workers, KV, D1, R2, Tunnel, Turnstile)

## 💾 Database & API Layer (`api/`, database files)

- **Database**: SQLite (default) or PostgreSQL (`goblin_assistant.db` or Postgres)
- **Purpose**: Data persistence, user sessions, and API routing
- **Features**: SQLAlchemy integration, database migrations

## 📊 Monitoring & Observability

- **Tools**: Sentry error tracking, Fly.io metrics, Vercel Analytics
- **Purpose**: Application monitoring, performance tracking, and alerting
- **Features**: Real-time error monitoring, performance insights, and health tracking
- **Setup**: See [Monitoring Setup Guide](./MONITORING_SETUP.md) for complete configuration
