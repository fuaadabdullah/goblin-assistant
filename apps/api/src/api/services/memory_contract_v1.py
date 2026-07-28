"""Versioned memory contract serializer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from .memory_contract_input import MemoryFactInput


class MemoryContractVersion(str, Enum):
    V1 = "1.0"


@dataclass(frozen=True, slots=True)
class MemoryContractV1:
    """Serializer for the current canonical memory contract."""

    @classmethod
    def build_payload(cls, normalized: MemoryFactInput) -> Dict[str, Any]:
        payload = normalized.to_payload_dict()
        payload["schema_version"] = MemoryContractVersion.V1.value
        return payload
