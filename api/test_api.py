#!/usr/bin/env python3
import requests
import json
import time

# Give the server time to start
time.sleep(2)

try:
    response = requests.get("http://127.0.0.1:5000/settings/api-keys/status", timeout=5)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("API Key Status:")
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.text}")
except requests.exceptions.Timeout:
    print("Request timed out")
except Exception as e:
    print(f"Connection error: {e}")
