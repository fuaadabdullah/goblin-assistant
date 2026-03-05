# 🔒 Secure Code Execution Sandbox

A comprehensive sandbox system for secure code execution in isolated Docker containers, integrated into the Goblin Assistant application.

## 🚀 Overview

The sandbox provides a secure environment for executing untrusted user code with the following key features:

- **Container Isolation**: Code runs in hardened Docker containers
- **Resource Limits**: CPU, memory, and file system restrictions
- **Security Controls**: No network access, non-root execution, seccomp/AppArmor profiles
- **Image Signing**: Optional cosign signature verification
- **Job Queueing**: Redis-based job queuing with RQ
- **Artifact Storage**: S3-compatible storage for generated files
- **API Integration**: RESTful API with authentication and rate limiting
- **Web Interface**: Integrated React component in the chat interface

## 📁 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   FastAPI       │    │   RQ Worker     │
│   (React/TSX)   │◄──►│   Sandbox API   │◄──►│   (Docker)      │
│                 │    │                 │    │                 │
│ • Code Editor   │    │ • Job Queueing  │    │ • Container     │
│ • Job Status    │    │ • Auth/Rate Lim │    │   Execution     │
│ • Logs Viewer   │    │ • Artifact Mgmt │    │ • Security      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │   Redis Queue   │
                    │   + Metadata    │
                    └─────────────────┘
```

## 🔧 Quick Start

### 1. Enable Sandbox
```bash
# Set environment variable
export SANDBOX_ENABLED=true

# Or add to your .env file
echo "SANDBOX_ENABLED=true" >> .env
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start Services
```bash
# Build and start all services
docker-compose up --build

# Or start specific services
docker-compose up redis sandbox-worker goblin-assistant-backend
```

### 4. Access the Sandbox
- Open http://localhost:3000
- Navigate to the Chat page
- Click the "Code Sandbox" tab

## 🎯 Usage

### Web Interface
1. **Select Language**: Choose Python, JavaScript, or Bash
2. **Write Code**: Enter your code in the editor
3. **Configure Options**: Set timeout (1-300 seconds) and runtime arguments
4. **Execute**: Click "Execute Code" to run in sandbox
5. **Monitor**: Watch real-time status updates
6. **View Results**: Check execution logs and download artifacts

### API Usage
```python
import requests

# Submit a job
response = requests.post('http://localhost:8001/api/sandbox/submit', json={
    'language': 'python',
    'source': 'print("Hello World!")',
    'timeout': 10
}, headers={'X-API-Key': 'your-api-key'})

job_id = response.json()['job_id']

# Check status
status = requests.get(f'http://localhost:8001/api/sandbox/status/{job_id}',
                     headers={'X-API-Key': 'your-api-key'})

# Get logs
logs = requests.get(f'http://localhost:8001/api/sandbox/logs/{job_id}',
                   headers={'X-API-Key': 'your-api-key'})
```

## 🔒 Security Features

### Container Security
- **Network Disabled**: No internet access during execution
- **Non-root User**: Code runs as `runner` user (UID 1000)
- **Resource Limits**: 256MB RAM, 0.25 CPU cores, 10-second CPU time
- **Filesystem Isolation**: Read-only root, writable `/tmp` with 64MB limit
- **Capability Dropping**: All Linux capabilities removed

### Application Security
- **Input Validation**: Language restrictions, timeout limits, size checks
- **Authentication**: API key required for all operations
- **Rate Limiting**: 10 requests/minute, 100 requests/hour per user
- **Audit Logging**: Job metadata stored in Redis with timestamps

### Optional Security (Configurable)
- **Image Signing**: Cosign signature verification before container execution
- **AppArmor/seccomp**: Additional kernel-level restrictions
- **S3 Storage**: Encrypted artifact storage with lifecycle policies

## ⚙️ Configuration

### Environment Variables
```bash
# Core Settings
SANDBOX_ENABLED=true                    # Enable/disable sandbox
SANDBOX_IMAGE=goblin-assistant-sandbox:latest  # Container image
JOBS_DIR=/var/lib/goblin/sandbox_jobs   # Job working directory

# Security Limits
MAX_JOB_MEMORY=256m                     # Memory limit per job
MAX_JOB_CPUS=0.25                       # CPU limit per job
JOB_TIMEOUT_SECONDS=10                  # Default timeout

# Rate Limiting
SANDBOX_RATE_LIMIT_PER_MINUTE=10        # Requests per minute
SANDBOX_RATE_LIMIT_PER_HOUR=100         # Requests per hour

# Optional Security
COSIGN_PUBLIC_KEY_PATH=/etc/sandbox/cosign.pub  # Image signing key
S3_BUCKET=goblin-sandbox               # Artifact storage bucket
```

