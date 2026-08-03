#!/usr/bin/env python3
"""Verify frontend proxy -> backend SSE -> real LLM -> completed response."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from typing import Any

from smoke_support import (
    SmokeFailure,
    login_user,
    register_user,
    request_json,
    require_success,
    unique_credentials,
)


def read_sse_response(
    url: str,
    *,
    access_token: str,
    conversation_id: str,
    provider: str,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(
            {
                "conversation_id": conversation_id,
                "message": "Reply with exactly three words confirming dogfooding works.",
                "provider": provider,
            }
        ).encode("utf-8"),
        headers={
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": "goblin-dogfood-smoke/1",
        },
        method="POST",
    )

    try:
        response = urllib.request.urlopen(request, timeout=90)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SmokeFailure(
            f"Frontend stream proxy returned HTTP {error.code}: {detail}"
        ) from error
    except urllib.error.URLError as error:
        raise SmokeFailure(
            f"Unable to reach frontend stream proxy: {error.reason}"
        ) from error

    content_type = response.headers.get("Content-Type", "")
    if "text/event-stream" not in content_type.lower():
        raise SmokeFailure(
            f"Expected text/event-stream, got {content_type or 'no Content-Type'}"
        )

    event_name = ""
    accumulated_content = ""
    completion: dict[str, Any] | None = None
    with response:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                event_name = ""
                continue
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip().lower()
                continue
            if not line.startswith("data:"):
                continue
            try:
                event_data = json.loads(line.split(":", 1)[1].strip())
            except json.JSONDecodeError:
                continue
            if not isinstance(event_data, dict):
                continue
            if event_name == "error" or event_data.get("type") == "error":
                message = (
                    event_data.get("message") or event_data.get("error") or event_data
                )
                raise SmokeFailure(f"Backend emitted an SSE error: {message}")
            chunk = event_data.get("content")
            if isinstance(chunk, str):
                accumulated_content += chunk
            if event_data.get("done") is True:
                completion = event_data
                break

    if completion is None:
        raise SmokeFailure("SSE connection ended without a completion event")
    result = completion.get("result")
    if not isinstance(result, str) or not result.strip():
        result = accumulated_content
    if not isinstance(result, str) or not result.strip():
        raise SmokeFailure("SSE completion contained no assistant text")
    completion["result"] = result
    return completion


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-url",
        default=os.getenv("SMOKE_BACKEND_URL", "http://127.0.0.1:8001"),
    )
    parser.add_argument(
        "--frontend-url",
        default=os.getenv("SMOKE_FRONTEND_URL", "http://127.0.0.1:3000"),
    )
    parser.add_argument(
        "--provider",
        default=os.getenv("SMOKE_PROVIDER", "auto"),
        help="provider id, or auto to choose a healthy OpenAI/Anthropic provider",
    )
    args = parser.parse_args()
    api_base_url = f"{args.backend_url.rstrip('/')}/api/v1"
    stream_url = f"{args.frontend_url.rstrip('/')}/api/chat/stream"

    try:
        print(f"Chat smoke: {stream_url} -> {api_base_url}/chat/stream")
        provider_health_response = request_json(
            f"{api_base_url}/health/providers", timeout=60
        )
        if provider_health_response[0] == 404:
            health = require_success(
                "Provider health",
                request_json(f"{api_base_url}/health", timeout=60),
            )
            components = health.get("components")
            provider_component = (
                components.get("providers") if isinstance(components, dict) else None
            )
            providers = (
                provider_component.get("details")
                if isinstance(provider_component, dict)
                else None
            )
        else:
            health = require_success("Provider health", provider_health_response)
            providers = health.get("providers")
        selected_provider = args.provider
        if selected_provider == "auto" and isinstance(providers, dict):
            selected_provider = next(
                (
                    provider_id
                    for provider_id in ("anthropic", "openai")
                    if isinstance(providers.get(provider_id), dict)
                    and providers[provider_id].get("configured")
                    and providers[provider_id].get("status") == "healthy"
                ),
                "",
            )
        provider_health = (
            providers.get(selected_provider) if isinstance(providers, dict) else None
        )
        if not isinstance(provider_health, dict) or not provider_health.get(
            "configured"
        ):
            raise SmokeFailure(
                "No dogfooding provider is configured and healthy"
                if args.provider == "auto"
                else f"Provider '{selected_provider}' is not configured"
            )
        if provider_health.get("status") != "healthy":
            raise SmokeFailure(
                f"Provider '{selected_provider}' is not healthy: {provider_health.get('status')}"
            )

        email, password = unique_credentials()
        register_user(api_base_url, email, password)
        auth = login_user(api_base_url, email, password)
        access_token = auth["access_token"]
        conversation_body = require_success(
            "Create conversation",
            request_json(
                f"{api_base_url}/chat/conversations",
                method="POST",
                payload={"title": "Dogfood SSE smoke"},
                access_token=access_token,
            ),
        )
        conversation_data = conversation_body.get("data")
        conversation_id = (
            conversation_data.get("conversation_id")
            if isinstance(conversation_data, dict)
            else None
        )
        if not isinstance(conversation_id, str) or not conversation_id:
            raise SmokeFailure("Conversation creation returned no conversation_id")

        completion = read_sse_response(
            stream_url,
            access_token=access_token,
            conversation_id=conversation_id,
            provider=selected_provider,
        )
        used_provider = completion.get("provider")
        if not used_provider:
            conversation = require_success(
                "Read completed conversation",
                request_json(
                    f"{api_base_url}/chat/conversations/{conversation_id}",
                    access_token=access_token,
                ),
            )
            messages = conversation.get("messages")
            assistant_messages = (
                [
                    message
                    for message in messages
                    if isinstance(message, dict) and message.get("role") == "assistant"
                ]
                if isinstance(messages, list)
                else []
            )
            last_assistant = assistant_messages[-1] if assistant_messages else {}
            metadata = last_assistant.get("metadata")
            used_provider = (
                metadata.get("provider") if isinstance(metadata, dict) else None
            )
        if used_provider != selected_provider:
            raise SmokeFailure(
                f"Requested provider '{selected_provider}', but completion reported '{used_provider}'"
            )
    except SmokeFailure as error:
        print(f"FAIL: {error}")
        return 1

    print(
        f"PASS: real SSE response received from {selected_provider}: {completion['result']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
