# Quick Start Guide: AI Provider Testing & Benchmarking

For the full canonical provider mapping (Provider → env vars → default model → tier → active/visible/selectable), see:

- `docs/operations/PROVIDERS.md`

## Canonical Provider Matrix (Alias Clarification)

| Input name (what you may see) | Canonical provider ID | Backend implementation | Endpoint family | When to use |
| --- | --- | --- | --- | --- |
| `siliconeflow` | `siliconeflow` | `SiliconeFlowProvider` (extends `OpenAICompatibleProvider`) | `https://api.siliconflow.com/v1/chat/completions` | Use for low-cost chat/code routing when `SILICONEFLOW_API_KEY` is configured. |
| `siliconflow`, `silicon_flow`, `silicone-flow`, `silicone_flow` | `siliconeflow` | Same as above (normalized alias) | Same as above | Use only as compatibility input; prefer storing/logging `siliconeflow` as the canonical ID. |

Source of truth:

- Backend alias map: `config/providers.toml` under `[provider_aliases]`
- Backend provider config: `config/providers.toml` under `[providers.siliconeflow]`
- Frontend normalization: `apps/web/src/lib/providers/normalizeProvider.ts`

Operational guidance:

- `siliconeflow` is not a separate internal-only backend; it is the canonical provider ID used by this repo.
- If telemetry, settings, or health output shows a variant like `siliconflow`, normalize it to `siliconeflow` before debugging routing behavior.
- For runbooks and incident notes, always record the canonical ID `siliconeflow`.

## Testing Local LLM Deployments

Check if your local LLM servers are up and running:

```bash
cd /Volumes/GOBLINOS\ 1/goblin-assistant
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
cd /path/to/goblin-assistant
python3 benchmark_providers.py
```

Results are saved to `benchmark_results.json`

## Setting Up SiliconeFlow

1. Get API key from <https://siliconflow.cn>
2. Add to your environment:

```bash
export SILICONEFLOW_API_KEY="your_key_here"
```

1. Test it:

```bash
python3 benchmark_providers.py
```

## Setting Up Colab Worker (Disposable GPU)

Colab provider is canonical ID `colab_worker` with aliases `colab` / `colab-worker`.

1. Follow the runbook: `docs/operations/COLAB_WORKER.md`
2. Set backend env:

```bash
export COLAB_WORKER_ENDPOINT="https://abc123.ngrok.app"
export COLAB_WORKER_API_KEY="replace_with_long_random_token"
export COLAB_WORKER_HEARTBEAT_ENABLED=true
export COLAB_WORKER_HEARTBEAT_INTERVAL_SECONDS=60
```

3. Use provider explicitly when desired:

```python
result = await dispatcher.invoke_provider(
    provider_id="colab_worker",
    model="gemma-3-12b",  # or "qwen3-14b"
    payload={"messages": [{"role": "user", "content": "Explain options trading"}]},
)
```

Operational note:
- Do not store state in Colab. Keep persistence in Goblin storage (Postgres/memory/task state).

## Using Providers in Code

```python
from api.providers.dispatcher import ProviderDispatcher

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

`colab_worker` is intentionally opt-in and not part of default auto-routing baseline.

## Current Working Providers

✅ **Ollama GCP** - <http://34.60.255.199:11434>

- Status: Working
- Average latency: ~8.7s (needs optimization)
- Models: qwen2.5:latest, phi3:latest, gemma2:latest

⚠️ Other providers need API keys configured

## Troubleshooting

### Alias confusion (`siliconflow` vs `siliconeflow`)

- Expected behavior: both backend and frontend alias normalization resolve to `siliconeflow`.
- Verify backend alias table:
  - `rg -n "siliconflow|siliconeflow" config/providers.toml`
- Verify frontend alias table:
  - `rg -n "siliconflow|siliconeflow" apps/web/src/lib/providers/normalizeProvider.ts`
- Use canonical provider IDs when calling APIs or saving defaults.

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
