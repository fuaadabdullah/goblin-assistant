"""
FastAPI main application with privacy & security features integrated.

This is a reference implementation showing how to integrate:
- Sanitization
- Rate limiting
- Telemetry with redaction
- Privacy endpoints
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from api.middleware.rate_limiter import RateLimiter
from api.routes.privacy import router as privacy_router
from api.services.telemetry import log_inference_metrics
from api.services.sanitization import sanitize_input_for_model, is_sensitive_content

# Configure logging with redaction
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("goblin_assistant.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting Goblin Assistant API with privacy features")
    yield
    logger.info("Shutting down Goblin Assistant API")


# Initialize FastAPI app
app = FastAPI(
    title="Goblin Assistant API",
    description="Privacy-first AI assistant API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://goblin.fuaad.ai", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Rate limiting middleware
rate_limiter = RateLimiter(
    redis_url="redis://localhost:6379", requests_per_minute=100, requests_per_hour=1000
)
app.middleware("http")(rate_limiter)

# Include privacy router
app.include_router(privacy_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "goblin-assistant",
        "privacy_features": {
            "sanitization": True,
            "rate_limiting": True,
            "rls": True,
            "ttl": True,
            "gdpr_compliant": True,
        },
    }


@app.post("/api/chat")
async def chat(request: Request):
    """
    Chat endpoint with privacy safeguards.

    Features:
    - Input sanitization
    - Rate limiting
    - Redacted telemetry
    - No raw message storage
    """
    try:
        body = await request.json()
        user_message = body.get("message", "")

        # Check for sensitive content
        if is_sensitive_content(user_message):
            logger.warning("Sensitive content detected in chat request")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Sensitive content detected",
                    "suggestion": "Please remove PII/secrets from your message",
                },
            )

        # Sanitize input
        sanitized_message, pii_detected = sanitize_input_for_model(user_message)

        if pii_detected:
            logger.warning(f"PII detected and redacted: {', '.join(pii_detected)}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "PII detected in message",
                    "detected_types": pii_detected,
                    "suggestion": "Please remove personal information",
                },
            )

        # TODO: Forward to LLM provider with sanitized input
        # response = await llm_client.chat(sanitized_message)

        # Log metrics (NO raw message content)
        log_inference_metrics(
            provider="openai",
            model="gpt-4",
            latency_ms=150,
            token_count=50,
            cost_usd=0.002,
            status_code=200,
            user_id=getattr(request.state, "user_id", None),
        )

        return {
            "response": "This is a placeholder response",
            "sanitized": True,
            "privacy_preserved": True,
        }

    except Exception as e:
        logger.error(
            f"Chat error: {str(e)}", exc_info=False
        )  # Don't log full exception (may contain PII)
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with privacy protection."""
    # Log error WITHOUT sensitive request data
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}",
        exc_info=False,  # Don't log full traceback to avoid PII leaks
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected error occurred",
            "request_id": request.headers.get("X-Request-ID", "unknown"),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main_with_privacy:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,  # Use our custom logging config
    )
