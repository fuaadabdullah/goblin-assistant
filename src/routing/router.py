import json
import time
import asyncio
import random
import os
import tomllib
from pathlib import Path
from typing import Dict, Any, List, Optional
from .invoke_provider_impl import invoke_provider

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "providers.toml"

# -------------------------
# Lightweight in-memory metrics & circuit state
METRICS: Dict[str, Dict[str, Any]] = {}
CB_STATE: Dict[str, Dict[str, Any]] = {}
COST_TRACKING: Dict[str, float] = {}  # Track costs per provider
BANDWIDTH_METRICS: Dict[str, List[float]] = {}  # Track tokens/sec per provider


def ensure_metrics(provider_id: str):
    METRICS.setdefault(
        provider_id, {"latencies": [], "succ": 0, "fail": 0, "tokens_per_sec": []}
    )


def record_latency(provider_id: str, ms: float):
    ensure_metrics(provider_id)
    METRICS[provider_id]["latencies"].append(ms)
    # keep tail small
    if len(METRICS[provider_id]["latencies"]) > 100:
        METRICS[provider_id]["latencies"].pop(0)


def record_success(provider_id: str):
    ensure_metrics(provider_id)
    METRICS[provider_id]["succ"] += 1


def record_fail(provider_id: str):
    ensure_metrics(provider_id)
    METRICS[provider_id]["fail"] += 1


def record_bandwidth(provider_id: str, tokens_per_sec: float):
    ensure_metrics(provider_id)
    BANDWIDTH_METRICS.setdefault(provider_id, []).append(tokens_per_sec)
    # keep tail small
    if len(BANDWIDTH_METRICS[provider_id]) > 50:
        BANDWIDTH_METRICS[provider_id].pop(0)


def record_cost(provider_id: str, cost: float):
    COST_TRACKING[provider_id] = COST_TRACKING.get(provider_id, 0) + cost


def moving_avg(latencies: List[float], n=8) -> Optional[float]:
    if not latencies:
        return None
    tail = latencies[-n:]
    return sum(tail) / len(tail)


def get_bandwidth_score(provider_id: str) -> float:
    """Get average tokens/sec for bandwidth scoring"""
    metrics = BANDWIDTH_METRICS.get(provider_id, [])
    if not metrics:
        return 0.5  # Default neutral score
    return sum(metrics) / len(metrics)


# -------------------------
# Load config
def load_config():
    with open(CONFIG_PATH, "rb") as f:
        raw = tomllib.load(f)
    return raw


CONFIG = load_config()
PROVIDERS = CONFIG["providers"]
DEFAULT_TIMEOUT_MS = CONFIG.get("default_timeout_ms", 12000)
SCORING_WEIGHTS = CONFIG.get(
    "scoring_weights",
    {"latency": 0.4, "cost": 0.3, "reliability": 0.2, "bandwidth": 0.1},
)
COT_SUPPRESSION = CONFIG.get("chain_of_thought_suppression", {})
COST_OPTIMIZATION = CONFIG.get("cost_optimization", {})


# -------------------------
# Circuit breaker helpers
def breaker_allows(pid: str) -> bool:
    st = CB_STATE.get(pid, {"fails": 0, "open_until": 0})
    if time.time() < st.get("open_until", 0):
        return False
    return True


def breaker_record_failure(pid: str, threshold=3, open_seconds=30):
    st = CB_STATE.setdefault(pid, {"fails": 0, "open_until": 0})
    st["fails"] += 1
    if st["fails"] >= threshold:
        st["open_until"] = time.time() + open_seconds
        st["fails"] = 0


def breaker_record_success(pid: str):
    CB_STATE.setdefault(pid, {"fails": 0, "open_until": 0})
    CB_STATE[pid]["fails"] = 0


