# Goblin Assistant - Docker Deployment

This directory contains Docker configurations for deploying Goblin Assistant.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- At least 2GB free disk space

### Setup Docker (macOS)

If Docker daemon is not running:

```bash
# Check Docker status
./docker-daemon.sh status

# Start Docker daemon
./docker-daemon.sh start

# Quick check if ready
./docker-daemon.sh check
```

### Local Development

1. **Start the application:**

   ```bash
   ./docker-deploy.sh run
   ```

2. **Access the application:**
   - Frontend: `http://localhost`
   - API: `http://localhost:3001`
   - Health check: `http://localhost/api/health`

3. **Stop the application:**

   ```bash
   ./docker-deploy.sh stop
   ```

### Production Deployment

1. **Build the image:**

   ```bash
   ./docker-deploy.sh build
   ```

2. **Deploy to production:**

   ```bash
   ./docker-deploy.sh deploy -r your-registry.com -t v1.0.0
   ```

## Architecture

The Docker setup includes:

- **Multi-stage build** for optimized production images
- **Nginx** for static file serving and reverse proxy
- **FastAPI** backend for AI processing
- **Supervisor** for process management
- **Health checks** for monitoring

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `production` | Environment mode |
| `PYTHONPATH` | `/app` | Python path for FastAPI |

### Ports

- `80`: Nginx web server
- `3001`: FastAPI backend (internal)

### Volumes

- `./logs:/app/logs`: Application logs

## Development vs Production

### Development (`Dockerfile.dev`)

- Includes all development tools
- Source code mounted as volume
- Hot reloading enabled
- Larger image size (~2GB)

### Production (`Dockerfile`)

- Multi-stage build for optimization
- Only production dependencies
- Static files pre-built
- Smaller image size (~500MB)

## Troubleshooting

### Build Issues

```bash
# Clear Docker cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache
```

### Logs

```bash
# View all logs
./docker-deploy.sh logs

# View specific service logs
docker-compose logs goblin-assistant
```

### Health Checks

```bash
# Manual health check
curl http://localhost/api/health

# Check container status
docker-compose ps
```

## Security Considerations

- Images are built with minimal attack surface
- No root processes in production
- SSL/TLS should be handled by external reverse proxy
- API keys should be mounted as secrets

## CI/CD Integration

The Docker setup is designed to work with CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Build and push
  run: ./docker-deploy.sh deploy -r ghcr.io -t ${{ github.sha }}
```

## File Structure

```
.
├── Dockerfile              # Production build
├── Dockerfile.dev          # Development build
├── docker-compose.yml      # Local orchestration
├── .dockerignore          # Build optimization
├── docker-deploy.sh       # Deployment script
└── infra/nginx/           # Nginx configuration
    ├── goblin-assistant.conf
    └── deploy.sh
```
