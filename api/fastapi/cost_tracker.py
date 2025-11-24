"""
Cost tracking and estimation for LLM provider calls.
Tracks token usage and estimates costs based on provider pricing.
"""

import os
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from metrics import metrics

@dataclass
class ProviderPricing:
    """Pricing information for an LLM provider."""
    input_tokens_per_dollar: float  # tokens per dollar for input
    output_tokens_per_dollar: float  # tokens per dollar for output
    model_name: str

class CostTracker:
    """Tracks and estimates costs for LLM API calls."""

    def __init__(self):
        # Pricing data (as of 2025 - update as needed)
        self.pricing: Dict[str, ProviderPricing] = {
            "openai": {
                "gpt-4o": ProviderPricing(25000, 100000, "gpt-4o"),  # $0.00004/input, $0.0001/output
                "gpt-4o-mini": ProviderPricing(150000, 600000, "gpt-4o-mini"),  # $0.00000667/input, $0.00001667/output
                "gpt-4-turbo": ProviderPricing(30000, 100000, "gpt-4-turbo"),
                "gpt-4": ProviderPricing(12500, 25000, "gpt-4"),
                "gpt-3.5-turbo": ProviderPricing(500000, 1666667, "gpt-3.5-turbo"),  # $0.000002/input, $0.000006/output
            },
            "anthropic": {
                "claude-3-5-sonnet": ProviderPricing(200000, 800000, "claude-3-5-sonnet"),  # $0.000005/input, $0.000015/output
                "claude-3-haiku": ProviderPricing(250000, 1250000, "claude-3-haiku"),  # $0.000004/input, $0.000012/output
                "claude-3-opus": ProviderPricing(15000, 75000, "claude-3-opus"),
            },
            "google": {
                "gemini-pro": ProviderPricing(125000, 357143, "gemini-pro"),  # $0.000008/input, $0.000028/output
                "gemini-flash": ProviderPricing(150000, 500000, "gemini-flash"),
            },
            "ollama": {
                "llama3.2": ProviderPricing(float('inf'), float('inf'), "llama3.2"),  # Local, no cost
                "llama3": ProviderPricing(float('inf'), float('inf'), "llama3"),
                "mistral": ProviderPricing(float('inf'), float('inf'), "mistral"),
            },
            "llama_cpp": {
                "default": ProviderPricing(float('inf'), float('inf'), "default"),  # Local, no cost
            },
            "cloudflare": {
                "workers-ai": ProviderPricing(1000000, 1000000, "workers-ai"),  # $0.000001/input+output
            }
        }

        # Daily cost tracking
        self.daily_costs: Dict[str, float] = {}
        self.daily_tokens: Dict[str, int] = {}

    def get_pricing(self, provider: str, model: str) -> Optional[ProviderPricing]:
        """Get pricing information for a provider/model combination."""
        provider_pricing = self.pricing.get(provider.lower(), {})
        return provider_pricing.get(model.lower())

    def estimate_cost(self, provider: str, model: str, input_tokens: int = 0, output_tokens: int = 0) -> float:
        """
        Estimate cost for a call based on token usage.

        Args:
            provider: Provider name (openai, anthropic, etc.)
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        pricing = self.get_pricing(provider, model)
        if not pricing:
            # Unknown provider/model, return 0 and log
            metrics.increment_counter("cost_tracking.unknown_provider", tags={
                "provider": provider,
                "model": model
            })
            return 0.0

        # For local models (ollama, llama_cpp), cost is 0
        if pricing.input_tokens_per_dollar == float('inf'):
            return 0.0

        # Calculate cost
        input_cost = input_tokens / pricing.input_tokens_per_dollar
        output_cost = output_tokens / pricing.output_tokens_per_dollar
        total_cost = input_cost + output_cost

        return total_cost

    def track_call(self, provider: str, model: str, input_tokens: int = 0,
                  output_tokens: int = 0, actual_cost: Optional[float] = None) -> float:
        """
        Track a call and update metrics.

        Args:
            provider: Provider name
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            actual_cost: Actual cost if known (overrides estimation)

        Returns:
            Cost used for tracking (actual or estimated)
        """
        # Determine cost
        if actual_cost is not None:
            cost = actual_cost
        else:
            cost = self.estimate_cost(provider, model, input_tokens, output_tokens)

        # Update daily totals
        today = datetime.utcnow().date().isoformat()
        self.daily_costs[today] = self.daily_costs.get(today, 0.0) + cost
        self.daily_tokens[today] = self.daily_tokens.get(today, 0) + input_tokens + output_tokens

        # Emit metrics
        metrics.gauge("llm.cost_estimate_usd", cost, tags={
            "provider": provider,
            "model": model
        })

        total_tokens = input_tokens + output_tokens
        if total_tokens > 0:
            metrics.gauge("llm.tokens", total_tokens, tags={
                "provider": provider,
                "model": model
            })

        # Daily rollup metrics
        metrics.gauge("daily.cost_total_usd", self.daily_costs[today], tags={
            "date": today
        })
        metrics.gauge("daily.tokens_total", self.daily_tokens[today], tags={
            "date": today
        })

        return cost

    def get_daily_summary(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get daily cost and token summary."""
        if date is None:
            date = datetime.utcnow().date().isoformat()

        return {
            "date": date,
            "total_cost_usd": self.daily_costs.get(date, 0.0),
            "total_tokens": self.daily_tokens.get(date, 0),
            "providers_used": len(set()),  # Would need to track per provider
        }

    def check_budget_alert(self, daily_budget_usd: float = 10.0) -> bool:
        """Check if daily budget is exceeded."""
        today = datetime.utcnow().date().isoformat()
        current_cost = self.daily_costs.get(today, 0.0)

        if current_cost > daily_budget_usd:
            metrics.increment_counter("budget.exceeded", tags={
                "budget_usd": str(daily_budget_usd),
                "current_cost_usd": str(current_cost)
            })
            return True

        return False


# Global cost tracker instance
cost_tracker = CostTracker()
