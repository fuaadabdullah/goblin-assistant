# Quick Start Guide: AI Provider Testing & Benchmarking

## Testing Local LLM Deployments

Check if your local LLM servers are up and running:

```bash
cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant
python3 test_local_llms.py
```

This will test:
- Ollama GCP (primary)
- LlamaCPP GCP
- Ollama Kamatera (legacy)
- LlamaCPP Kamatera (legacy)

## Running Provider Benchmarks

Test all configured AI providers for latency, throughput, and quality:

```bash
cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant
python3 benchmark_providers.py
```

Results are saved to `benchmark_results.json`

## Setting Up SiliconeFlow

1. Get API key from https://siliconflow.cn
2. Add to your environment:

```bash
export SILICONEFLOW_API_KEY="your_key_here"
```

3. Test it:

```bash
python3 benchmark_providers.py
```

## Using Providers in Code

```python
from api.providers.dispatcher_fixed import ProviderDispatcher

# Initialize dispatcher
dispatcher = ProviderDispatcher()

# Get specific provider
provider = dispatcher.get_provider("siliconeflow")

# Make inference request
result = await provider.invoke(
    prompt="Your question here",
    model="Qwen/Qwen2.5-7B-Instruct",
    stream=False,
    max_tokens=100
)

if result.get("ok"):
    print(result.get("text"))
```

## Provider Priority Order

When auto-selecting, providers are tried in this order:

1. OpenAI (if OPENAI_API_KEY set)
2. Anthropic (if ANTHROPIC_API_KEY set)
3. Groq (if GROQ_API_KEY set)
4. **SiliconeFlow** (if SILICONEFLOW_API_KEY set) ← NEW
5. Google/Gemini (if GOOGLE_API_KEY set)
6. Ollama GCP (if OLLAMA_GCP_URL set)
7. LlamaCPP GCP (if LLAMACPP_GCP_URL set)
8. Local Ollama (localhost)

## Current Working Providers

✅ **Ollama GCP** - http://34.60.255.199:11434
- Status: Working
- Average latency: ~8.7s (needs optimization)
- Models: qwen2.5:latest, phi3:latest, gemma2:latest

⚠️ Other providers need API keys configured

## Troubleshooting

### "Invalid API key" errors
- Check your .env file has correct keys
- Verify keys are not expired
- Make sure no extra spaces in key values

### "Connection refused" errors
- Check if server is running
- Verify firewall allows traffic
- Test with curl: `curl http://server:port/health`

### Slow responses
- Check server resources (CPU, memory)
- Consider using smaller models
- Enable GPU acceleration if available

## Files Created

- `test_local_llms.py` - Deployment verification script
- `benchmark_providers.py` - Comprehensive benchmark suite
- `AI_PROVIDER_INTEGRATION_REPORT.md` - Full implementation report
- `api/providers/siliconeflow.py` - SiliconeFlow provider implementation

## Next Steps

1. Configure missing API keys
2. Optimize Ollama GCP performance (target < 1s latency)
3. Fix LlamaCPP GCP connectivity
4. Set up monitoring and alerts
5. Implement caching for common queries
