from __future__ import annotations

from api.providers.contracts import ProviderAdapter
from api.providers.dispatcher import dispatcher


def test_dispatcher_registry_providers_conform_to_adapter_protocol():
    providers = list(dispatcher._providers.items())
    assert providers, "Expected at least one initialized provider in dispatcher registry"
    for provider_id, provider in providers:
        assert isinstance(provider, ProviderAdapter), (
            f"Provider '{provider_id}' does not satisfy ProviderAdapter contract"
        )
