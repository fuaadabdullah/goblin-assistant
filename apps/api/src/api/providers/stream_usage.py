"""Stream usage totals with explicit estimates when providers omit usage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base import BaseProvider

from .quota_pkg.estimation import estimate_text_tokens


class StreamUsage:
    def __init__(self, messages: list[dict[str, Any]], prompt: str = "") -> None:
        self.input_estimate = estimate_text_tokens(prompt) + sum(
            estimate_text_tokens(str(message.get("content", ""))) for message in messages
        )
        self.output_chars = 0
        self.usage: dict[str, Any] = {}
        self.cost: float | None = None

    def update(self, chunk: Any) -> None:
        if not isinstance(chunk, dict):
            self.output_chars += len(str(chunk))
            return
        self.output_chars += len(chunk.get("text", "") or "")
        if isinstance(chunk.get("usage"), dict):
            self.usage.update(chunk["usage"])
        if isinstance(chunk.get("cost_usd"), (int, float)):
            self.cost = chunk["cost_usd"]

    def tokens(self) -> tuple[int, int]:
        return (
            int(
                self.usage.get("prompt_tokens", self.usage.get("input_tokens", self.input_estimate))
            ),
            int(
                self.usage.get(
                    "completion_tokens",
                    self.usage.get("output_tokens", (self.output_chars + 3) // 4),
                )
            ),
        )

    def summary(self, provider: BaseProvider, model: str) -> dict[str, Any]:
        input_tokens, output_tokens = self.tokens()
        return {
            "usage": {"prompt_tokens": input_tokens, "completion_tokens": output_tokens},
            "usage_estimated": not (
                any(key in self.usage for key in ("prompt_tokens", "input_tokens"))
                and any(key in self.usage for key in ("completion_tokens", "output_tokens"))
            ),
            "cost_usd": self.cost
            if self.cost is not None
            else provider.estimate_cost(input_tokens, output_tokens, model),
            "cost_estimated": self.cost is None,
        }
