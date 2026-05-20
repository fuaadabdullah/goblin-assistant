# Redis Setup Guide for Goblin Assistant

This guide provides instructions for setting up Redis for production deployment of the Goblin Assistant backend.

## Overview

Redis is used for:
- Caching API responses to improve performance
- Session storage for user authentication
- Rate limiting to prevent abuse
- Task result caching for long-running operations
- Provider status caching for health monitoring

## Production Setup

### 1. Environment Configuration

The Redis configuration is already set up in `api/.env`:

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### 2. Docker Setup (Recommended for Production)

Create a `docker-compose.redis.yml` file:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7.2-alpine
    container_name: goblin-assistant-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    environment:
      - REDIS_REPLICATION_MODE=master
    networks:
      - goblin-assistant-network

volumes:
  redis_data:

networks:
  goblin-assistant-network:
    driver: bridge
```

### 3. Redis Configuration File

Create `redis.conf` for production settings:

```conf
# Network
bind 0.0.0.0
port 6379
tcp-backlog 511
timeout 300
tcp-keepalive 300

# General
daemonize no
supervised no
pidfile /var/run/redis_6379.pid
loglevel notice
logfile ""

# Snapshotting
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /data

# Security
# requirepass your_redis_password_here

# Memory Management
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Performance
tcp-nodelay yes
hz 10
dynamic-hz yes

# Client Output Buffer Limits
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60

# Slow Log
slowlog-log-slower-than 10000
slowlog-max-len 128
```

### 4. Fly.io Deployment

For Fly.io deployment, add this to your `fly.toml`:

```toml
[[services]]
  internal_port = 6379
  protocol = "tcp"

  [services.concurrency]
    soft_limit = 25
    hard_limit = 25

  [[services.ports]]
    port = "6379"
    handlers = ["tls", "http"]
```

### 5. Environment Variables for Production

Update your production environment variables:

```bash
# For production, use a managed Redis service
REDIS_URL=redis://username:password@your-redis-host:6379/0
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# Connection pool settings
REDIS_MAX_CONNECTIONS=100
REDIS_SOCKET_TIMEOUT=5.0
REDIS_CONNECT_TIMEOUT=5.0
REDIS_RETRY_ON_TIMEOUT=true
REDIS_SOCKET_KEEPALIVE=true

# Health check
REDIS_HEALTH_CHECK_INTERVAL=30

# Cache TTL settings
REDIS_DEFAULT_TTL=3600
REDIS_CACHE_PREFIX=goblin_assistant_prod:
```

### 6. Managed Redis Services

#### AWS ElastiCache
```bash
REDIS_URL=redis://your-elasticache-endpoint.cache.amazonaws.com:6379/0
```

#### Google Cloud Memorystore
```bash
REDIS_URL=redis://your-memorystore-ip:6379/0
```

#### Azure Cache for Redis
```bash
REDIS_URL=redis://your-redis-cache.redis.cache.windows.net:6380/0?ssl=true
```

#### Upstash (Serverless Redis)
```bash
REDIS_URL=redis://your-upstash-url.upstash.io:6379
REDIS_PASSWORD=your-upstash-token
```

### 7. Monitoring and Health Checks

The backend includes Redis health monitoring:

```python
# Test Redis connection
from api.config.redis_config import test_redis_connection

async def check_redis_health():
    is_healthy = await test_redis_connection()
    return is_healthy
```

### 8. Cache Management

Use the cache utilities in your application:

```python
from api.storage.cache import cache, cache_response, get_cached_provider_status

# Cache API responses
@cache_response(expire=600, cache_type="ROUTING_CACHE")
async def get_routing_info():
    # Your logic here
    return result

# Cache provider status
await cache_provider_status("openai", {"status": "healthy", "latency": 150})

# Get cached data
status = await get_cached_provider_status("openai")
```

### 9. Development Setup

For local development, you can use Docker:

```bash
# Start Redis
docker run -d --name redis-dev -p 6379:6379 redis:7.2-alpine

# Or use Redis CLI for testing
docker exec -it redis-dev redis-cli
```

### 10. Troubleshooting

#### Connection Issues
- Check Redis is running: `docker ps` or `systemctl status redis`
- Verify network connectivity: `telnet localhost 6379`
- Check Redis logs: `docker logs redis-dev`

#### Performance Issues
- Monitor memory usage: `redis-cli info memory`
- Check slow queries: `redis-cli slowlog get 10`
- Adjust maxmemory settings in redis.conf

#### Authentication Issues
- Verify password in REDIS_URL matches redis.conf requirepass
- Check firewall rules allow port 6379

### 11. Security Best Practices

1. **Use strong passwords** for Redis authentication
2. **Enable TLS** for production connections
3. **Restrict network access** using firewalls
4. **Monitor connections** and set appropriate limits
5. **Regular backups** of Redis data
6. **Use separate databases** for different environments

### 12. Scaling Redis

For high-traffic production:

1. **Redis Cluster** for horizontal scaling
2. **Redis Sentinel** for high availability
3. **Read replicas** for read-heavy workloads
4. **Connection pooling** to manage client connections

This Redis setup provides a solid foundation for production deployment with proper caching, monitoring, and scalability features.
