"""
Bootstrap script: compute and persist intent prototype vectors.

For each of the 7 intent labels, embeds 8-10 canonical example prompts,
averages the vectors, L2-normalises, and writes to intent_prototypes.json
in the same directory.

Usage:
    python -m api.routing.build_intent_prototypes

Requires OPENAI_API_KEY or the project's configured embedding provider to be
available in the environment. The file is then bundled with the API service
and loaded by IntentClassifier at startup.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import sys
from typing import Dict, List

# ---------------------------------------------------------------------------
# Canonical exemplar prompts per intent label
# ---------------------------------------------------------------------------

EXEMPLARS: Dict[str, List[str]] = {
    "coding": [
        "Write a Python function that parses a JWT token and returns the payload.",
        "I'm getting a TypeError in my TypeScript code, can you help me debug it?",
        "Refactor this React component to use hooks instead of class syntax.",
        "Write unit tests for this authentication middleware.",
        "How do I implement a binary search tree in Go?",
        "Can you review this pull request and suggest improvements?",
        "Fix the SQL query — it's returning duplicate rows.",
        "Write a Dockerfile for a FastAPI application with a PostgreSQL dependency.",
        "What's wrong with this async function? It's not awaiting correctly.",
        "Implement rate limiting for this REST API endpoint.",
    ],
    "research": [
        "What does the research say about the long-term effects of intermittent fasting?",
        "Summarize the key findings from recent papers on transformer architectures.",
        "Give me an overview of quantum computing and its current limitations.",
        "What is the scientific consensus on CRISPR gene editing safety?",
        "Find and synthesize academic sources on the effects of social media on teenagers.",
        "Explain the main theories behind dark matter and dark energy.",
        "What are the latest developments in large language model alignment research?",
        "Background on the history and evolution of the internet.",
        "Compare and contrast different theories of consciousness.",
        "What are the state-of-the-art methods for protein structure prediction?",
    ],
    "creative": [
        "Write a short story about an astronaut who discovers a mysterious signal.",
        "Compose a poem about the passage of time using ocean imagery.",
        "Draft a blog post about the unexpected joys of slow travel.",
        "Write a screenplay scene where two old friends reunite after 20 years.",
        "Create a brand tagline for an eco-friendly sneaker company.",
        "Write lyrics for an indie folk song about moving to a new city.",
        "Give me a creative brief for a campaign that targets Gen Z readers.",
        "Help me develop the backstory for this fictional character.",
        "Write a haiku series about the four seasons.",
        "Draft an opening paragraph for a thriller novel set in 1980s Berlin.",
    ],
    "business": [
        "Help me write a go-to-market strategy for our new SaaS product.",
        "Create a pitch deck outline for a Series A raise.",
        "What should our OKRs be for Q3 given our growth targets?",
        "Analyze the competitive landscape for the HR tech space.",
        "Write an executive summary for our annual business review.",
        "Help me think through our pricing model — should we go freemium or direct sales?",
        "Draft a SWOT analysis for our expansion into the European market.",
        "How should we structure our hiring plan for a 50-person startup?",
        "What's the best way to communicate our pivot to existing customers?",
        "Review this product roadmap and identify gaps in the strategy.",
    ],
    "finance": [
        "What is the Value at Risk (VaR) of my portfolio given these positions?",
        "Explain the relationship between bond yields and equity valuations.",
        "How should I think about portfolio rebalancing given current volatility?",
        "Calculate the Sharpe ratio for this trading strategy.",
        "What are the key risks in going long on emerging market equities right now?",
        "Explain the mechanics of a covered call options strategy.",
        "Analyze this earnings report and what it means for the stock price.",
        "What's the difference between CVaR and VaR in risk management?",
        "How do I backtest a mean-reversion strategy in Python?",
        "What macro events should I be monitoring for my fixed income portfolio?",
    ],
    "reasoning": [
        "Help me think through whether I should take this new job offer.",
        "Walk me through the pros and cons of microservices vs monolith architecture.",
        "Is it logically consistent to support X but oppose Y? Analyze the argument.",
        "Think step by step: what are the second-order consequences of this policy?",
        "Help me evaluate these three options and choose the best one.",
        "Play devil's advocate — why might this strategy fail?",
        "What are the hidden assumptions in this argument?",
        "Reason from first principles: what would an ideal solution look like?",
        "Compare and contrast these two philosophical positions.",
        "What is the strongest counterargument to my thesis?",
    ],
    "agent_task": [
        "Fetch the latest data from this API and format it as a CSV.",
        "Automate the process of sending weekly summary emails to my team.",
        "Set up a cron job that runs this Python script every night at midnight.",
        "Scrape product prices from this website and store them in a database.",
        "Deploy this Docker container to our staging environment.",
        "Build a pipeline that ingests CSV files, transforms them, and loads to PostgreSQL.",
        "Loop through all files in this directory and rename them with today's date.",
        "Trigger a webhook whenever a new row is added to this Supabase table.",
        "Search the web for recent news about this company and summarize it.",
        "Execute this multi-step workflow: fetch → transform → validate → send.",
    ],
}


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def _mean_vector(vectors: List[List[float]]) -> List[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    result = [0.0] * dim
    for vec in vectors:
        for i, v in enumerate(vec):
            result[i] += v
    n = len(vectors)
    return [x / n for x in result]


async def build_prototypes() -> None:
    print("Building intent prototype vectors...")

    # Import the project's embedding service
    try:
        from api.services.embedding_service import EmbeddingService

        svc = EmbeddingService()
    except ImportError:
        print(
            "ERROR: Could not import EmbeddingService. Ensure you're running from the api package root.",
            file=sys.stderr,
        )
        sys.exit(1)

    prototypes: Dict[str, List[float]] = {}

    for label, exemplars in EXEMPLARS.items():
        print(f"  Embedding {len(exemplars)} exemplars for '{label}'...")
        vectors: List[List[float]] = []
        for text in exemplars:
            try:
                vec = await svc.embed_text(text)
                if vec and isinstance(vec, list):
                    vectors.append(vec)
            except Exception as exc:
                print(f"    WARNING: failed to embed exemplar '{text[:60]}...': {exc}")

        if not vectors:
            print(f"  SKIP: no vectors for '{label}'")
            continue

        prototype = _l2_normalize(_mean_vector(vectors))
        prototypes[label] = prototype
        print(f"  OK: {label} prototype dim={len(prototype)}")

    output_path = os.path.join(os.path.dirname(__file__), "intent_prototypes.json")
    with open(output_path, "w") as f:  # noqa: ASYNC230 — build script, sync I/O intentional
        json.dump(prototypes, f)

    print(f"\nWrote {len(prototypes)} prototype vectors to {output_path}")


if __name__ == "__main__":
    asyncio.run(build_prototypes())
