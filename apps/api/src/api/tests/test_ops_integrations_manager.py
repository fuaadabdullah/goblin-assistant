import pytest

from api.ops.integrations import MonitoringManager


class _OkIntegration:
    enabled = True
    config = {"api_key": "secret", "non_secret": "ok"}

    async def send_metrics(self, metrics):
        return True

    async def send_alert(self, alert):
        return True


class _FailMetricsIntegration:
    enabled = True
    config = {}

    async def send_metrics(self, metrics):
        raise RuntimeError("boom")

    async def send_alert(self, alert):
        return False


@pytest.mark.asyncio
async def test_monitoring_manager_dispatch_and_status_masking() -> None:
    manager = MonitoringManager()
    manager.integrations = {
        "ok": _OkIntegration(),
        "fail": _FailMetricsIntegration(),
    }

    metric_results = await manager.send_metrics({"health": {"overall_score": 90}})
    alert_results = await manager.send_alert({"title": "x"})
    status = await manager.get_status()

    assert metric_results["ok"] is True
    assert metric_results["fail"] is False
    assert alert_results["ok"] is True
    assert alert_results["fail"] is False
    assert status["ok"]["config"]["api_key"] == "****"
    assert status["ok"]["config"]["non_secret"] == "ok"
