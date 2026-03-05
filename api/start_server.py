#!/usr/bin/env python
import uvicorn
import os

# Set PYTHONPATH
os.environ["PYTHONPATH"] = (
    "/Users/fuaadabdullah/ForgeMonorepo/apps/goblin-assistant/backend"
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, log_level="info")
