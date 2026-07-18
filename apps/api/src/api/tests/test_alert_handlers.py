from __future__ import annotations

from api.observability.alert_handlers import DEFAULT_ALERT_HANDLERS, register_default_alert_handlers


class _AlertSystemStub:
    def __init__(self) -> None:
        self.callbacks = []

    def register_alert_callback(self, callback):
        self.callbacks.append(callback)


def test_default_alert_handlers_register_as_plugins():
    system = _AlertSystemStub()

    register_default_alert_handlers(system)

    assert system.callbacks == list(DEFAULT_ALERT_HANDLERS)
