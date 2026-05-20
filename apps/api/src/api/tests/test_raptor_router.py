import pytest

import api.raptor_router as raptor


@pytest.mark.asyncio
async def test_raptor_start_stop_status_logs_demo(tmp_path, monkeypatch):
    raptor.RAPTOR_STATE["running"] = False

    started = await raptor.raptor_start()
    assert started == {"running": True}
    assert raptor.RAPTOR_STATE["running"] is True

    status = await raptor.raptor_status()
    assert status["running"] is True
    assert status["config_file"] == "config/providers.toml"

    stopped = await raptor.raptor_stop()
    assert stopped == {"running": False}
    assert raptor.RAPTOR_STATE["running"] is False

    monkeypatch.chdir(tmp_path)
    missing = await raptor.raptor_logs(raptor.LogsRequest(max_chars=10))
    assert "Log file not found" in missing["log_tail"]

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "raptor.log").write_text("0123456789abcdef")
    tail = await raptor.raptor_logs(raptor.LogsRequest(max_chars=4))
    assert tail["log_tail"] == "cdef"

    ok = await raptor.raptor_demo("hello")
    assert ok == {"result": "Demo executed with value: hello"}


@pytest.mark.asyncio
async def test_raptor_demo_boom_raises_http_exception():
    with pytest.raises(raptor.HTTPException):
        await raptor.raptor_demo("boom")
