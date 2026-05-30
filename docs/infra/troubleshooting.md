# Troubleshooting

## Common Issues and Solutions

This guide covers frequently encountered issues and their solutions when working with GoblinOS Assistant.

## Installation Issues

### Python Version Compatibility

**Problem**: `pip install` fails with Python version errors.

**Solution**:
```bash
# Check Python version
python --version

# Use Python 3.11+ for best compatibility
python3.11 -m pip install -r requirements.txt
```

**Prevention**: Always use Python 3.11 or higher as specified in requirements.

### Node.js Dependencies

**Problem**: `npm install` fails or hangs.

**Solution**:
```bash
# Clear npm cache
npm cache clean --force

# Use specific Node.js version (18+ recommended)
node --version

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Environment Variables

**Problem**: Application fails to start due to missing environment variables.

**Solution**:
```bash
# Check for required .env files
ls -la backend/.env*

# Copy from template if missing
cp backend/.env.example backend/.env.local

# Validate environment loading
cd backend && python -c "import os; print(os.getenv('DATABASE_URL'))"
```

## Runtime Issues

### Database Connection Errors

**Problem**: `sqlite3.OperationalError: unable to open database file`

**Solutions**:

1. **Check file permissions**:
   ```bash
   ls -la goblin_assistant.db
   chmod 664 goblin_assistant.db
   ```

2. **Check database path**:
   ```bash
   # Ensure correct path in .env
   DATABASE_URL=sqlite:///./goblin_assistant.db
   ```

3. **Reset database** (development only):
   ```bash
   rm goblin_assistant.db
   alembic upgrade head
   ```

### API Key Authentication

**Problem**: `401 Unauthorized` errors when calling AI providers.

**Solutions**:

1. **Verify API keys**:
   ```bash
   # Check environment variables
   echo $OPENAI_API_KEY | head -c 10  # Should show sk-...
   ```

2. **Test API key validity**:
   ```bash
   curl -H "Authorization: Bearer $OPENAI_API_KEY" \
        https://api.openai.com/v1/models
   ```

3. **Check key format**:
   - OpenAI: `sk-...`
   - Anthropic: `sk-ant-...`
   - DeepSeek: `sk-...`

### Model Routing Failures

**Problem**: Requests fail with routing errors.

**Solutions**:

1. **Check provider health**:
   ```bash
   curl http://localhost:8000/v1/health/provider-status
   ```

2. **Verify routing configuration**:
   ```bash
   # Check routing settings in database
   sqlite3 goblin_assistant.db "SELECT * FROM routing_config;"
   ```

3. **Test individual providers**:
   ```bash
   # Test OpenAI directly
   curl -X POST http://localhost:8000/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}]}'
   ```

## Frontend Issues

### Build Failures

**Problem**: `npm run build` fails with TypeScript errors.

**Solutions**:

1. **Check TypeScript configuration**:
   ```bash
   npx tsc --noEmit
   ```

2. **Clear build cache**:
   ```bash
   rm -rf .next
   npm run build
   ```

3. **Update dependencies**:
   ```bash
   npm update
   ```

### Development Server Issues

**Problem**: `npm run dev` fails to start or crashes.

**Solutions**:

1. **Check port availability**:
   ```bash
   lsof -i :3000
   kill -9 <PID>
   ```

2. **Clear node modules**:
   ```bash
   rm -rf node_modules .next
   npm install
   npm run dev
   ```

3. **Check environment variables**:
   ```bash
   # Ensure VITE_API_BASE_URL is set
   grep VITE_API_BASE_URL .env.local
   ```

## Performance Issues

### Slow Response Times

**Problem**: API responses are slower than expected.

**Solutions**:

1. **Check system resources**:
   ```bash
   # Monitor CPU/memory usage
   top -p $(pgrep -f "uvicorn\|node")
   ```

2. **Enable caching**:
   ```bash
   # Check Redis connection
   redis-cli ping
   ```

3. **Profile application**:
   ```bash
   # Use py-spy for Python profiling
   pip install py-spy
   py-spy top --pid $(pgrep -f uvicorn)
   ```

### Memory Leaks

**Problem**: Application memory usage grows over time.

**Solutions**:

1. **Monitor memory usage**:
   ```bash
   # Check process memory
   ps aux --sort=-%mem | head
   ```

2. **Enable garbage collection logging**:
   ```python
   # Add to main.py
   import gc
   gc.set_debug(gc.DEBUG_STATS)
   ```

3. **Check for object retention**:
   ```bash
   # Use memory_profiler
   pip install memory-profiler
   python -m memory_profiler main.py
   ```

## Networking Issues

### CORS Errors

**Problem**: Browser blocks requests with CORS errors.

**Solutions**:

1. **Check CORS configuration**:
   ```python
   # In FastAPI app
   from fastapi.middleware.cors import CORSMiddleware

   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. **Verify frontend configuration**:
   ```bash
   # Check VITE_API_BASE_URL
   grep VITE_API_BASE_URL .env.local
   ```

