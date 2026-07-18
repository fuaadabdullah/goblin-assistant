"""Vulture false-positive whitelist.

Each attribute access below tells vulture that name is intentionally
unused — a parameter kept only to match a real call signature (interface
compliance for a stub/mock implementation), not dead code. Uses vulture's
own Whitelist helper so this file stays lint-clean and executable.
"""

from vulture.whitelists.whitelist_utils import Whitelist

_ = Whitelist()
_.results_count  # api.observability.retrieval_tracer.RetrievalTracer.end_trace
_.use_cache  # mirrors api.providers.provider_config_runtime.load_provider_config
