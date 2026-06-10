"""Backward-compatibility shim for write_time_matrix → write_time_intelligence rename.

Import from api.services.write_time_intelligence instead.
"""

from .write_time_intelligence import *  # noqa: F401, F403
from .write_time_intelligence import WriteTimeDecisionMatrix, write_time_intelligence  # noqa: F401
