from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.providers import router_service
from api.providers.dispatcher_pkg.execution import dispatch_request
from api.providers.provider_config_runtime import ProviderToml


def _router_config(tmp_path):
    config_path = tmp_path / "providers.toml"
    config_path.write_text(
        """
[router_models."router-cheap"]
description = "Budget-first routing"
routing_strategy = "latency-based-routing"
num_retries = 2
enable_pre_call_checks = true
fallbacks = ["router-code"]
context_window_fallbacks = ["gemini-2.5-flash"]
content_policy_fallbacks = ["gemini-2.5-flash"]

[[router_models."router-cheap".backends]]
provider_id = "dashscope"
litellm_provider = "dashscope"
model = "qwen-turbo"
api_key_env = "DASHSCOPE_API_KEY"
endpoint_env = "DASHSCOPE_ENDPOINT"
order = 1
cost_input_per1k = 0.00005
cost_output_per1k = 0.0002

[[router_models."router-cheap".backends]]
provider_id = "vertex_ai"
litellm_provider = "vertex_ai"
model = "gemini-2.5-flash-lite"
project_env = "VERTEX_AI_PROJECT"
vertex_location_env = "VERTEX_AI_LOCATION"
vertex_credentials_env = "GOOGLE_APPLICATION_CREDENTIALS"
order = 2
cost_input_per1k = 0.00010
cost_output_per1k = 0.0004

[router_models."router-code"]
description = "Code-first routing for implementation work"
routing_strategy = "cost-based-routing"
num_retries = 3
enable_pre_call_checks = true
fallbacks = ["router-cheap"]
context_window_fallbacks = ["gemini-2.5-flash"]
content_policy_fallbacks = ["gemini-2.5-flash"]

[[router_models."router-code".backends]]
provider_id = "dashscope"
litellm_provider = "dashscope"
model = "qwen3-coder"
api_key_env = "DASHSCOPE_API_KEY"
endpoint_env = "DASHSCOPE_ENDPOINT"
order = 1
cost_input_per1k = 0.00011
cost_output_per1k = 0.0008

[[router_models."router-code".backends]]
provider_id = "vertex_ai"
litellm_provider = "vertex_ai"
model = "gemini-2.5-flash"
project_env = "VERTEX_AI_PROJECT"
vertex_location_env = "VERTEX_AI_LOCATION"
vertex_credentials_env = "GOOGLE_APPLICATION_CREDENTIALS"
order = 2
cost_input_per1k = 0.00030
cost_output_per1k = 0.0025

[router_models."router-reason"]
description = "Reasoning-first routing with a lower-cost fallback"
routing_strategy = "cost-based-routing"
num_retries = 4
enable_pre_call_checks = true
fallbacks = ["router-code"]
context_window_fallbacks = ["gemini-2.5-flash"]
content_policy_fallbacks = ["gemini-2.5-flash"]

[[router_models."router-reason".backends]]
provider_id = "vertex_ai"
litellm_provider = "vertex_ai"
model = "gemini-2.5-pro"
project_env = "VERTEX_AI_PROJECT"
vertex_location_env = "VERTEX_AI_LOCATION"
vertex_credentials_env = "GOOGLE_APPLICATION_CREDENTIALS"
order = 1
cost_input_per1k = 0.00125
cost_output_per1k = 0.01000

[[router_models."router-reason".backends]]
provider_id = "dashscope"
litellm_provider = "dashscope"
model = "qwen-max"
api_key_env = "DASHSCOPE_API_KEY"
endpoint_env = "DASHSCOPE_ENDPOINT"
order = 2
cost_input_per1k = 0.00400
cost_output_per1k = 0.01200
""".strip(),
        encoding="utf-8",
    )
    return ProviderToml.load(config_path)


def _prepare_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-key")
    monkeypatch.setenv("DASHSCOPE_ENDPOINT", "https://dashscope-intl.aliyuncs.com/compatible-mode")
    monkeypatch.setenv("VERTEX_AI_PROJECT", "goblin-project")
    monkeypatch.setenv("VERTEX_AI_LOCATION", "us-central1")
    vertex_credentials = tmp_path / "vertex-sa.json"
    vertex_credentials.write_text(
        '{"type":"service_account","project_id":"goblin"}', encoding="utf-8"
    )
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(vertex_credentials))
    monkeypatch.setenv("UPSTASH_REDIS_HOST", "candy.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_PASSWORD", "upstash-password")
    monkeypatch.setenv("UPSTASH_REDIS_PORT", "6380")
    return vertex_credentials


