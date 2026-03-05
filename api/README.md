# Goblin Assistant Backend API

## Welcome to the Goblin Assistant Backend

This directory contains the FastAPI-based backend service for the Goblin Assistant AI platform.

### Quick Links

- **[📖 Complete API Documentation](./docs/README.md)** - Comprehensive API reference, architecture, and guides
- **[🚀 Setup Guide](./docs/SETUP.md)** - Installation and configuration instructions
- **[🏗️ Architecture](./docs/ARCHITECTURE.md)** - System design and component details
- **[🔧 Development Guide](./docs/DEVELOPMENT.md)** - Contributing and development workflow
- **[🚨 Troubleshooting](./docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload

# Access API documentation
open http://localhost:8000/docs
```

### Key Features

- **FastAPI-based** async API with automatic OpenAPI documentation
- **Intelligent routing** across multiple AI providers (OpenAI, Anthropic, etc.)
- **Real-time streaming** support for long-running tasks
- **Comprehensive monitoring** with health checks and metrics
- **Multi-integration** support (Datadog, Cloudflare, Supabase)
- **Scalable architecture** with Redis caching and database support

### API Structure

The API is organized into specialized routers:

- `/health` - System health and monitoring endpoints
- `/chat` - Conversation management and AI chat
- `/api` - Core task routing and orchestration
- `/routing` - Provider selection and management
- `/search` - Document search and vector operations
- `/execute` - Task execution and management
- `/stream` - Real-time streaming endpoints
- `/api-keys` - AI provider API key management
- `/settings` - System and provider configuration

For detailed API documentation, visit the [complete documentation](./docs/README.md).

### Documentation Standards

All documentation follows our established standards:
- **Version**: 1.0.0 (aligned with API version)
- **Format**: Markdown with consistent structure
- **Coverage**: Development, deployment, and operations
- **Quality**: Tested examples and cross-references

### Entry Points

- **Development**: `python start_server.py` or `uvicorn main:app --reload`
- **Production**: Uses Procfile pointing to `main:app`

### Architecture

- FastAPI-based async API
- Provider routing via intelligent routing system
- See `docs/ARCHITECTURE.md` for detailed system design
- See `MIGRATION_SUMMARY.md` for DB migration status

---

**Last Updated**: December 17, 2025
**Documentation Version**: 1.0.0
**API Version**: 1.0.0
