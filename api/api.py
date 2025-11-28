from flask import Flask, request, jsonify
import json

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({"status": "healthy", "message": "API is working!"})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


@app.route("/routing/providers")
def get_providers():
    return jsonify(["openai", "anthropic", "gemini"])


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    return jsonify(
        {
            "token": "mock_jwt_token",
            "user": {
                "id": "mock_user",
                "email": data.get("email", "user@example.com"),
                "name": "Mock User",
            },
        }
    )


@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    return jsonify(
        {
            "token": "mock_jwt_token",
            "user": {
                "id": "mock_user",
                "email": data.get("email", "user@example.com"),
                "name": data.get("name", "Mock User"),
            },
        }
    )


@app.route("/auth/logout", methods=["POST"])
def logout():
    return jsonify({"message": "Logged out successfully"})


@app.route("/auth/validate", methods=["POST"])
def validate():
    return jsonify(
        {
            "valid": True,
            "user": {"id": "mock_user", "email": "user@example.com"},
        }
    )


@app.route("/execute", methods=["POST"])
def execute():
    data = request.get_json() or {}
    return jsonify({"taskId": f"mock_task_{hash(json.dumps(data, sort_keys=True))}"})


@app.route("/parse", methods=["POST"])
def parse():
    data = request.get_json() or {}
    return jsonify(
        {
            "steps": [
                {
                    "id": "step1",
                    "goblin": data.get("default_goblin", "docs-writer"),
                    "task": data.get("text", "mock task"),
                    "dependencies": [],
                    "batch": 0,
                }
            ],
            "total_batches": 1,
            "max_parallel": 1,
        }
    )


@app.route("/raptor/status")
def raptor_status():
    return jsonify({"running": False})


@app.route("/raptor/start", methods=["POST"])
def raptor_start():
    return jsonify({"running": True})


@app.route("/raptor/stop", methods=["POST"])
def raptor_stop():
    return jsonify({"running": False})


@app.route("/raptor/logs", methods=["POST"])
def raptor_logs():
    return jsonify({"log_tail": "Mock raptor logs"})


@app.route("/api-keys/<provider>", methods=["GET", "POST", "DELETE"])
def api_keys(provider):
    if request.method == "POST":
        return jsonify({"message": f"API key stored for {provider}"})
    elif request.method == "GET":
        return jsonify({"key": f"mock_key_for_{provider}"})
    elif request.method == "DELETE":
        return jsonify({"message": f"API key cleared for {provider}"})


@app.route("/routing/providers/<provider>")
def get_provider_models(provider):
    models = {
        "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        "anthropic": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        "gemini": ["gemini-pro", "gemini-pro-vision"],
    }
    return jsonify(models.get(provider, []))
