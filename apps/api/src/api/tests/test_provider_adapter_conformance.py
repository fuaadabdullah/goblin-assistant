from __future__ import annotations

from api.providers.contracts import ProviderAdapter
from api.providers.dispatcher import dispatcher


def test_dispatcher_registry_providers_conform_to_adapter_protocol():
    provider_ids = dispatcher.provider_ids(include_hidden=True)
    providers = []
    for provider_id in provider_ids:
        try:
            providers.append(
                (provider_id, dispatcher.get_provider(provider_id))
            )
        except KeyError:
            continue

    assert providers, (
        "Expected at least one provider available through dispatcher"
    )
    for provider_id, provider in providers:
        assert isinstance(provider, ProviderAdapter), (
            f"Provider '{provider_id}' does not satisfy "
            "ProviderAdapter contract"
        )
