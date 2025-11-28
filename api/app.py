from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    Float,
    DateTime,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
import random
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:////tmp/goblin_assistant.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Database Models
class User(db.Model):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat(),
        }


class Provider(db.Model):
    __tablename__ = "providers"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    api_key = Column(String(500))
    base_url = Column(String(500))
    models = Column(JSON)  # Store as JSON array
    enabled = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "name": self.name,
            "api_key": self.api_key or "",
            "base_url": self.base_url or "",
            "models": self.models or [],
            "enabled": self.enabled,
        }


class Model(db.Model):
    __tablename__ = "models"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    provider = Column(String(50), nullable=False)
    model_id = Column(String(100), nullable=False)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)
    enabled = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "name": self.name,
            "provider": self.provider,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "enabled": self.enabled,
        }


class Task(db.Model):
    __tablename__ = "tasks"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True)
    goblin = Column(String(50), nullable=False)
    task = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    result = Column(Text)
    cost = Column(Float, default=0.0)
    tokens = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "goblin": self.goblin,
            "task": self.task,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "result": self.result,
            "cost": self.cost,
            "tokens": self.tokens,
            "duration_ms": self.duration_ms,
        }


class SearchDocument(db.Model):
    __tablename__ = "search_documents"
    id = Column(String(50), primary_key=True)
    collection = Column(String(50), nullable=False)
    document = Column(Text, nullable=False)
    document_metadata = Column(JSON)

    def to_dict(self):
        return {
            "id": self.id,
            "document": self.document,
            "metadata": self.document_metadata or {},
            "collection": self.collection,
        }


