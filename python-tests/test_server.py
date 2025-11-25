#!/usr/bin/env python3
"""
Simple test server for Goblin Assistant Continue integration.
Tests basic functionality without complex dependencies.
"""

import os
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys

# Add the goblinos package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value


class GoblinTestHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for testing Goblin Assistant endpoints."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"status": "healthy", "service": "goblin-assistant-test"}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode())

        if self.path == "/continue/hook":
            # Test Continue integration
            response = self._handle_continue_hook(data)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        elif self.path == "/v1/chat/completions":
            # OpenAI-compatible chat completions endpoint
            response = self._handle_chat_completions(data)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        elif self.path == "/assistant/query":
            # Test assistant query
            response = self._handle_assistant_query(data)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        else:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())

    def _handle_continue_hook(self, data):
        """Handle Continue IDE hook."""
        print(f"📥 Continue hook received: {data}")

        # Simple response for testing
        return {
            "success": True,
            "message": "Continue hook received",
            "data": data,
            "api_keys_configured": {
                "openai": bool(os.getenv("OPENAI_API_KEY")),
                "admin": bool(os.getenv("OPENAI_ADMIN_KEY")),
                "service": bool(os.getenv("OPENAI_SERVICE_KEY")),
            },
        }

    def _handle_chat_completions(self, data):
        """Handle OpenAI-compatible chat completions."""
        print(f"📥 Chat completions request: {data}")

        messages = data.get("messages", [])
        if not messages:
            return {"error": "No messages provided"}

        # Get the last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        # Mock response in OpenAI format
        return {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "goblin-assistant",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Goblin Assistant here! You said: '{user_message}'. This is a mock response from your custom backend. API keys configured: {bool(os.getenv('OPENAI_API_KEY'))}",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": 50,
                "total_tokens": len(user_message.split()) + 50,
            },
        }

    def _handle_assistant_query(self, data):
        """Handle assistant query."""
        print(f"📥 Assistant query received: {data}")

        query = data.get("query", "")
        user_id = data.get("user_id", "anonymous")

        # Simple mock response
        return {
            "answer": f'Mock response to: "{query}"',
            "contexts": [],
            "usage": {"tokens": 100},
            "hit_rate": 0.0,
            "provider": "mock",
            "model": "test-model",
            "user_id": user_id,
        }

    def log_message(self, format, *args):
        """Override to use print instead of stderr."""
        print(f"[HTTP] {format % args}")


def run_test_server(port=3001):
    """Run the test server."""
    server_address = ("", port)
    httpd = HTTPServer(server_address, GoblinTestHandler)

    print(f"🚀 Goblin Assistant Test Server running on port {port}")
    print("📡 Test endpoints:")
    print(f"   GET  http://localhost:{port}/health")
    print(f"   POST http://localhost:{port}/continue/hook")
    print(f"   POST http://localhost:{port}/v1/chat/completions (OpenAI-compatible)")
    print(f"   POST http://localhost:{port}/assistant/query")
    print(f"🔑 API Keys configured: {bool(os.getenv('OPENAI_API_KEY'))}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        httpd.shutdown()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3001))
    run_test_server(port)