### Docker Compose Services
```yaml
services:
  sandbox-worker:
    build:
      context: .
      dockerfile: Dockerfile.sandbox
    environment:
      - REDIS_URL=redis://redis:6379/0
      - SANDBOX_IMAGE=goblin-assistant-sandbox:latest
    volumes:
      - sandbox_jobs:/work
      - /var/run/docker.sock:/var/run/docker.sock:ro
```

## 🧪 Testing

### Run Integration Tests
```bash
python test_sandbox_integration.py
```

### API Demo
```bash
python sandbox_demo.py
```

### Manual Testing
```bash
# Test container execution directly
docker run --rm \
  --network none \
  --memory=256m \
  --cpus=0.25 \
  --user runner \
  --read-only \
  --tmpfs /tmp:rw,size=64m \
  -v $(pwd)/test_job:/work \
  goblin-assistant-sandbox:latest \
  python /work/main.py
```

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sandbox/submit` | Submit code for execution |
| GET | `/api/sandbox/status/{job_id}` | Get job status |
| GET | `/api/sandbox/logs/{job_id}` | Get execution logs |
| GET | `/api/sandbox/artifacts/{job_id}` | List job artifacts |
| GET | `/api/sandbox/artifacts/{job_id}/download/{filename}` | Download artifact |
| POST | `/api/sandbox/cancel/{job_id}` | Cancel running job |
| GET | `/api/sandbox/health/status` | Health check |

## 🔧 Supported Languages

| Language | Runtime | File Extension |
|----------|---------|----------------|
| Python | CPython 3.11 | `.py` |
| JavaScript | Node.js 18 | `.js` |
| Bash | GNU Bash | `.sh` |

## 🚀 CI/CD Pipeline

### GitHub Actions Workflow
- **Trigger**: Push to `main`/`develop` or changes to sandbox files
- **Security Scanning**: Trivy vulnerability scanning
- **Image Signing**: Cosign signature generation
- **Artifact Attestation**: SLSA provenance records

### Build Commands
```bash
# Build sandbox image
docker build -f Dockerfile.sandbox -t goblin-assistant-sandbox:latest .

# Run security scan
trivy image goblin-assistant-sandbox:latest

# Sign image
cosign sign goblin-assistant-sandbox:latest
```

## 📈 Monitoring & Observability

### Health Checks
- Container health status
- Redis connectivity
- Queue depth monitoring
- Resource usage metrics

### Metrics (Future Enhancement)
- Job execution duration
- Success/failure rates
- Resource utilization
- Queue performance

## 🐛 Troubleshooting

### Common Issues

**Sandbox not enabled**
```bash
# Check environment
echo $SANDBOX_ENABLED

# Enable in docker-compose
export SANDBOX_ENABLED=true
docker-compose up
```

**Container execution fails**
```bash
# Check Docker daemon
docker ps

# Check sandbox worker logs
docker-compose logs sandbox-worker

# Test manual execution
docker run --rm goblin-assistant-sandbox:latest python -c "print('test')"
```

**API authentication errors**
```bash
# Check API key
curl -H "X-API-Key: your-key" http://localhost:8001/api/sandbox/health/status

# Verify API is running
curl http://localhost:8001/health
```

### Debug Commands
```bash
# Check Redis queue
docker-compose exec redis redis-cli LLEN sandbox-jobs

# Inspect job data
docker-compose exec redis redis-cli HGETALL "sandbox:job:job-id"

# View worker logs
docker-compose logs -f sandbox-worker

# Test API endpoints
curl -X POST http://localhost:8001/api/sandbox/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: devkey" \
  -d '{"language":"python","source":"print(\"test\")","timeout":5}'
```

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd goblin-assistant

# Install dependencies
pip install -r requirements.txt
npm install

# Run tests
python test_sandbox_integration.py

# Start development environment
docker-compose -f docker-compose.dev.yml up
```

### Code Standards
- **Python**: Black formatting, type hints, comprehensive tests
- **TypeScript**: ESLint, Prettier, typed interfaces
- **Security**: Input validation, secure defaults, audit logging

## 📜 License

This sandbox implementation follows security best practices and is designed for production use. Ensure proper security review before deployment in sensitive environments.

## ⚠️ Security Notice

While this sandbox provides strong isolation, no system is completely secure. Regular security audits, dependency updates, and monitoring are essential for production deployments.