# Database initialization
def init_db():
    """Initialize the database and create tables"""
    with app.app_context():
        db.create_all()

        # Seed initial data if tables are empty
        if Provider.query.count() == 0:
            # Seed providers with API keys from environment variables
            providers_data = [
                {
                    "name": "openai",
                    "api_key": os.getenv("OPENAI_API_KEY", ""),
                    "base_url": "",
                    "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
                    "enabled": True,
                },
                {
                    "name": "anthropic",
                    "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
                    "base_url": "",
                    "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
                    "enabled": True,
                },
                {
                    "name": "gemini",
                    "api_key": os.getenv("GEMINI_API_KEY", ""),
                    "base_url": "",
                    "models": ["gemini-pro", "gemini-pro-vision"],
                    "enabled": True,
                },
                {
                    "name": "groq",
                    "api_key": os.getenv("GROQ_API_KEY", ""),
                    "base_url": "",
                    "models": ["llama2-70b-4096", "mixtral-8x7b-32768"],
                    "enabled": True,
                },
                {
                    "name": "deepseek",
                    "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
                    "base_url": "",
                    "models": ["deepseek-chat", "deepseek-coder"],
                    "enabled": True,
                },
                {
                    "name": "siliconflow",
                    "api_key": os.getenv("SILICONFLOW_API_KEY", ""),
                    "base_url": "",
                    "models": ["Qwen2-72B-Instruct"],
                    "enabled": True,
                },
                {
                    "name": "moonshot",
                    "api_key": os.getenv("MOONSHOT_API_KEY", ""),
                    "base_url": "",
                    "models": ["moonshot-v1-8k", "moonshot-v1-32k"],
                    "enabled": True,
                },
                {
                    "name": "fireworks",
                    "api_key": os.getenv("FIREWORKS_API_KEY", ""),
                    "base_url": "",
                    "models": ["accounts/fireworks/models/llama-v2-7b-chat"],
                    "enabled": True,
                },
                {
                    "name": "elevenlabs",
                    "api_key": os.getenv("ELEVENLABS_API_KEY", ""),
                    "base_url": "",
                    "models": ["eleven_monolingual_v1"],
                    "enabled": True,
                },
                {
                    "name": "datadog",
                    "api_key": os.getenv("DATADOG_API_KEY", ""),
                    "base_url": "",
                    "models": [],
                    "enabled": True,
                },
                {
                    "name": "netlify",
                    "api_key": os.getenv("NETLIFY_API_KEY", ""),
                    "base_url": "",
                    "models": [],
                    "enabled": True,
                },
            ]

            for provider_data in providers_data:
                provider = Provider(
                    name=provider_data["name"],
                    api_key=provider_data["api_key"],
                    base_url=provider_data["base_url"],
                    models=provider_data["models"],
                    enabled=provider_data["enabled"],
                )
                db.session.add(provider)
        else:
            # Update existing providers with API keys from environment variables
            providers_to_update = {
                "openai": os.getenv("OPENAI_API_KEY", ""),
                "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
                "gemini": os.getenv("GEMINI_API_KEY", ""),
                "groq": os.getenv("GROQ_API_KEY", ""),
                "deepseek": os.getenv("DEEPSEEK_API_KEY", ""),
                "siliconflow": os.getenv("SILICONFLOW_API_KEY", ""),
                "moonshot": os.getenv("MOONSHOT_API_KEY", ""),
                "fireworks": os.getenv("FIREWORKS_API_KEY", ""),
                "elevenlabs": os.getenv("ELEVENLABS_API_KEY", ""),
                "datadog": os.getenv("DATADOG_API_KEY", ""),
                "netlify": os.getenv("NETLIFY_API_KEY", ""),
            }

            for provider_name, api_key in providers_to_update.items():
                provider = Provider.query.filter_by(name=provider_name).first()
                if provider and api_key:
                    provider.api_key = api_key
                    print(f"Updated API key for {provider_name}")
                elif not provider:
                    # Create missing providers
                    provider_data = {
                        "name": provider_name,
                        "api_key": api_key,
                        "base_url": "",
                        "models": [],
                        "enabled": True,
                    }
                    if provider_name == "openai":
                        provider_data["models"] = [
                            "gpt-4",
                            "gpt-4-turbo",
                            "gpt-3.5-turbo",
                        ]
                    elif provider_name == "anthropic":
                        provider_data["models"] = [
                            "claude-3-opus",
                            "claude-3-sonnet",
                            "claude-3-haiku",
                        ]
                    elif provider_name == "gemini":
                        provider_data["models"] = ["gemini-pro", "gemini-pro-vision"]
                    elif provider_name == "groq":
                        provider_data["models"] = [
                            "llama2-70b-4096",
                            "mixtral-8x7b-32768",
                        ]
                    elif provider_name == "deepseek":
                        provider_data["models"] = ["deepseek-chat", "deepseek-coder"]
                    elif provider_name == "siliconflow":
                        provider_data["models"] = ["Qwen2-72B-Instruct"]
                    elif provider_name == "moonshot":
                        provider_data["models"] = ["moonshot-v1-8k", "moonshot-v1-32k"]
                    elif provider_name == "fireworks":
                        provider_data["models"] = [
                            "accounts/fireworks/models/llama-v2-7b-chat"
                        ]
                    elif provider_name == "elevenlabs":
                        provider_data["models"] = ["eleven_monolingual_v1"]

                    provider = Provider(**provider_data)
                    db.session.add(provider)
                    print(f"Created provider {provider_name}")

        if Model.query.count() == 0:
            # Seed models
            models_data = [
                # OpenAI models
                {
                    "name": "gpt-4",
                    "provider": "openai",
                    "model_id": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                {
                    "name": "gpt-4-turbo",
                    "provider": "openai",
                    "model_id": "gpt-4-turbo-preview",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                {
                    "name": "gpt-3.5-turbo",
                    "provider": "openai",
                    "model_id": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                # Anthropic models
                {
                    "name": "claude-3-opus",
                    "provider": "anthropic",
                    "model_id": "claude-3-opus-20240229",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                {
                    "name": "claude-3-sonnet",
                    "provider": "anthropic",
                    "model_id": "claude-3-sonnet-20240229",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                {
                    "name": "claude-3-haiku",
                    "provider": "anthropic",
                    "model_id": "claude-3-haiku-20240307",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                # Gemini models
                {
                    "name": "gemini-pro",
                    "provider": "gemini",
                    "model_id": "gemini-pro",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                {
                    "name": "gemini-pro-vision",
                    "provider": "gemini",
                    "model_id": "gemini-pro-vision",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                # Groq models
                {
                    "name": "llama2-70b",
                    "provider": "groq",
                    "model_id": "llama2-70b-4096",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                {
                    "name": "mixtral-8x7b",
                    "provider": "groq",
                    "model_id": "mixtral-8x7b-32768",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                # DeepSeek models
                {
                    "name": "deepseek-chat",
                    "provider": "deepseek",
                    "model_id": "deepseek-chat",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                {
                    "name": "deepseek-coder",
                    "provider": "deepseek",
                    "model_id": "deepseek-coder",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                # SiliconFlow models
                {
                    "name": "qwen2-72b",
                    "provider": "siliconflow",
                    "model_id": "Qwen2-72B-Instruct",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
                # Moonshot models
                {
                    "name": "moonshot-v1-8k",
                    "provider": "moonshot",
                    "model_id": "moonshot-v1-8k",
                    "temperature": 0.7,
                    "max_tokens": 8192,
                    "enabled": True,
                },
                {
                    "name": "moonshot-v1-32k",
                    "provider": "moonshot",
                    "model_id": "moonshot-v1-32k",
                    "temperature": 0.7,
                    "max_tokens": 32768,
                    "enabled": True,
                },
                # Fireworks models
                {
                    "name": "llama-v2-7b",
                    "provider": "fireworks",
                    "model_id": "accounts/fireworks/models/llama-v2-7b-chat",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enabled": True,
                },
            ]

            for model_data in models_data:
                model = Model(
                    name=model_data["name"],
                    provider=model_data["provider"],
                    model_id=model_data["model_id"],
                    temperature=model_data["temperature"],
                    max_tokens=model_data["max_tokens"],
                    enabled=model_data["enabled"],
                )
                db.session.add(model)

        if SearchDocument.query.count() == 0:
            # Seed search documents
            search_docs = [
                {
                    "id": "doc_1",
                    "collection": "documents",
                    "document": "This is a comprehensive guide to building modern web applications using React and TypeScript. It covers component architecture, state management, and best practices for scalable applications.",
                    "metadata": {
                        "source": "docs",
                        "type": "guide",
                        "tags": ["react", "typescript", "web-development"],
                    },
                },
                {
                    "id": "doc_2",
                    "collection": "documents",
                    "document": "API design principles for microservices architecture. Learn about RESTful APIs, GraphQL, and how to design scalable backend services.",
                    "metadata": {
                        "source": "docs",
                        "type": "tutorial",
                        "tags": ["api", "microservices", "backend"],
                    },
                },
                {
                    "id": "doc_3",
                    "collection": "documents",
                    "document": "Machine learning fundamentals including neural networks, deep learning, and practical applications in computer vision and natural language processing.",
                    "metadata": {
                        "source": "docs",
                        "type": "reference",
                        "tags": ["ml", "ai", "neural-networks"],
                    },
                },
                {
                    "id": "code_1",
                    "collection": "code",
                    "document": "function calculateTotal(items) { return items.reduce((sum, item) => sum + item.price * item.quantity, 0); }",
                    "metadata": {
                        "source": "code",
                        "language": "javascript",
                        "tags": ["javascript", "array-methods"],
                    },
                },
                {
                    "id": "code_2",
                    "collection": "code",
                    "document": "class UserService { constructor(db) { this.db = db; } async findById(id) { return this.db.users.find(u => u.id === id); } }",
                    "metadata": {
                        "source": "code",
                        "language": "javascript",
                        "tags": ["javascript", "class", "service"],
                    },
                },
                {
                    "id": "kb_1",
                    "collection": "knowledge",
                    "document": "DevOps best practices include continuous integration, automated testing, infrastructure as code, and monitoring. These practices help teams deliver software faster and more reliably.",
                    "metadata": {
                        "source": "knowledge",
                        "category": "devops",
                        "tags": ["devops", "ci-cd", "automation"],
                    },
                },
                {
                    "id": "kb_2",
                    "collection": "knowledge",
                    "document": "Security principles: defense in depth, least privilege, fail-safe defaults, and regular security audits are essential for protecting applications and data.",
                    "metadata": {
                        "source": "knowledge",
                        "category": "security",
                        "tags": ["security", "best-practices", "auditing"],
                    },
                },
            ]

            for doc_data in search_docs:
                doc = SearchDocument(
                    id=doc_data["id"],
                    collection=doc_data["collection"],
                    document=doc_data["document"],
                    document_metadata=doc_data["metadata"],
                )
                db.session.add(doc)

        if Task.query.count() == 0:
            # Seed some mock tasks
            mock_tasks = [
                {
                    "id": "task_001",
                    "user_id": "demo_user",
                    "goblin": "docs-writer",
                    "task": "Write documentation for the new API endpoints",
                    "status": "completed",
                    "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
                    "updated_at": datetime.now(timezone.utc)
                    - timedelta(hours=1, minutes=45),
                    "result": "Successfully generated comprehensive API documentation with examples and usage patterns.",
                    "cost": 0.0345,
                    "tokens": 456,
                    "duration_ms": 2340,
                },
                {
                    "id": "task_002",
                    "user_id": "demo_user",
                    "goblin": "code-writer",
                    "task": "Implement user authentication middleware",
                    "status": "completed",
                    "created_at": datetime.now(timezone.utc) - timedelta(hours=4),
                    "updated_at": datetime.now(timezone.utc)
                    - timedelta(hours=3, minutes=30),
                    "result": "Created JWT-based authentication middleware with role-based access control and secure token handling.",
                    "cost": 0.0678,
                    "tokens": 789,
                    "duration_ms": 4120,
                },
                {
                    "id": "task_003",
                    "user_id": "demo_user",
                    "goblin": "docs-writer",
                    "task": "Create deployment guide for the application",
                    "status": "completed",
                    "created_at": datetime.now(timezone.utc) - timedelta(hours=6),
                    "updated_at": datetime.now(timezone.utc)
                    - timedelta(hours=5, minutes=15),
                    "result": "Compiled detailed deployment guide covering Docker, Kubernetes, and cloud platform configurations.",
                    "cost": 0.0234,
                    "tokens": 345,
                    "duration_ms": 1890,
                },
            ]

            for task_data in mock_tasks:
                task = Task(
                    id=task_data["id"],
                    user_id=task_data["user_id"],
                    goblin=task_data["goblin"],
                    task=task_data["task"],
                    status=task_data["status"],
                    created_at=task_data["created_at"],
                    updated_at=task_data["updated_at"],
                    result=task_data["result"],
                    cost=task_data["cost"],
                    tokens=task_data["tokens"],
                    duration_ms=task_data["duration_ms"],
                )
                db.session.add(task)

        db.session.commit()


# Initialize database on startup
with app.app_context():
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        # Don't crash the app if database init fails
        pass


@app.route("/")
def home():
    return jsonify({"status": "healthy", "message": "API is working!"})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


@app.route("/db/init", methods=["POST"])
def init_database():
    """Manually initialize the database"""
    try:
        init_db()
        return jsonify({"message": "Database initialized successfully"})
    except Exception as e:
        return jsonify({"error": f"Database initialization failed: {str(e)}"}), 500


@app.route("/routing/providers")
def get_providers():
    return jsonify(["openai", "anthropic", "gemini"])


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "")
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Find user by email
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify(
        {
            "token": f"jwt_token_{user.id}",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
            },
        }
    )


@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = data.get("email", "")
    password = data.get("password", "")
    name = data.get("name", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "User already exists"}), 409

    # Create new user
    user = User(email=email, name=name or email.split("@")[0].title())
    db.session.add(user)
    db.session.commit()

    return jsonify(
        {
            "token": f"jwt_token_{user.id}",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
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
    task_description = data.get("task", "")
    goblin = data.get("goblin", "docs-writer")
    user_id = data.get("user_id", "anonymous")

    if not task_description:
        return jsonify({"error": "Task description is required"}), 400

    # Create a new task
    task = Task(user_id=user_id, goblin=goblin, task=task_description, status="pending")
    db.session.add(task)

    # Simulate task execution (in production, this would be async)
    # For now, we'll mark it as completed immediately with mock results
    task.status = "completed"
    task.result = f"Task '{task_description}' completed successfully using {goblin}"
    task.cost = round(random.uniform(0.01, 0.1), 4)
    task.tokens = random.randint(100, 1000)
    task.duration_ms = random.randint(500, 3000)
    task.updated_at = datetime.now(timezone.utc)

    db.session.commit()

    return jsonify(
        {
            "taskId": task.id,
            "status": "accepted",
            "message": "Task submitted for execution",
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


@app.route("/goblins")
def get_goblins():
    """Get list of available goblins"""
    return jsonify(
        [
            {
                "id": "docs-writer",
                "name": "docs-writer",
                "title": "Documentation Writer",
                "status": "available",
                "guild": "crafters",
            },
            {
                "id": "code-writer",
                "name": "code-writer",
                "title": "Code Writer",
                "status": "available",
                "guild": "crafters",
            },
        ]
    )


@app.route("/goblins/<goblin>/history")
def get_goblin_history(goblin):
    """Get task history for a specific goblin"""
    limit = int(request.args.get("limit", 10))
    user_id = request.args.get("user_id")

    # Query tasks from database
    query = Task.query.filter_by(goblin=goblin)
    if user_id:
        query = query.filter_by(user_id=user_id)

    tasks = query.order_by(Task.created_at.desc()).limit(limit).all()

    # Convert to the expected format
    history = []
    for task in tasks:
        history.append(
            {
                "id": task.id,
                "goblin": task.goblin,
                "task": task.task,
                "response": task.result or "Task in progress",
                "timestamp": int(task.created_at.timestamp() * 1000),
                "kpis": f"duration_ms: {task.duration_ms}, cost: {task.cost}, tokens: {task.tokens}",
            }
        )

    return jsonify(history)


@app.route("/goblins/<goblin>/stats")
def get_goblin_stats(goblin):
    """Get statistics for a specific goblin"""
    user_id = request.args.get("user_id")

    # Query completed tasks from database
    query = Task.query.filter_by(goblin=goblin, status="completed")
    if user_id:
        query = query.filter_by(user_id=user_id)

    tasks = query.all()

    if not tasks:
        return jsonify(
            {
                "total_tasks": 0,
                "total_cost": 0.0,
                "avg_duration_ms": 0,
                "success_rate": 0.0,
                "last_used": None,
            }
        )

    total_tasks = len(tasks)
    total_cost = sum(task.cost for task in tasks)
    avg_duration = sum(task.duration_ms for task in tasks) / total_tasks
    success_rate = 1.0  # All completed tasks are successful in our mock
    last_used = max(task.updated_at for task in tasks)
    last_used_timestamp = int(last_used.timestamp() * 1000)

    return jsonify(
        {
            "total_tasks": total_tasks,
            "total_cost": round(total_cost, 4),
            "avg_duration_ms": int(avg_duration),
            "success_rate": success_rate,
            "last_used": last_used_timestamp,
        }
    )


@app.route("/cost-summary")
def get_cost_summary():
    """Get overall cost summary"""
    user_id = request.args.get("user_id")

    # Query completed tasks from database
    query = Task.query.filter_by(status="completed")
    if user_id:
        query = query.filter_by(user_id=user_id)

    tasks = query.all()

    if not tasks:
        return jsonify(
            {
                "total_cost": 0.0,
                "cost_by_provider": {},
                "cost_by_model": {},
            }
        )

    total_cost = sum(task.cost for task in tasks)

    # Group costs by provider and model from task data
    cost_by_provider = {}
    cost_by_model = {}

    for task in tasks:
        # Use provider and model from task data
        provider = task.provider or "unknown"
        model = task.model or "unknown"

        cost_by_provider[provider] = cost_by_provider.get(provider, 0.0) + task.cost
        cost_by_model[model] = cost_by_model.get(model, 0.0) + task.cost

    return jsonify(
        {
            "total_cost": round(total_cost, 4),
            "cost_by_provider": {k: round(v, 4) for k, v in cost_by_provider.items()},
            "cost_by_model": {k: round(v, 4) for k, v in cost_by_model.items()},
        }
    )


@app.route("/stream")
def stream_task():
    """Stream task execution results"""
    task_id = request.args.get("task_id", "mock_task")
    goblin = request.args.get("goblin", "docs-writer")
    task = request.args.get("task", "mock task")

    def generate_events():
        import time

        # Send initial status
        yield f"data: {json.dumps({'status': 'started', 'task_id': task_id})}\n\n"
        time.sleep(0.5)

        # Send chunks
        response_text = f"Executing task '{task}' using goblin '{goblin}'"
        words = response_text.split()
        total_tokens = 0
        total_cost = 0

        for i, word in enumerate(words):
            time.sleep(0.1)  # Simulate processing delay

            chunk_data = {
                "content": word + (" " if i < len(words) - 1 else ""),
                "token_count": len(word) // 4 + 1,
                "cost_delta": 0.001,
                "done": False,
            }

            total_tokens += chunk_data["token_count"]
            total_cost += chunk_data["cost_delta"]

            yield f"data: {json.dumps(chunk_data)}\n\n"

        # Send completion
        completion_data = {
            "result": response_text,
            "cost": total_cost,
            "tokens": total_tokens,
            "model": "gpt-4",
            "provider": "openai",
            "duration_ms": len(words) * 100,
            "done": True,
        }

        yield f"data: {json.dumps(completion_data)}\n\n"

    return app.response_class(
        generate_events(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@app.route("/settings")
def get_settings():
    """Get all settings"""
    # Query providers and models from database
    providers = Provider.query.all()
    models = Model.query.all()

    return jsonify(
        {
            "providers": [provider.to_dict() for provider in providers],
            "models": [model.to_dict() for model in models],
        }
    )


@app.route("/settings/providers/<provider_name>", methods=["PUT"])
def update_provider_settings(provider_name):
    """Update settings for a specific provider"""
    data = request.get_json() or {}

    # Find and update the provider in database
    provider = Provider.query.filter_by(name=provider_name).first()
    if not provider:
        return jsonify({"error": f"Provider {provider_name} not found"}), 404

    # Update provider fields
    for key, value in data.items():
        if hasattr(provider, key):
            setattr(provider, key, value)

    db.session.commit()

    return jsonify({"message": f"Provider {provider_name} updated successfully"})


@app.route("/settings/models/<model_name>", methods=["PUT"])
def update_model_settings(model_name):
    """Update settings for a specific model"""
    data = request.get_json() or {}

    # Find and update the model in database
    model = Model.query.filter_by(name=model_name).first()
    if not model:
        return jsonify({"error": f"Model {model_name} not found"}), 404

    # Update model fields
    for key, value in data.items():
        if hasattr(model, key):
            setattr(model, key, value)

    db.session.commit()

    return jsonify({"message": f"Model {model_name} updated successfully"})


@app.route("/settings/test-connection", methods=["POST"])
def test_connection():
    """Test connection to a provider"""
    data = request.get_json() or {}
    provider_name = data.get("provider_name", "")

    # Find the provider in database
    provider = Provider.query.filter_by(name=provider_name).first()
    if not provider:
        return jsonify(
            {"connected": False, "message": f"Provider {provider_name} not found"}
        ), 404

    if not provider.enabled:
        return jsonify(
            {"connected": False, "message": f"Provider {provider_name} is disabled"}
        ), 400

    # Mock connection test - in real implementation, this would actually test the API key
    # For now, assume connection is successful if API key is set
    has_api_key = bool(provider.api_key and provider.api_key.strip())

    if has_api_key:
        return jsonify(
            {"connected": True, "message": f"Successfully connected to {provider_name}"}
        )
    else:
        return jsonify(
            {
                "connected": False,
                "message": f"No API key configured for {provider_name}",
            }
        )


# API Keys status endpoint for frontend
@app.route("/settings/api-keys/status")
def get_api_keys_status():
    """Get status of API keys for all providers (without exposing the keys)"""
    providers = Provider.query.all()

    status = {}
    for provider in providers:
        has_key = bool(provider.api_key and provider.api_key.strip())
        status[provider.name] = {
            "configured": has_key,
            "enabled": provider.enabled,
            "models": provider.models or [],
        }

    return jsonify(status)


# Search endpoints
@app.route("/search/collections", methods=["GET"])
def get_search_collections():
    """Get available search collections"""
    # Query distinct collections from SearchDocument table
    collections = db.session.query(SearchDocument.collection).distinct().all()
    collection_names = [c[0] for c in collections]

    return jsonify(
        {
            "collections": collection_names,
            "total_collections": len(collection_names),
        }
    )


@app.route("/search/query", methods=["POST"])
def search_query():
    """Perform semantic search across collections"""
    data = request.get_json()
    query = data.get("query", "")
    collection = data.get("collection", "all")
    limit = data.get("limit", 10)

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    results = []

    # Query documents from database
    if collection == "all":
        documents = SearchDocument.query.all()
    else:
        documents = SearchDocument.query.filter_by(collection=collection).all()

    for doc in documents:
        # Simple text matching (in production, this would use vector similarity)
        if query.lower() in doc.document.lower():
            results.append(
                {
                    "id": doc.id,
                    "document": doc.document,
                    "metadata": doc.metadata,
                    "collection": doc.collection,
                    "score": random.uniform(0.7, 0.95),  # Mock similarity score
                }
            )

    # Sort by score and limit results
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:limit]

    return jsonify(
        {
            "query": query,
            "collection": collection,
            "results": results,
            "total_results": len(results),
        }
    )


@app.route("/search/suggest", methods=["GET"])
def search_suggest():
    """Get search suggestions"""
    query = request.args.get("q", "")
    if not query:
        return jsonify({"suggestions": []})

    # Mock suggestions based on common queries
    suggestions = [
        f"{query} tutorial",
        f"{query} best practices",
        f"{query} examples",
        f"how to {query}",
        f"{query} documentation",
    ]

    return jsonify({"suggestions": suggestions})


if __name__ == "__main__":
    app.run(debug=True)
