# Troubleshooting Guide

Comprehensive troubleshooting guide for common Goblin Assistant issues and their solutions.

## 🚀 Startup Issues

### Backend Won't Start

**Symptoms:**

- FastAPI server fails to start
- Port 8000 already in use
- Python dependency errors

**Solutions:**

1. **Check Python Version:**

   ```bash
   python --version  # Should be 3.11+
   ```

2. **Activate Virtual Environment:**

   ```bash
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Check Port Availability:**

   ```bash
   lsof -i :8000  # Linux/Mac
   netstat -ano | findstr :8000  # Windows
   ```

5. **Kill Conflicting Process:**

   ```bash
   kill -9 <PID>  # Linux/Mac
   # or use Task Manager on Windows
   ```

### Frontend Won't Load

**Symptoms:**

- Blank page or connection refused
- Vite dev server errors
- Node.js version issues

**Solutions:**

1. **Check Node.js Version:**

   ```bash
   node --version  # Should be 18+
   ```

2. **Clear Cache and Reinstall:**

   ```bash
   rm -rf node_modules/.vite
   npm install
   ```

3. **Try Different Port:**

   ```bash
   npm run dev -- --port 3000
   ```

4. **Check Firewall:**
   - Ensure port 5173 is not blocked
   - Try disabling firewall temporarily

## 🔑 Provider Configuration Issues

### API Key Problems

**Symptoms:**

- "Invalid API key" errors
- Authentication failures
- Provider shows as disabled

**Solutions:**

1. **Verify API Key Format:**

   ```bash
   # OpenAI keys start with 'sk-'
   # Anthropic keys start with 'sk-ant-'
   # Check provider documentation for format
   ```

2. **Environment Variables:**

   ```bash
   export OPENAI_API_KEY="sk-your-key-here"
   export ANTHROPIC_API_KEY="sk-ant-your-key-here"
   ```

3. **TOML Configuration:**

   ```toml
   [openai]
   api_key = "${OPENAI_API_KEY}"
   enabled = true
   ```

4. **Key Permissions:**
   - Ensure API key has correct permissions
   - Check account billing status
   - Verify rate limits not exceeded

### Provider Connectivity

**Symptoms:**

- Timeout errors
- Network connection failed
- DNS resolution issues

**Solutions:**

1. **Test Connectivity:**

   ```bash
   curl -I https://api.openai.com/v1/models
   curl -I https://api.anthropic.com/v1/messages
   ```

2. **Check DNS:**

   ```bash
   nslookup api.openai.com
   ```

3. **Proxy Configuration:**

   ```toml
   [openai]
   proxy_url = "http://proxy.company.com:8080"
   ```

4. **Firewall/VPN Issues:**
   - Try without VPN
   - Check corporate firewall rules
   - Use different network

## 🏠 Local AI Issues

### Ollama Problems

**Symptoms:**

- Ollama service not running
- Model download failures
- Local model not responding

**Solutions:**

1. **Start Ollama Service:**

   ```bash
   ollama serve
   ```

2. **Check Service Status:**

   ```bash
   curl http://localhost:11434/api/tags
   ```

3. **Pull Models:**

   ```bash
   ollama pull llama2:7b-chat
   ollama pull codellama:7b
   ```

4. **Free Disk Space:**

   ```bash
   df -h  # Linux/Mac
   # Check available space (>10GB needed)
   ```

5. **Restart Service:**

   ```bash
   pkill ollama
   ollama serve
   ```

### LM Studio Issues

**Symptoms:**

- Local server not accessible
- Model loading failures
- Port conflicts

**Solutions:**

1. **Check LM Studio Settings:**
   - Ensure local server is enabled
   - Verify port 1234 is available
   - Check model is loaded

2. **Configuration:**

   ```toml
   [lmstudio]
   enabled = true
   base_url = "http://localhost:1234"
   ```

3. **Test Connection:**

   ```bash
   curl http://localhost:1234/v1/models
   ```

## 💰 Cost and Budget Issues

### Unexpected Costs

**Symptoms:**

- Higher than expected spending
- Budget alerts triggering
- Cost tracking not working

**Solutions:**

1. **Check Budget Settings:**

   ```toml
   [budget]
   hourly_limit = 10.0
   daily_limit = 50.0
   ```

2. **Monitor Usage:**
   - Check the cost tracker in UI
   - Review provider usage logs
   - Identify expensive operations

3. **Optimize Provider Selection:**

   ```toml
   [openai.gpt-3.5-turbo]
   cost_weight = 0.8  # Prefer cheaper option
   ```

4. **Use Local Models:**

   ```toml
   [ollama.llama2:7b]
   cost_weight = 1.0  # Free
   ```

### Rate Limiting

**Symptoms:**

- "Rate limit exceeded" errors
- Requests being throttled
- Service unavailable temporarily

**Solutions:**

1. **Check Rate Limits:**
   - OpenAI: 60 RPM, 40K TPM
   - Anthropic: Varies by tier
   - Check provider dashboard

2. **Implement Backoff:**

   ```toml
   [openai]
   requests_per_minute = 50
   tokens_per_minute = 35000
   ```

3. **Use Multiple Providers:**
   - Distribute load across providers
   - Enable failover to less busy providers

## 🔄 Workflow Issues

### Workflow Not Executing

**Symptoms:**

- Workflow appears stuck
- Steps not progressing
- Timeout errors

**Solutions:**

1. **Check Syntax:**

   ```text
   # Correct
   task1 THEN task2 THEN task3

   # Incorrect
   task1 THEN task2 THEN
   ```

2. **Provider Availability:**
   - Ensure providers are enabled
   - Check API keys are valid
   - Verify network connectivity

3. **Step Dependencies:**
   - Some steps may require previous results
   - Check for circular dependencies

### Conditional Logic Problems

**Symptoms:**

- IF_SUCCESS/IF_FAILURE not working
- Wrong branch executing
- Logic evaluation issues

**Solutions:**

1. **Check Success Criteria:**
   - Define what constitutes "success"
   - Review error handling logic

2. **Debug Mode:**

   ```toml
   [debug]
   workflow_tracing = true
   log_step_details = true
   ```

3. **Test Individual Steps:**
   - Run steps separately first
   - Verify each step works independently

## 📊 Performance Issues

### Slow Responses

**Symptoms:**

- High latency
- Delayed responses
- Timeout errors

**Solutions:**

1. **Optimize Provider Selection:**

   ```toml
   [openai.gpt-3.5-turbo]
   latency_weight = 0.7  # Favor speed
   ```

2. **Check Network:**

   ```bash
   ping api.openai.com
   ```

3. **Reduce Token Limits:**

   ```toml
   [openai.gpt-4]
   max_tokens = 2048  # Smaller for faster responses
   ```

4. **Use Streaming:**
   - Enable streaming for better perceived performance
   - Process responses as they arrive

### High Memory Usage

**Symptoms:**

- Application becomes slow
- Out of memory errors
- System performance degraded

**Solutions:**

1. **Monitor Resources:**

   ```bash
   top  # Linux/Mac
   # or Task Manager on Windows
   ```

2. **Limit Concurrent Requests:**

   ```toml
   [scaling]
   concurrent_requests = 5
   ```

3. **Clear Cache:**

   ```bash
   rm -rf node_modules/.vite
   npm run build
   ```

## 🔧 Configuration Issues

### TOML Syntax Errors

**Symptoms:**

- Configuration not loading
- "Invalid TOML" errors
- Settings not applying

**Solutions:**

1. **Validate Syntax:**

   ```bash
   python -c "import tomllib; tomllib.load(open('config/providers.toml', 'rb'))"
   ```

2. **Common Mistakes:**

   ```toml
   # Correct
   [openai]
   api_key = "sk-key"

   # Incorrect
   [openai]
   api_key = sk-key  # Missing quotes
   ```

3. **Use TOML Validator:**
   - Online validators
   - IDE extensions
   - Command line tools

### Environment Variables

**Symptoms:**

- Variables not resolving
- Configuration shows `${VAR_NAME}`
- Values not substituted

**Solutions:**

1. **Check Variable Export:**

   ```bash
   echo $OPENAI_API_KEY
   export OPENAI_API_KEY="sk-your-key"
   ```

2. **Shell Configuration:**

   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export OPENAI_API_KEY="sk-your-key"
   ```

