#!/bin/bash
# Start the canonical FastAPI backend in the api directory
cd /Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant/api
exec uvicorn main:app --host 0.0.0.0 --port 8000
