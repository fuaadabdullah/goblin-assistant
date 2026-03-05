# Integrations Guide

This document provides comprehensive guides for setting up and configuring third-party integrations in the Goblin Assistant Backend API.

## Overview

The Goblin Assistant Backend integrates with several external services to provide monitoring, security, database, and AI provider functionality:

- **Datadog**: Application monitoring, metrics, and distributed tracing
- **Cloudflare**: Edge computing, security, and CDN services
- **Supabase**: Database, authentication, and storage services
- **AI Providers**: OpenAI, Anthropic, Google Gemini, Groq, DeepSeek

## Datadog Integration

Datadog provides comprehensive application monitoring, metrics collection, and distributed tracing for the Goblin Assistant Backend.

### Setup

#### 1. Create Datadog Account

1. Sign up at [datadoghq.com](https://www.datadoghq.com/)
2. Create a new organization
3. Navigate to **Organization Settings** → **API Keys**

#### 2. Generate API Keys

```bash
# Get your Datadog API Key and Application Key
# API Key: Used for sending data to Datadog
# Application Key: Used for accessing Datadog API
```

#### 3. Configure Environment Variables

```bash
# Add to your .env file or production environment
DATADOG_ENABLED=true
DATADOG_API_KEY=your-datadog-api-key
DATADOG_APP_KEY=your-datadog-application-key
DATADOG_SITE=datadoghq.com  # For US region
# DATADOG_SITE=datadoghq.eu  # For EU region
```

#### 4. Install Datadog SDK

```bash
pip install ddtrace
```

#### 5. Configure Application

The integration is automatically enabled when `DATADOG_ENABLED=true`:

```python
# api/datadog_integration.py is automatically imported
# Metrics are sent to Datadog automatically
```

### Features

#### Custom Metrics

```python
# Provider request metrics
track_provider_request(
    provider="openai", 
    duration=1.23, 
    success=True
)

# Conversation metrics
track_conversation_metrics(
    action="message_sent",
    user_id="user123"
)

# System health metrics
track_system_health(
    component="database",
    status="healthy"
 Tracing

All)
```

#### Distributed API requests are automatically traced:

```python
# Request flow tracing
GET /chat/conversations → Chat Router → Conversation Store → Database
```

#### Service Level Objectives (SLOs)

Monitor key performance indicators:

- **Chat Response Time**: P95 < 2 seconds
- **API Availability**: > 99.9%
- **Provider Success Rate**: > 98%

### Dashboard Configuration

#### Create Custom Dashboard

1. Go to **Dashboards** → **New Dashboard**
2. Add widgets for:
   - Request rate and response times
   - Error rates by endpoint
   - Provider usage and costs
   - Database and Redis performance

#### Key Metrics to Monitor

```json
{
  "application_metrics": {
    "http_requests_total": "Total request count",
    "http_request_duration_seconds": "Request latency",
    "http_requests_errors_total": "Error count by status code"
  },
  "business_metrics": {
    "provider_requests_total": "AI provider usage",
    "conversation_count": "Active conversations",
    "daily_active_users": "User engagement"
  },
  "infrastructure_metrics": {
    "database_connections": "Database connection pool",
    "redis_memory_usage": "Cache memory utilization",
    "cpu_memory_usage": "System resources"
  }
}
```

### Alerting

#### Create Alerts

1. Navigate to **Monitors** → **New Monitor**
2. Configure alerts for:

```yaml
# High error rate alert
Metric: http_requests_errors_total / http_requests_total > 0.05
Threshold: 5%
Message: "Error rate is above 5%"

# Slow response time alert  
Metric: http_request_duration_seconds:p95 > 2.0
Threshold: 2 seconds
Message: "P95 response time is above 2 seconds"

# Provider failure alert
Metric: provider_requests_errors_total > 10
Threshold: 10 errors per hour
Message: "High provider error rate detected"
```

### Troubleshooting

#### Common Issues

**No Data Appearing in Datadog:**

```bash
# Check environment variables
echo $DATADOG_API_KEY
echo $DATADOG_APP_KEY
echo $DATADOG_ENABLED

# Test Datadog connection
curl -X GET "https://api.datadoghq.com/api/v1/validate" \
  -H "DD-API-KEY: $DATADOG_API_KEY" \
  -H "DD-APPLICATION-KEY: $DATADOG_APP_KEY"
```

**Missing Traces:**

```bash
# Enable debug logging
export DD_TRACE_DEBUG=true
export DD_LOG_LEVEL=DEBUG

# Restart application
uvicorn main:app --reload
```

**High Cardinality Metrics:**

```python
# Avoid high-cardinality tags
# Good: service, endpoint, status
# Bad: user_id, session_id, random_uuids
```

## Cloudflare Integration

Cloudflare provides edge computing, security, and CDN services for the Goblin Assistant Backend.

### Setup

#### 1. Create Cloudflare Account

1. Sign up at [cloudflare.com](https://cloudflare.com/)
2. Add your domain to Cloudflare
3. Configure DNS settings

#### 2. Generate API Token

1. Go to **My Profile** → **API Tokens**
2. Create a new API token with permissions:
   - `Zone:Read` for DNS records
   - `Analytics:Read` for analytics data
   - `Security:Read` for security events

#### 3. Configure Environment Variables

```bash
# Add to your environment
CLOUDFLARE_API_TOKEN=your-api-token
CLOUDFLARE_ZONE_ID=your-zone-id
CLOUDFLARE_ACCOUNT_ID=your-account-id
```

#### 4. Setup DNS Records

```bash
# Add DNS records for your API
Type: A
Name: api
Content: your-server-ip
Proxy: Enabled (orange cloud)

Type: CNAME  
Name: www
Content: api.yourdomain.com
Proxy: Enabled (orange cloud)
```

### Features

#### Security Middleware

```python
# Automatic security headers
class CloudflareSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Validate Cloudflare security headers
        # Rate limiting
        # Bot detection
        pass
```

#### Edge Caching

```python
# Cache static content at the edge
@router.get("/static/{path:path}")
async def get_static(path: str):
    # Served from Cloudflare cache
    # Automatic compression
    # Global CDN distribution
    pass
```

#### DDoS Protection

Cloudflare automatically provides:
- DDoS mitigation
- Bot protection
- Rate limiting
- IP reputation filtering

### Analytics Integration

#### Traffic Analytics

```python
# Get Cloudflare analytics
analytics = CloudflareAnalytics()
traffic_data = await analytics.get_analytics(since="24h")

# Security events
security_events = await analytics.get_security_events(since="24h")
```

#### Web Analytics

```javascript
// Add to your frontend
<script defer src='https://static.cloudflareinsights.com/beacon.min.js' 
        data-cf-beacon='{"token": "your-beacon-token"}'></script>
```

### Workers Deployment

#### Deploy Edge Functions

```javascript
// cloudflare-worker.js
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  // Route requests to appropriate regions
  // Implement edge logic
  // Cache responses
  return fetch(request)
}
```

```bash
# Deploy worker
wrangler publish
```

### Troubleshooting

#### DNS Issues

```bash
# Check DNS propagation
dig api.yourdomain.com

# Verify Cloudflare proxy status
nslookup api.yourdomain.com
# Should return Cloudflare IP (not your server IP)
```

#### SSL/TLS Problems

1. Go to **SSL/TLS** → **Overview**
2. Set encryption mode to **Full (strict)**
3. Enable **Always Use HTTPS**
4. Enable **Automatic HTTPS Rewrites**

#### Performance Issues

```bash
# Enable Cloudflare caching
# Add Cache-Control headers
# Use Cloudflare Workers for edge logic
# Enable compression (Gzip/Brotli)
```

## Supabase Integration

Supabase provides PostgreSQL database, authentication, and storage services for the Goblin Assistant Backend.

### Setup

#### 1. Create Supabase Project

1. Sign up at [supabase.com](https://supabase.com/)
2. Create a new project
3. Note your project URL and API keys

#### 2. Configure Environment Variables

```bash
# Add to your environment
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

#### 3. Install Supabase Client

```bash
pip install supabase
```

### Database Setup

#### Create Tables

```sql
-- Conversations table
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT,
  title TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Messages table
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Users can view own conversations" ON conversations
  FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own conversations" ON conversations
  FOR INSERT WITH CHECK (auth.uid()::text = user_id);
```

#### Database Connection

```python
# Connect to Supabase database
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Use async operations
import asyncpg

async def get_db_connection():
    """Get database connection for async operations"""
    conn = await asyncpg.connect(DATABASE_URL)
    return conn
```

### Authentication

#### User Management

```python
# Create user
async def create_user(email: str, password: str):
    user = supabase.auth.sign_up({
        "email": email,
        "password": password
    })
    return user

# Verify JWT token
async def verify_jwt_token(token: str):
    try:
        user = supabase.auth.get_user(token)
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
```

#### Row Level Security

```sql
-- Example RLS policies

-- Conversations: Users can only access their own
CREATE POLICY "Users can manage own conversations"
ON conversations FOR ALL
USING (auth.uid()::text = user_id)
WITH CHECK (auth.uid()::text = user_id);

-- Messages: Users can only access messages in their conversations
CREATE POLICY "Users can manage messages in own conversations"
ON messages FOR ALL
USING (
  conversation_id IN (
    SELECT id FROM conversations 
    WHERE user_id = auth.uid()::text
  )
)
WITH CHECK (
  conversation_id IN (
    SELECT id FROM conversations 
    WHERE user_id = auth.uid()::text
  )
);
```

### Storage

#### File Upload

```python
# Upload file to Supabase Storage
async def upload_file(file_path: str, bucket: str = "avatars"):
    with open(file_path, 'rb') as f:
        response = supabase.storage.from_(bucket).upload(
            path=f"user_uploads/{uuid.uuid4()}",
            file=f,
            file_options={"content-type": "image/jpeg"}
        )
    return response

# Get public URL
async def get_file_url(bucket: str, path: str):
    response = supabase.storage.from_(bucket).get_public_url(path)
    return response
```

#### Create Storage Bucket

```sql
-- Create storage bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('avatars', 'avatars', true);
```

### Real-time Features

#### Subscribe to Changes

```python
# Listen for real-time updates
def subscribe_to_conversation(conversation_id: str):
    subscription = supabase.table('messages').on('*', 
        lambda payload: handle_message_change(payload)
    ).filter('conversation_id', 'eq', conversation_id).subscribe()
    
    return subscription
```

### Performance Connection Pooling

 Optimization

####```python
# Database connection pool
engine = create_async_engine(
    SUPABASE_DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
```

#### Query Optimization

```sql
-- Add indexes for better performance
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

### Troubleshooting

#### Connection Issues

```bash
# Test Supabase connection
curl -X GET "https://your-project.supabase.co/rest/v1/" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY"
```

#### Authentication Errors

```python
# Check JWT token validity
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

#### RLS Policy Issues

```sql
-- Check RLS policies
SELECT * FROM pg_policies WHERE tablename = 'conversations';

-- Test policy with specific user
SET LOCAL role authenticated;
SET LOCAL "request.jwt.claims" = '{"sub": "user-uuid"}';
SELECT * FROM conversations;
```

## AI Provider Integration

The system integrates with multiple AI providers for intelligent routing and redundancy.

### Supported Providers

#### OpenAI
- **Models**: GPT-4, GPT-3.5-turbo
- **Use Case**: General purpose, reasoning
- **API**: `https://api.openai.com/v1/chat/completions`

#### Anthropic
- **Models**: Claude-3-haiku, Claude-3-sonnet, Claude-3-opus
- **Use Case**: Safety-focused, long context
- **API**: `https://api.anthropic.com/v1/messages`

#### Google Gemini
- **Models**: Gemini-pro, Gemini-pro-vision
- **Use Case**: Multimodal, fast inference
- **API**: `https://generativelanguage.googleapis.com/v1beta/models/`

#### Groq
- **Models**: Mixtral, Llama2, Gemma
- **Use Case**: Fast inference, open source models
- **API**: `https://api.groq.com/openai/v1/chat/completions`

#### DeepSeek
- **Models**: DeepSeek-Coder, DeepSeek-Chat
- **Use Case**: Coding, reasoning
- **API**: `https://api.deepseek.com/v1/chat/completions`

### Configuration

```python
# Provider configuration
PROVIDERS = {
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4", "gpt-3.5-turbo"],
        "cost_per_token": 0.000002,  # $0.002 per 1K tokens
        "rate_limit": 10000,  # requests per minute
    },
    "anthropic": {
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "base_url": "https://api.anthropic.com",
        "models": ["claude-3-haiku", "claude-3-sonnet", "claude-3-opus"],
        "cost_per_token": 0.000003,
        "rate_limit": 5000,
    },
    # ... other providers
}
```

### Intelligent Routing

```python
# Routing algorithm
async def route_request(task_type: str, requirements: dict):
    """Route request to optimal provider"""
    available_providers = []
    
    for name, config in PROVIDERS.items():
        if await is_provider_available(name):
            score = calculate_provider_score(
                provider=name,
                task_type=task_type,
                requirements=requirements,
                config=config
            )
            available_providers.append((name, score))
    
    # Select best provider
    best_provider = max(available_providers, key=lambda x: x[1])
    return best_provider[0]

def calculate_provider_score(provider: str, task_type: str, 
                           requirements: dict, config: dict) -> float:
    """Calculate provider score based on multiple factors"""
    score = 0.0
    
    # Cost factor (lower is better)
    cost = requirements.get("cost_budget", 1.0)
    score += (1 - config["cost_per_token"]) * 0.3
    
    # Latency factor
    latency = requirements.get("max_latency", 5.0)
    provider_latency = await get_provider_latency(provider)
    if provider_latency < latency:
        score += 0.4
    
    # Quality factor
    quality = requirements.get("min_quality", 0.8)
    if config["quality_score"] >= quality:
        score += 0.3
    
    return score
```

### Provider Health Monitoring

```python
# Monitor provider health
class ProviderMonitor:
    async def check_provider_health(self, provider: str):
        """Check if provider is healthy and available"""
        try:
            # Test with a minimal request
            response = await make_test_request(provider)
            return {
                "provider": provider,
                "healthy": True,
                "response_time": response.time,
                "error_rate": response.error_rate
            }
        except Exception as e:
            return {
