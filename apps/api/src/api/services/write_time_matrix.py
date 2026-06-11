"""Backward-compatibility shim for write_time_matrix → write_time_intelligence rename.

Import from api.services.write_time_intelligence instead.
"""

# Re-exports the matrix plus its deps (embedding_worker, cache_service, ...)
from .write_time_decision_matrix import *  # noqa: F401, F403
from .write_time_intelligence import *  # noqa: F401, F403
from .write_time_intelligence import WriteTimeDecisionMatrix, write_time_intelligence  # noqa: F401
