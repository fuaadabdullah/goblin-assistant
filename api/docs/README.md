# Goblin Assistant Backend API Documentation

## Overview

The Goblin Assistant Backend is a FastAPI-based asynchronous API service that provides intelligent AI model routing, conversation management, and development assistance capabilities. The system features intelligent provider selection, real-time streaming, comprehensive health monitoring, and seamless integration with multiple AI providers.

## Quick Start

### Prerequisites

- Python 3.11+
- pip (Python package manager)
- Redis (optional, for production caching)

### Installation

```bash
# Clone and navigate to the API directory
cd apps/goblin-assistant/api

# Install dependencies
pip install -r requirements.txt

# Run the development server
uvicorn main:app --reload --port 8000

# Access the API
open http://localhost:8000/docs
```

### Environment Configuration

Create a `.env` file with the following variables:

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

# Redis (for production)
REDIS_URL=redis://localhost:6379
USE_REDIS_CHALLENGES=false
```

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│  Middleware Stack                                           │
│  ├── CORS Middleware                                        │
│  ├── Error Handling Middleware                             │
│  ├── Security Middleware                                   │
│  └── Monitoring Middleware                                 │
├─────────────────────────────────────────────────────────────┤
│  Router Stack                                               │
│  ├── Health Router (/health)                               │
│  ├── Chat Router (/chat)                                   │
│  ├── API Router (/api)                                     │
│  ├── Routing Router (/routing)                             │
│  ├── Execute Router (/execute)                             │
│  ├── Parse Router (/parse)                                 │
│  ├── Raptor Router (/raptor)                               │
│  ├── API Keys Router (/api-keys)                           │
│  ├── Settings Router (/settings)                           │
│  ├── Search Router (/search)                               │
│  └── Stream Router (/stream)                               │
├─────────────────────────────────────────────────────────────┤
│  Integration Layer                                          │
│  ├── Datadog Integration                                   │
│  ├── Cloudflare Integration                                │
│  ├── Supabase Integration                                  │
│  └── Provider Dispatchers                                  │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                 │
│  ├── Database (SQLite/PostgreSQL)                          │
│  ├── Redis Cache                                           │
│  ├── Vector Store (ChromaDB)                               │
│  └── File Storage                                          │
└─────────────────────────────────────────────────────────────┘
```

### Request Flow

1. **Request Reception**: FastAPI handles incoming HTTP requests
2. **Middleware Processing**: CORS, authentication, logging, monitoring
3. **Router Routing**: Request routed to appropriate router based on path
4. **Business Logic**: Router processes request using providers/services
5. **Response Processing**: Response formatted and returned to client
6. **Monitoring**: Metrics and logs collected throughout the process

## API Reference

### Authentication

The API uses JWT-based authentication for protected endpoints. Include the JWT token in the Authorization header:

```http
Authorization: Bearer <your-jwt-token>
```

### Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://goblin-assistant-backend.onrender.com`

### API Versioning

The API uses URL-based versioning:
- **Current Version**: `/v1/`
- **Future Versions**: `/v2/`, `/v3/`, etc.

### Rate Limiting

- **Default**: 100 requests per minute per IP
- **Authenticated**: 1000 requests per minute per user
- **Burst**: 10 requests per second

## Router Documentation

### Health Router (`/health`)

Comprehensive health monitoring and system status endpoints.

#### Endpoints

- `GET /health` - Basic health check
- `GET /v1/health/` - Comprehensive health check
- `GET /v1/health/all` - All services health status
- `GET /v1/health/chroma/status` - Vector database health
- `GET /v1/health/mcp/status` - MCP service health
- `GET /v1/health/raptor/status` - Raptor monitoring health
- `GET /v1/health/sandbox/status` - Sandbox environment health
- `GET /v1/health/scheduler/status` - Background task scheduler health
- `GET /v1/health/cost-tracking` - Cost tracking status
- `GET /v1/health/latency-history/{service}` - Service latency history
- `GET /v1/health/service-errors/{service}` - Service error analysis
- `POST /v1/health/retest/{service}` - Service health retest

#### Example Response

```json
{
  "status": "healthy",
  "timestamp": "2025-12-17T22:21:00Z",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 15
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 5
    },
    "providers": {
      "openai": "healthy",
      "anthropic": "healthy"
    }
  }
}
```