# -------------------------
# Scoring (lower is better)
def score_provider(
    pid: str, capability: str, prefer_local: bool = False, prefer_cost: bool = False
) -> float:
    p = PROVIDERS[pid]
    if capability not in p.get("capabilities", []):
        return float("inf")

    # Base score components
    priority_score = p.get("priority_tier", 2) * 10.0
    cost_score = p.get("cost_score", 0.5)

    # Latency scoring
    lat = moving_avg(METRICS.get(pid, {}).get("latencies", [])) or (
        p.get("default_timeout_ms", DEFAULT_TIMEOUT_MS) / 2
    )
    latency_score = (lat / 1000.0) * 2.0

    # Reliability scoring
    succ = METRICS.get(pid, {}).get("succ", 0)
    fail = METRICS.get(pid, {}).get("fail", 0)
    total = succ + fail
    succ_rate = (succ / total) if total > 0 else 0.9
    reliability_multiplier = 1.0 - succ_rate * 0.45

    # Bandwidth scoring
    bandwidth_score = get_bandwidth_score(pid)
    configured_bandwidth = p.get("bandwidth_score", 0.5)
    bandwidth_combined = (bandwidth_score + configured_bandwidth) / 2

    # Cost optimization check
    current_hourly_cost = COST_TRACKING.get(pid, 0)
    max_budget = COST_OPTIMIZATION.get("max_budget_per_hour", 10.0)
    cost_over_limit = current_hourly_cost > max_budget

    if cost_over_limit and pid not in COST_OPTIMIZATION.get(
        "preferred_providers_under_budget", []
    ):
        # Penalize providers over budget (unless they're preferred budget providers)
        cost_score *= 2.0

    # Calculate weighted score
    weights = SCORING_WEIGHTS
    total_score = (
        priority_score
        + (cost_score * weights["cost"] * 5.0)
        + (latency_score * weights["latency"])
        + (reliability_multiplier * weights["reliability"] * 10.0)
        + (
            (1.0 - bandwidth_combined) * weights["bandwidth"] * 5.0
        )  # Invert bandwidth (higher is better)
    )

    # Preference modifiers
    if prefer_local and p.get("endpoint", "").startswith("http://127.0.0.1"):
        total_score *= 0.6
    if prefer_cost:
        total_score += cost_score * 10

    # Circuit breaker check
    if not breaker_allows(pid):
        total_score += 1000  # Heavy penalty for circuit-open providers

    # Add small jitter to prevent ties
    total_score += random.random() * 0.01

    return total_score


# -------------------------
# Chain-of-thought suppression logic
def should_suppress_cot(task_type: str, provider_id: str) -> tuple[bool, str]:
    """
    Determine if chain-of-thought should be suppressed for a task and provider.
    Returns (should_suppress, suppression_prompt)
    """
    p = PROVIDERS.get(provider_id, {})

    # Check if provider supports CoT suppression
    if not p.get("supports_cot", True):
        return False, ""  # Provider doesn't support CoT at all

    # Check global suppression rules
    suppress_for = COT_SUPPRESSION.get("suppress_for", [])
    force_for = COT_SUPPRESSION.get("force_for", [])

    if task_type in force_for:
        return False, ""  # Force CoT for complex tasks
    elif task_type in suppress_for:
        suppression_prompt = p.get(
            "cot_suppression_prompt", "Answer directly without showing your reasoning."
        )
        return True, suppression_prompt

    # Check provider-specific rules
    provider_rules = COT_SUPPRESSION.get("provider_rules", {})
    if provider_id in provider_rules:
        rule = provider_rules[provider_id]
        if rule.get("suppress_cot", False):
            suppression_prompt = rule.get(
                "suppression_prompt", "Be direct and concise."
            )
            return True, suppression_prompt

    # Default: don't suppress
    return False, ""


# -------------------------
# Provider invoke hook (REAL IMPLEMENTATION)