class FakeRouter:
    instances: list["FakeRouter"] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls: list[tuple[str, dict]] = []
        self.__class__.instances.append(self)

    async def acompletion(self, model, **kwargs):
        self.calls.append((model, kwargs))
        model_map = {
            "router-cheap": "dashscope/qwen-turbo",
            "router-code": "dashscope/qwen3-coder",
            "router-reason": "vertex_ai/gemini-2.5-pro",
        }
        backend_model = model_map.get(model, "dashscope/qwen-turbo")
        return SimpleNamespace(
            model=backend_model,
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=f"{model} result"),
                )
            ],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=5),
        )


def test_build_model_list_uses_cost_based_weights(tmp_path, monkeypatch):
    provider_toml = _router_config(tmp_path)
    _prepare_env(monkeypatch, tmp_path)

    model_list = router_service.build_model_list(provider_toml)
    cheap_entries = [entry for entry in model_list if entry["model_name"] == "router-cheap"]

    assert len(cheap_entries) == 2
    assert cheap_entries[0]["litellm_params"]["model"] == "dashscope/qwen-turbo"
    assert cheap_entries[1]["litellm_params"]["model"] == "vertex_ai/gemini-2.5-flash-lite"
    assert (
        cheap_entries[0]["litellm_params"]["weight"] > cheap_entries[1]["litellm_params"]["weight"]
    )
    assert cheap_entries[0]["model_info"]["provider_id"] == "dashscope"
    assert cheap_entries[1]["model_info"]["provider_id"] == "vertex_ai"
    assert cheap_entries[1]["litellm_params"]["vertex_project"] == "goblin-project"
    assert cheap_entries[1]["litellm_params"]["vertex_location"] == "us-central1"
    assert cheap_entries[1]["litellm_params"]["vertex_credentials"] == str(
        tmp_path / "vertex-sa.json"
    )

    # Regression: VERTEX_AI_LOCATION/VERTEX_AI_PROJECT/GOOGLE_APPLICATION_CREDENTIALS
    # are process-global env vars, not scoped to the vertex_ai backend. Before this
    # fix, _resolve_vertex_location()/_resolve_vertex_credentials() fell back to
    # them unconditionally for every backend, so the dashscope deployment's
    # litellm_params ended up polluted with irrelevant vertex_location/
    # vertex_credentials keys — which broke LiteLLM's dashscope request
    # construction (reproduced live: it 404'd instead of hitting the configured
    # api_base's /chat/completions path).
    assert "vertex_project" not in cheap_entries[0]["litellm_params"]
    assert "vertex_location" not in cheap_entries[0]["litellm_params"]
    assert "vertex_credentials" not in cheap_entries[0]["litellm_params"]


@pytest.mark.asyncio
async def test_route_logical_model_uses_group_specific_router_kwargs(tmp_path, monkeypatch):
    provider_toml = _router_config(tmp_path)
    _prepare_env(monkeypatch, tmp_path)

    monkeypatch.setattr(router_service, "_load_router_class", lambda: FakeRouter)
    router_service.invalidate_router_cache()
    FakeRouter.instances.clear()

    response = await router_service.route_logical_model(
        "router-cheap",
        {"messages": [{"role": "user", "content": "hello"}]},
        timeout_ms=30000,
        provider_toml=provider_toml,
    )

    assert response is not None
    assert response["ok"] is True
    assert response["provider"] == "router-cheap"
    assert response["model"] == "qwen-turbo"
    assert response["result"]["text"] == "router-cheap result"
    assert response["routing"]["backend_litellm_model"] == "dashscope/qwen-turbo"

    router_instance = FakeRouter.instances[-1]
    assert router_instance.kwargs["routing_strategy"] == "latency-based-routing"
    assert router_instance.kwargs["num_retries"] == 2
    assert router_instance.kwargs["enable_pre_call_checks"] is True
    assert router_instance.kwargs["redis_host"] == "candy.upstash.io"
    assert router_instance.kwargs["redis_password"] == "upstash-password"
    assert router_instance.kwargs["redis_port"] == 6380
    assert router_instance.kwargs["fallbacks"] == [{"router-cheap": ["router-code"]}]
    assert router_instance.kwargs["context_window_fallbacks"] == [
        {"router-cheap": ["gemini-2.5-flash"]}
    ]
    assert router_instance.kwargs["content_policy_fallbacks"] == [
        {"router-cheap": ["gemini-2.5-flash"]}
    ]