3. **Restart Application:**
   - Environment variables load on startup
   - Restart both backend and frontend

## 🐛 Debugging Tools

### Enable Debug Logging

```toml
[logging]
level = "DEBUG"
file = "logs/goblin_assistant.log"
console = true
```

### Test Commands

```bash
# Test backend health
curl http://localhost:8000/health

# Test provider connectivity
python -c "from goblin_assistant.providers import test_provider; test_provider('openai')"

# Validate configuration
python -m goblin_assistant.validate_config config/providers.toml
```

### Performance Profiling

```bash
# Profile Python performance
python -m cProfile api/fastapi/app.py

# Monitor network requests
# Use browser dev tools or tools like mitmproxy
```

## 🚨 Critical Issues

### Data Loss

**Symptoms:**

- Configuration lost
- Metrics/history missing
- SQLite database corrupted

**Solutions:**

1. **Backup Configuration:**

   ```bash
   cp config/providers.toml config/providers.toml.backup
   ```

2. **Database Recovery:**

   ```bash
   sqlite3 metrics.db .dump > backup.sql
   sqlite3 new_metrics.db < backup.sql
   ```

3. **Version Control:**
   - Commit configuration changes
   - Use git for version control
   - Keep backups of important data

### Security Issues

**Symptoms:**

- API keys exposed
- Unauthorized access
- Suspicious activity

**Solutions:**

1. **Rotate Keys:**

   ```bash
   # Generate new API keys
   # Update configuration
   # Revoke old keys
   ```

2. **Check Logs:**

   ```bash
   grep "unauthorized" logs/*.log
   ```

3. **Security Audit:**
   - Review access logs
   - Check file permissions
   - Update dependencies

## 📞 Getting Help

### Community Support

- **GitHub Issues:** [Report bugs](https://github.com/fuaadabdullah/goblin-assistant/issues)
- **Discussions:** [Ask questions](https://github.com/fuaadabdullah/goblin-assistant/discussions)
- **Discord:** Join our community server

### Emergency Contacts

- **Security Issues:** `security@goblin-assistant.dev`
- **Critical Bugs:** Report immediately on GitHub
- **General Help:** Community discussions

### Diagnostic Information

When reporting issues, include:

```bash
# System information
uname -a
python --version
node --version
npm --version

# Application logs
tail -n 50 logs/goblin_assistant.log

# Configuration (redact sensitive info)
cat config/providers.toml | grep -v api_key
```

---

*Still having issues? Check the [FAQ](../README.md#faq) or create a [new issue](https://github.com/fuaadabdullah/goblin-assistant/issues) with detailed information.*