# -------------------------
# Main router
async def route_task(
    task_type: str,
    payload: Dict[str, Any],
    prefer_local: bool = False,
    prefer_cost: bool = False,
    max_retries: int = 2,
    stream: bool = False,
) -> Dict[str, Any]:
    """
    task_type e.g. "reasoning","chat","summary","code","embedding","image","search"
    """
    # filter candidates
    candidates = []
    for pid, p in PROVIDERS.items():
        if task_type not in p.get("capabilities", []):
            continue
        # Check if provider has required API key
        api_key_env = p.get("api_key_env")
        api_key_value = os.getenv(api_key_env) if api_key_env else None
        # Consider API key valid if it exists and doesn't look like a placeholder
        has_valid_api_key = bool(
            api_key_value
            and not api_key_value.startswith("your-")
            and not api_key_value.startswith("sk-1234567890")
        )
        print(
            f"DEBUG: Provider {pid}, api_key_env={api_key_env}, api_key_value={api_key_value[:20] if api_key_value else None}, has_valid_api_key={has_valid_api_key}"
        )
        if api_key_env and not has_valid_api_key:
            print(f"DEBUG: Skipping provider {pid} due to invalid/placeholder API key")
            continue  # Skip providers without valid API keys
        candidates.append(pid)

    print(f"DEBUG: Final candidates for {task_type}: {candidates}")

    if not candidates:
        return {
            "ok": False,
            "error": f"No providers with valid API keys for capability {task_type}",
        }
    # score
    scored = []
    for pid in candidates:
        if not breaker_allows(pid):
            continue
        s = score_provider(
            pid,
            capability=task_type,
            prefer_local=prefer_local,
            prefer_cost=prefer_cost,
        )
        scored.append((s, pid))
    if not scored:
        return {"ok": False, "error": "All providers circuit-open or none available"}
    scored.sort(key=lambda x: x[0])
    last_err = None
    # attempt providers in score order
    for _, pid in scored:
        p = PROVIDERS[pid]
        model = p.get("models", [None])[0] or "default"
        timeout = p.get("default_timeout_ms", DEFAULT_TIMEOUT_MS)

        # Apply chain-of-thought suppression if needed
        enhanced_payload = payload.copy()
        suppress_cot, cot_prompt = should_suppress_cot(task_type, pid)
        if suppress_cot and cot_prompt:
            if "messages" in enhanced_payload:
                # Add suppression instruction to the last user message
                last_message = enhanced_payload["messages"][-1]
                if last_message.get("role") == "user":
                    last_message["content"] = (
                        f"{cot_prompt}\n\n{last_message['content']}"
                    )
            elif "prompt" in enhanced_payload:
                enhanced_payload["prompt"] = (
                    f"{cot_prompt}\n\n{enhanced_payload['prompt']}"
                )

        # try with retries
        for attempt in range(max_retries + 1):
            try:
                t0 = time.time()
                res = await invoke_provider(
                    pid, model, enhanced_payload, timeout, stream=stream
                )
                took_ms = (time.time() - t0) * 1000
                record_latency(pid, took_ms)

                # Estimate cost and record it (rough approximation)
                estimated_cost = (
                    p.get("cost_score", 0.5) * 0.001
                )  # Rough cost per request
                record_cost(pid, estimated_cost)

                if not res.get("ok"):
                    record_fail(pid)
                    breaker_record_failure(pid)
                    last_err = res.get("error")
                    # backoff and retry
                    await asyncio.sleep(0.2 * (attempt + 1))
                    continue
                # success
                record_success(pid)
                breaker_record_success(pid)

                # Calculate tokens/sec for bandwidth tracking
                if "usage" in res.get("result", {}):
                    usage = res["result"]["usage"]
                    total_tokens = usage.get(
                        "total_tokens",
                        usage.get("completion_tokens", 0)
                        + usage.get("prompt_tokens", 0),
                    )
                    if total_tokens > 0 and took_ms > 0:
                        tokens_per_sec = (total_tokens / took_ms) * 1000
                        record_bandwidth(pid, tokens_per_sec)

                # Streaming case
                if stream and "stream" in res:
                    return {
                        "ok": True,
                        "provider": pid,
                        "model": model,
                        "stream": res["stream"],
                    }
                # Non-stream case
                return {
                    "ok": True,
                    "provider": pid,
                    "model": model,
                    "result": res["result"],
                    "latency_ms": took_ms,
                }
            except Exception as e:
                record_fail(pid)
                breaker_record_failure(pid)
                last_err = str(e)
                await asyncio.sleep(0.2 * (attempt + 1))
    # local fallback
    for pid, p in PROVIDERS.items():
        if p.get("endpoint", "").startswith("http://127.0.0.1") and task_type in p.get(
            "capabilities", []
        ):
            res = await invoke_provider(
                pid,
                p.get("models", [None])[0],
                payload,
                p.get("default_timeout_ms", DEFAULT_TIMEOUT_MS),
                stream=stream,
            )
            if res.get("ok"):
                # Streaming case
                if stream and "stream" in res:
                    return {
                        "ok": True,
                        "provider": pid,
                        "model": p.get("models", [None])[0],
                        "stream": res["stream"],
                    }
                # Non-stream case
                return {
                    "ok": True,
                    "provider": pid,
                    "model": p.get("models", [None])[0],
                    "result": res["result"],
                    "latency_ms": res.get("latency_ms"),
                }
    return {"ok": False, "error": last_err or "no-provider-available"}


# sync wrapper
def route_task_sync(*args, **kwargs):
    return asyncio.run(route_task(*args, **kwargs))


# quick helper to inspect top providers by current score
def top_providers_for(capability: str, prefer_local=False, prefer_cost=False, limit=6):
    items = []
    for pid in PROVIDERS:
        try:
            s = score_provider(
                pid, capability, prefer_local=prefer_local, prefer_cost=prefer_cost
            )
            if s != float("inf"):
                items.append((s, pid))
        except Exception:
            continue
    items.sort(key=lambda x: x[0])
    return [pid for _, pid in items[:limit]]