@pytest.mark.asyncio
async def test_route_logical_model_uses_distinct_strategies_per_group(tmp_path, monkeypatch):
    provider_toml = _router_config(tmp_path)
    _prepare_env(monkeypatch, tmp_path)

    monkeypatch.setattr(router_service, "_load_router_class", lambda: FakeRouter)
    router_service.invalidate_router_cache()
    FakeRouter.instances.clear()

    await router_service.route_logical_model(
        "router-cheap",
        {"messages": [{"role": "user", "content": "hello"}]},
        timeout_ms=30000,
        provider_toml=provider_toml,
    )
    await router_service.route_logical_model(
        "router-code",
        {"messages": [{"role": "user", "content": "hello"}]},
        timeout_ms=30000,
        provider_toml=provider_toml,
    )

    assert FakeRouter.instances[-2].kwargs["routing_strategy"] == "latency-based-routing"
    assert FakeRouter.instances[-1].kwargs["routing_strategy"] == "cost-based-routing"
    assert FakeRouter.instances[-1].kwargs["num_retries"] == 3


@pytest.mark.asyncio
async def test_route_logical_model_cache_invalidates_cleanly(tmp_path, monkeypatch):
    provider_toml = _router_config(tmp_path)
    _prepare_env(monkeypatch, tmp_path)

    monkeypatch.setattr(router_service, "_load_router_class", lambda: FakeRouter)
    monkeypatch.setattr(
        router_service, "load_provider_config", lambda use_cache=True: provider_toml
    )
    router_service.invalidate_router_cache()
    FakeRouter.instances.clear()

    await router_service.route_logical_model(
        "router-cheap",
        {"messages": [{"role": "user", "content": "hello"}]},
        timeout_ms=30000,
    )
    await router_service.route_logical_model(
        "router-cheap",
        {"messages": [{"role": "user", "content": "hello"}]},
        timeout_ms=30000,
    )
    assert len(FakeRouter.instances) == 1

    router_service.invalidate_router_cache()

    await router_service.route_logical_model(
        "router-cheap",
        {"messages": [{"role": "user", "content": "hello"}]},
        timeout_ms=30000,
    )
    assert len(FakeRouter.instances) == 2


@pytest.mark.asyncio
async def test_dispatch_request_short_circuits_logical_models(monkeypatch):
    dispatcher = MagicMock()
    dispatcher._resolve_model_alias.return_value = ("openai", "gpt-4o-mini")
    dispatcher._candidate_order.return_value = ["openai"]
    monkeypatch.setattr(
        "api.providers.router_service.route_logical_model",
        AsyncMock(
            return_value={
                "ok": True,
                "provider": "router-cheap",
                "model": "qwen-turbo",
                "result": {"text": "from router"},
            }
        ),
    )

    result = await dispatch_request(
        dispatcher,
        pid="openai",
        model="router-cheap",
        payload={"messages": [{"role": "user", "content": "hello"}]},
        timeout_ms=30000,
        stream=False,
        logger=MagicMock(),
    )

    dispatcher._resolve_model_alias.assert_not_called()
    assert result["provider"] == "router-cheap"
    assert result["result"]["text"] == "from router"


@pytest.mark.asyncio
async def test_resolve_task_route_uses_heuristic_for_code_prompts(tmp_path, monkeypatch):
    provider_toml = _router_config(tmp_path)
    _prepare_env(monkeypatch, tmp_path)

    called = False

    async def _should_not_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("LLM fallback should not be used for obvious code prompts")

    monkeypatch.setattr(router_service, "route_logical_model", _should_not_run)

    decision = await router_service.resolve_task_route(
        {"messages": [{"role": "user", "content": "Write a function to parse JSON in Python."}]},
        timeout_ms=30000,
        provider_toml=provider_toml,
    )

    assert decision.task_class == "code"
    assert decision.logical_model == "router-code"
    assert decision.source == "heuristic"
    assert decision.confidence >= 0.8
    assert called is False


