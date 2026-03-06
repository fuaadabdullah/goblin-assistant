#!/bin/bash

# Start Goblin Assistant Backend with GCP LLM configuration

cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant

# GCP LLM env vars removed - VMs terminated since 2026-01-11
# Re-add OLLAMA_GCP_URL / LLAMACPP_GCP_URL after redeploying GCP infra

# Start the server
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8004
