# MCP (Model Control Plane) - Goblin Assistant

The **Model Control Plane (MCP)** is the orchestration layer that makes Goblin Assistant behave like a weaponized assistant. It provides centralized request management, provider routing, streaming, observability, and policy enforcement.

## 🏗️ Architecture Overview

```
React/Tauri UI <--> MCP FastAPI (Port 8000)
                        │
        ┌───────────────┴───────────────┐
        │                              │
   Router Engine                 Worker Queue (Redis)
   (health/cost/circuit)         - Async processing
        │                              │
Local Models <--> Provider Plugins     Result Streaming
        │                              │
  Vector DB (Chroma) + Postgres        WebSocket/SSE
        │                              │
   Observability (Datadog + Sentry)    Audit Logs
        │                              │
   Security Layer (Secret Scanning)    Policy Enforcement
```

## 🚀 Quick Start

### 1. Database Setup

```bash
# Install dependencies
cd api/fastapi
pip install -r requirements.txt

# Set up database (requires PostgreSQL running)
export DATABASE_URL="postgresql://user:password@localhost/mcp_db"
python setup_mcp_db.py
```

### 2. Start Services

```bash
# Start MCP API (port 8000)
uvicorn mcp_router:app --host 0.0.0.0 --port 8000 --reload

# Start worker (in another terminal)
python mcp_worker.py

# Or use Docker Compose
docker-compose -f docker-compose.mcp.yml up -d
```

### 3. Test the MCP

```bash
# Run the test script
./test_mcp.sh

# Or test manually
curl -X POST http://localhost:8000/mcp/v1/request \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "prompt": "Hello MCP!", "task_type": "chat"}'
```

## 📡 API Endpoints

### Core Endpoints

- `POST /mcp/v1/request` - Submit a new request
- `GET /mcp/v1/request/{id}` - Get request status
- `GET /mcp/v1/request/{id}/result` - Get final result
- `POST /mcp/v1/cancel/{id}` - Cancel a running request
- `WS /mcp/v1/stream/{id}` - Real-time streaming

### Admin Endpoints

- `GET /mcp/v1/admin/metrics` - Basic health metrics

## 🗃️ Database Schema

### mcp_request
- Request tracking with status, priority, cost estimates
- User hashing for privacy
- Provider hints and attempt tracking

### mcp_event
- Audit trail for all request events
- Structured JSON payloads
- Indexed for performance

### mcp_result
- Final results with token counts and costs
- Flexible JSON storage

## 🔄 Request Lifecycle

1. **Submit** → Client sends request with prompt and metadata
2. **Validate** → MCP validates, hashes user ID, estimates cost
3. **Queue** → Request queued in Redis for async processing
4. **Process** → Worker picks up, routes to provider, streams results
5. **Complete** → Results stored, metrics emitted, client notified

## 🎯 Key Features

## 🎯 Key Features

### ✅ Implemented
- FastAPI router with all core endpoints
- PostgreSQL models with SQLAlchemy
- Redis queue integration
- WebSocket streaming support
- Multi-provider routing (31+ AI providers)
- Cost estimation and user hashing
- Event logging and metrics collection
- Docker Compose setup
- **ChromaDB integration** for RAG and document indexing
- **Comprehensive secret scanning** at multiple layers
- **Security event logging** and audit trails
- **Circuit breaker pattern** for provider failover
- **JWT authentication** and user management
- **Real-time monitoring** with Datadog integration

### 🚧 Next Steps
- Advanced RAG with reranker cross-encoder
- Provider cost accounting dashboard
- Streaming UI polish
- Kubernetes deployment configuration

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/mcp_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Observability
DD_TRACE_ENABLED=true
DD_SERVICE=mcp-api
DD_ENV=development

# API Keys (for providers)
OPENAI_API_KEY=sk-...
```

### Scaling

- **API Service**: Stateless, horizontally scalable
- **Workers**: Scale based on queue depth
- **Database**: Use connection pooling
- **Redis**: Cluster for high availability

## 📊 Monitoring & Metrics

### Datadog Metrics
- `goblin.mcp.request.count` - Request volume by task type
- `goblin.mcp.request.latency_ms` - End-to-end latency
- `goblin.mcp.tokens` - Token usage
- `goblin.mcp.cost_estimate_usd` - Cost tracking
- `goblin.mcp.fallback.count` - Provider fallback events

### Health Checks
- API health: `GET /mcp/v1/admin/metrics`
- Worker health: Queue depth monitoring
- Database: Connection pool status

## 🛡️ Security & Privacy

- **User Hashing**: SHA256 truncated hashes for privacy
- **Secret Scanning**: Regex-based detection before provider calls
- **Audit Logging**: All actions tracked with request IDs
- **Rate Limiting**: Per-user and global limits (TODO)
- **RBAC**: Token-based permissions (TODO)

## 🧪 Testing

```bash
# Unit tests
pytest api/fastapi/test_mcp_*.py

# Integration tests
./test_mcp.sh

# Load testing
# TODO: Add load test script
```

## 🚀 Deployment

### Production Setup

```bash
# Build and deploy
docker-compose -f docker-compose.mcp.yml up -d

# Scale workers
docker-compose -f docker-compose.mcp.yml up -d --scale mcp-worker=3

# Logs
docker-compose -f docker-compose.mcp.yml logs -f mcp-api
```

### Kubernetes (Future)

```yaml
# TODO: Add K8s manifests
- HPA for workers based on queue depth
- ConfigMaps for environment variables
- Secrets for API keys
```

## 🔗 Integration Points

### Existing Goblin Assistant
- Integrates with current FastAPI app
- Uses existing metrics and tracing
- Compatible with current provider plugins

### Future Extensions
- **RAG Pipeline**: Context retrieval integration
- **Workflow Engine**: Multi-step request processing
- **Admin UI**: Real-time monitoring dashboard
- **Plugin System**: Dynamic provider loading

## 📝 Development Notes

### Adding New Providers

```python
# In mcp_worker.py
def call_provider(self, provider: str, request, context):
    if provider == "my_provider":
        # Implement provider logic
        return self.call_my_provider(request, context)
```

### Custom Metrics

```python
# Emit custom metrics
goblin_metrics.histogram("goblin.mcp.custom_metric", value, tags={"key": "value"})
```

### Event Logging

```python
# Log structured events
self.log_event(request_id, "custom_event", {"data": "value"})
```

## 🤝 Contributing

1. **Database Changes**: Update `mcp_models.py` and `setup_mcp_db.py`
2. **API Changes**: Modify `mcp_router.py` with proper Pydantic models
3. **Worker Logic**: Update `mcp_worker.py` for processing changes
4. **Testing**: Add tests in `test_mcp_*.py`

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Models](https://sqlalchemy.org/)
- [Redis Queue](https://redis.io/)
- [Datadog APM](https://docs.datadoghq.com/tracing/)

---

**MCP turns chaos into control. Every request flows through here - make it count.**
