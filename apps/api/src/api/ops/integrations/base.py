"""Base contracts for monitoring integrations."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class MonitoringIntegration(ABC):
    """Base class for monitoring system integrations."""

    def __init__(self, name: str):
        self.name = name
        self.enabled = False
        self.config = {}

    async def initialize(self, config: Dict[str, Any]) -> bool:
        self.config = config
        self.enabled = config.get("enabled", False)
        return self.enabled

    @abstractmethod
    async def send_metrics(self, metrics: Dict[str, Any]) -> bool: ...

    @abstractmethod
    async def send_alert(self, alert: Dict[str, Any]) -> bool: ...
