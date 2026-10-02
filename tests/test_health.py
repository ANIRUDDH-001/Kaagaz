from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import FakePush, FakeTemporal, mock_store


def test_health_reports_mode_and_backends(monkeypatch):
    monkeypatch.setenv("APP_MODE", "demo")
    monkeypatch.setenv("TTS_BACKEND", "browser")
    from app.config import get_settings
    get_settings.cache_clear()
    app = create_app(store=mock_store(), temporal=FakeTemporal(), push=FakePush(), start_workers=False)
    with TestClient(app) as c:
        body = c.get("/api/health").json()
    assert body["ok"] is True
    assert body["mode"] == "demo"
    assert body["tts"] == "browser"
    assert "push_key" in body