@pytest.mark.asyncio
async def test_resolve_task_route_escalates_ambiguous_prompts(tmp_path, monkeypatch):
    provider_toml = _router_config(tmp_path)
    _prepare_env(monkeypatch, tmp_path)

    async def _fake_route_logical_model(model, payload, **kwargs):
        assert model == "router-cheap"
        return {
            "ok": True,
            "provider": "router-cheap",
            "model": "qwen-turbo",
            "result": {
                "text": '{"class":"long-doc","confidence":0.91,"reason":"document-heavy"}',
                "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            },
            "routing": {
                "logical_model": "router-cheap",
                "backend_provider_id": "dashscope",
                "backend_litellm_model": "dashscope/qwen-turbo",
            },
        }

    monkeypatch.setattr(router_service, "route_logical_model", _fake_route_logical_model)

    decision = await router_service.resolve_task_route(
        {"messages": [{"role": "user", "content": "Can you help me with this?"}]},
        timeout_ms=30000,
        provider_toml=provider_toml,
    )

    assert decision.task_class == "long-doc"
    assert decision.logical_model == "router-reason"
    assert decision.source == "llm"
    assert decision.classifier_prompt_tokens == 12
    assert decision.classifier_completion_tokens == 4
    assert decision.classifier_backend_litellm_model == "dashscope/qwen-turbo"


@pytest.mark.asyncio
async def test_route_logical_model_auto_routes_by_task(tmp_path, monkeypatch):
    provider_toml = _router_config(tmp_path)
    _prepare_env(monkeypatch, tmp_path)

    monkeypatch.setattr(router_service, "_load_router_class", lambda: FakeRouter)
    monkeypatch.setattr(router_service, "_persist_routing_audit", AsyncMock())
    router_service.invalidate_router_cache()
    FakeRouter.instances.clear()

    response = await router_service.route_logical_model(
        "auto",
        {"messages": [{"role": "user", "content": "Write a function to parse JSON in Python."}]},
        timeout_ms=30000,
        provider_toml=provider_toml,
    )

    assert response is not None
    assert response["ok"] is True
    assert response["provider"] == "router-code"
    assert response["routing"]["task_routing"]["task_class"] == "code"
    assert response["routing"]["logical_model"] == "router-code"
    assert FakeRouter.instances[-1].kwargs["routing_strategy"] == "cost-based-routing"


@pytest.mark.asyncio
async def test_route_logical_model_kill_switch_falls_back_from_router_reason(tmp_path, monkeypatch):
    provider_toml = _router_config(tmp_path)
    _prepare_env(monkeypatch, tmp_path)
    monkeypatch.setenv("ROUTER_REASON_DAILY_SPEND_CAP_USD", "10")

    monkeypatch.setattr(router_service, "_load_router_class", lambda: FakeRouter)
    monkeypatch.setattr(
        router_service.usage_event_store,
        "get_total_spend_for_date",
        AsyncMock(return_value=12.5),
    )
    guard_event = MagicMock()
    monkeypatch.setattr(router_service, "record_router_cost_guard_event", guard_event)
    router_service.invalidate_router_cache()
    FakeRouter.instances.clear()

    response = await router_service.route_logical_model(
        "router-reason",
        {"messages": [{"role": "user", "content": "help me reason about this"}]},
        timeout_ms=30000,
        provider_toml=provider_toml,
    )

    assert response is not None
    assert response["provider"] == "router-code"
    assert response["routing"]["logical_model"] == "router-code"
    assert response["routing"]["cost_control"]["disabled"] is True
    guard_event.assert_called_once()


def test_normalize_vertex_credentials_survives_name_too_long(monkeypatch):
    """Regression test: inline JSON/base64 credential content is long enough
    to exceed a single path component's NAME_MAX on Linux (e.g. ext4's
    255-byte limit), so Path.exists() raises OSError[ENAMETOOLONG] instead
    of returning False. This previously propagated uncaught, breaking
    Vertex AI credential resolution in any Linux deployment even when the
    credential JSON itself was valid (reproduced on Render; not reproducible
    on macOS, where the same-length string doesn't trip the OS check)."""
    credentials_json = (
        '{"type": "authorized_user", "client_id": "test", '
        '"client_secret": "test", "refresh_token": "test"}'
    )

    def _raise_name_too_long(self):
        raise OSError(36, "File name too long")

    monkeypatch.setattr(router_service.Path, "exists", _raise_name_too_long)

    result = router_service._normalize_vertex_credentials(credentials_json)

    assert result == credentials_json