### Connection Timeouts

**Problem**: Requests timeout when calling external APIs.

**Solutions**:

1. **Increase timeout settings**:
   ```python
   # In HTTP client configuration
   timeout = httpx.Timeout(30.0, connect=10.0)
   ```

2. **Check network connectivity**:
   ```bash
   # Test external connectivity
   curl -I https://api.openai.com
   ```

3. **Use retry logic**:
   ```python
   # Implement exponential backoff
   import asyncio
   from tenacity import retry, stop_after_attempt, wait_exponential
   ```

## Deployment Issues

### Docker Build Failures

**Problem**: `docker build` fails during deployment.

**Solutions**:

1. **Check build context**:
   ```bash
   # Ensure .dockerignore is correct
   cat .dockerignore
   ```

2. **Build with no cache**:
   ```bash
   docker build --no-cache -t goblin-assistant .
   ```

3. **Check build logs**:
   ```bash
   docker build -t goblin-assistant . 2>&1 | tee build.log
   ```

### Fly.io Deployment Issues

**Problem**: Fly.io deployment fails.

**Solutions**:

1. **Check Fly.io configuration**:
   ```bash
   fly config validate
   ```

2. **Monitor deployment logs**:
   ```bash
   fly logs --instance <instance-id>
   ```

3. **Check resource limits**:
   ```bash
   fly scale show
   ```

## Monitoring and Debugging

### Health Check Failures

**Problem**: Health endpoints return errors.

**Solutions**:

1. **Check individual services**:
   ```bash
   curl http://localhost:8000/v1/health/database
   curl http://localhost:8000/v1/health/vector-store
   ```

2. **Review logs**:
   ```bash
   # Check application logs
   tail -f logs/app.log
   ```

3. **Test dependencies**:
   ```bash
   # Test database connectivity
   python -c "import sqlite3; sqlite3.connect('goblin_assistant.db')"
   ```

### Log Analysis

**Problem**: Unable to debug issues from logs.

**Solutions**:

1. **Increase log verbosity**:
   ```bash
   # Set environment variable
   export LOG_LEVEL=DEBUG
   ```

2. **Search for specific errors**:
   ```bash
   grep "ERROR" logs/app.log | tail -10
   ```

3. **Use structured logging**:
   ```python
   import logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   ```

## Security Issues

### API Key Exposure

**Problem**: API keys accidentally committed or exposed.

**Solutions**:

1. **Rotate compromised keys**:
   ```bash
   # Generate new keys immediately
   # Update all environments
   ```

2. **Check for exposed keys**:
   ```bash
   # Use git-secrets or similar tools
   git log --all --grep="sk-" --oneline
   ```

3. **Use secret management**:
   ```bash
   # Implement proper secret storage
   # Use Bitwarden or similar for development
   ```

### Authentication Failures

**Problem**: Users unable to authenticate.

**Solutions**:

1. **Check JWT configuration**:
   ```bash
   # Verify JWT_SECRET_KEY
   echo $JWT_SECRET_KEY | wc -c  # Should be >32 chars
   ```

2. **Validate token format**:
   ```bash
   # Test token decoding
   python -c "import jwt; jwt.decode('<token>', options={'verify_signature': False})"
   ```

3. **Check session storage**:
   ```bash
   # Verify Redis connectivity for sessions
   redis-cli keys "session:*"
   ```

## Getting Help

### Community Support

- **GitHub Issues**: Search existing issues or create new ones
- **Documentation**: Check the docs folder for detailed guides
- **Discord**: Join our community server for real-time help

### Diagnostic Information

When reporting issues, please include:

```bash
# System information
uname -a
python --version
node --version
npm --version

# Application status
curl http://localhost:8000/health

# Recent logs
tail -50 logs/app.log

# Environment check
env | grep -E "(DATABASE|API_KEY|JWT)" | head -10
```

### Emergency Contacts

- **Security Issues**: `security@goblin-assistant.vercel.app`
- **Production Outages**: Check status page or contact on-call engineer
- **General Support**: Create GitHub issue with diagnostic information

This troubleshooting guide is continuously updated. If you encounter an issue not covered here, please contribute a solution by creating a pull request or opening an issue.
