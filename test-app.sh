#!/bin/bash
# Test script to start the app and test endpoints

cd /Users/fuaadabdullah/ForgeMonorepo/goblin-assistant

# Start the app in background
PYTHONPATH=/Users/fuaadabdullah/ForgeMonorepo/goblin-assistant:/Users/fuaadabdullah/ForgeMonorepo/goblin-assistant/api/fastapi /usr/local/opt/python@3.14/bin/python3.14 minimal-app.py &
APP_PID=$!

# Wait for app to start
sleep 3

# Test endpoints
echo "Testing health endpoint..."
curl -s -X GET "http://localhost:8001/health"

echo -e "\n\nTesting invoke endpoint..."
curl -s -X POST "http://localhost:8001/invoke" -H "Content-Type: application/json" -d '{"prompt": "Hello, test LLM call", "provider": "openai", "model": "gpt-3.5-turbo"}'

echo -e "\n\nTesting metrics endpoint..."
curl -s -X GET "http://localhost:8001/metrics"

echo -e "\n\nStopping app..."
kill $APP_PID

echo "Test completed!"