### Chat Router (`/chat`)

Conversation management and chat completion endpoints.

#### Endpoints

- `POST /chat/conversations` - Create new conversation
- `GET /chat/conversations` - List user conversations
- `GET /chat/conversations/{conversation_id}` - Get conversation details
- `PUT /chat/conversations/{conversation_id}/title` - Update conversation title
- `DELETE /chat/conversations/{conversation_id}` - Delete conversation
- `POST /chat/conversations/{conversation_id}/messages` - Send message
- `POST /chat/completions` - OpenAI-compatible chat completions

#### Example Usage

```bash
# Create a conversation
curl -X POST "http://localhost:8000/chat/conversations" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Chat Session"}'

# Send a message
curl -X POST "http://localhost:8000/chat/conversations/{conversation_id}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how can you help me?",
    "provider": "openai",
    "model": "gpt-3.5-turbo"
  }'
```

### API Router (`/api`)

Core task routing and orchestration endpoints.

#### Endpoints

- `POST /api/route_task` - Route task to best provider
- `POST /api/route_task_stream_start` - Start streaming task
- `GET /api/route_task_stream_poll/{stream_id}` - Poll streaming task
- `POST /api/route_task_stream_cancel/{stream_id}` - Cancel streaming task
- `GET /api/goblins` - List available goblins
- `GET /api/history/{goblin_id}` - Get goblin task history
- `GET /api/stats/{goblin_id}` - Get goblin statistics
- `POST /api/orchestrate/parse` - Parse orchestration plan
- `POST /api/orchestrate/execute` - Execute orchestration plan
- `GET /api/orchestrate/plans/{plan_id}` - Get orchestration plan

#### Example Usage

```bash
# Route a task
curl -X POST "http://localhost:8000/api/route_task" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "code_review",
    "payload": {"code": "print('Hello World')"},
    "prefer_cost": true
  }'
```

### Routing Router (`/routing`)

Provider management and intelligent routing endpoints.

#### Endpoints

- `GET /routing/providers` - List all available providers
- `GET /routing/providers/{capability}` - Get providers for capability
- `POST /routing/route` - Route request to best provider

#### Example Usage

```bash
# Get providers for chat capability
curl "http://localhost:8000/routing/providers/chat"

# Route a request
curl -X POST "http://localhost:8000/routing/route" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "chat",
    "payload": {"message": "Hello"},
    "prefer_local": false
  }'
```

### Search Router (`/search`)

Document search and vector store operations.

#### Endpoints

- `POST /search/documents` - Search documents
- `GET /search/collections` - List collections
- `POST /search/collections/{name}/documents` - Add document to collection
- `GET /search/collections/{name}/documents` - Get collection documents

### Execute Router (`/execute`)

Task execution and management endpoints.

#### Endpoints

- `POST /execute/task` - Execute a task
- `GET /execute/tasks/{task_id}/status` - Get task status
- `POST /execute/tasks/{task_id}/simulate` - Simulate task execution

### Stream Router (`/stream`)

Real-time streaming endpoints for long-running operations.

#### Endpoints

- `POST /stream/task` - Start streaming task
- `GET /stream/{stream_id}` - Get stream status

### API Keys Router (`/api-keys`)

Manage AI provider API keys.

#### Endpoints

- `POST /api-keys/{provider}` - Store API key
- `GET /api-keys/{provider}` - Get API key status
- `DELETE /api-keys/{provider}` - Delete API key

### Settings Router (`/settings`)

System and provider settings management.

#### Endpoints

- `GET /settings` - Get all settings
- `PUT /settings/providers/{name}` - Update provider settings
- `PUT /settings/models/{name}` - Update model settings
- `POST /settings/providers/{name}/test` - Test provider connection

## Middleware Stack

### CORS Middleware

Handles Cross-Origin Resource Sharing for web frontend integration.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Error Handling Middleware

Centralized error processing and response formatting.

```python
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle exceptions and format responses
        # Log errors for monitoring
        # Return user-friendly error messages
```

### Monitoring Middleware

Request/response logging and performance monitoring.

```python
class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Track request metrics
        # Log performance data
        # Monitor error rates
```

## Integrations

### Datadog Integration

Comprehensive application monitoring and metrics collection.

#### Features

- Custom metrics tracking (requests, costs, performance)
- Distributed tracing
- Error tracking and alerting
- Service health monitoring

