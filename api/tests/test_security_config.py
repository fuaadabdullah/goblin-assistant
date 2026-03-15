from __future__ import annotations

from api.security_config import build_allowed_origins


def test_build_allowed_origins_keeps_public_frontend_in_development():
    origins = build_allowed_origins(environment="development", raw_origins="")

    assert "https://goblin-assistant.vercel.app" in origins
    assert "https://goblin-assistant-backend.onrender.com" in origins
    assert "http://localhost:3000" in origins


def test_build_allowed_origins_appends_canonical_public_origins():
    origins = build_allowed_origins(
        environment="development",
        raw_origins="https://example.com",
    )

    assert origins[0] == "https://example.com"
    assert "https://goblin-assistant.vercel.app" in origins
    assert "https://goblin-assistant-backend.onrender.com" in origins