#### Configuration

```python
# Enable Datadog integration
DATADOG_ENABLED=true
DATADOG_API_KEY=your-datadog-api-key
DATADOG_APP_KEY=your-datadog-app-key
```

### Cloudflare Integration

Edge computing and security features.

#### Features

- WAF (Web Application Firewall)
- DDoS protection
- Edge caching
- Analytics and logging

#### Configuration

```python
# Cloudflare settings
CLOUDFLARE_API_TOKEN=your-api-token
CLOUDFLARE_ZONE_ID=your-zone-id
```

### Supabase Integration

Database, authentication, and storage services.

#### Features

- PostgreSQL database
- Row-level security
- Real-time subscriptions
- File storage

#### Configuration

```python
# Supabase settings
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

## Data Models

### Common Response Format

All API responses follow a consistent format:

```json
{
  "success": true,
  "data": { ... },
  "metadata": {
    "timestamp": "2025-12-17T22:21:00Z",
    "version": "1.0.0",
    "request_id": "uuid"
  }
}
```

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request parameters are invalid",
    "details": { ... }
  },
  "metadata": {
    "timestamp": "2025-12-17T22:21:00Z",
    "request_id": "uuid"
  }
}
```

## Error Handling

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid authentication)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error
- `503` - Service Unavailable

### Error Codes

| Code | Description |
|------|-------------|
| `INVALID_REQUEST` | Request parameters are invalid |
| `AUTHENTICATION_FAILED` | Invalid or missing authentication |
| `PROVIDER_UNAVAILABLE` | AI provider is not available |
| `ROUTING_FAILED` | Task routing failed |
| `RATE_LIMIT_EXCEEDED` | Request rate limit exceeded |
| `INTERNAL_ERROR` | Internal server error |

## Performance

### Response Time Targets

- Health endpoints: < 50ms
- Simple API calls: < 200ms
- AI provider requests: < 5 seconds
- Streaming responses: < 100ms initial chunk

### Optimization Features

- Connection pooling
- Request caching
- Async processing
- Provider health monitoring
- Automatic failover

## Monitoring

### Health Checks

The system provides comprehensive health monitoring:

- Database connectivity
- Redis availability
- AI provider status
- System resource usage
- Response time tracking

### Metrics

Key metrics tracked:

- Request count and rate
- Response times (P50, P95, P99)
- Error rates
- Provider usage
- Cost tracking
- Cache hit rates

### Logging

Structured logging with correlation IDs:

```json
{
  "timestamp": "2025-12-17T22:21:00Z",
  "level": "INFO",
  "request_id": "uuid",
  "user_id": "user123",
  "endpoint": "/chat/completions",
  "duration_ms": 250,
  "status": 200
}
```

## Development

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api_endpoints.py

# Run with coverage
pytest --cov=api tests/
```

### Code Style

- Follow PEP 8 for Python code
- Use type hints for all functions
- Document all public APIs
- Use async/await for I/O operations

### Debugging

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
uvicorn main:app --reload
```

## Deployment

### Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Redis configured for caching
- [ ] Monitoring and logging enabled
- [ ] Rate limiting configured
- [ ] Security headers set
- [ ] SSL/TLS certificates installed
- [ ] Health checks configured
- [ ] Backup strategy implemented

### Scaling Considerations

- Use connection pooling for databases
- Implement Redis for session storage
- Configure load balancing
- Monitor resource usage
- Set up auto-scaling

## Troubleshooting

### Common Issues

#### High Response Times

1. Check AI provider status
2. Monitor database performance
3. Review Redis connectivity
4. Analyze request patterns

#### Authentication Failures

1. Verify JWT token validity
2. Check token expiration
3. Validate API key configuration
4. Review middleware configuration

#### Provider Errors

1. Check API key validity
2. Verify provider service status
3. Review rate limits
4. Monitor quota usage

### Debug Endpoints

- `/health` - System health status
- `/debug/config` - Configuration debugging (development only)
- `/debug/providers` - Provider status

## Support

For technical support:

1. Check the troubleshooting guide
2. Review application logs
3. Consult the health endpoints
4. Contact the development team

## Changelog

### Version 1.0.0

- Initial API release
- Basic routing and chat functionality
- Health monitoring
- Provider integrations
- OpenAPI documentation
