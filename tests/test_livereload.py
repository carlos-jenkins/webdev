"""Tests for live-reload primitives."""

from __future__ import annotations

import asyncio

from webdev.livereload import CLIENT_SNIPLET, LIVERELOAD_PATH, ReloadHub


def test_snippet_references_endpoint() -> None:
    assert LIVERELOAD_PATH in CLIENT_SNIPLET
    assert "WebSocket" in CLIENT_SNIPLET


def test_hub_register_unregister() -> None:
    hub = ReloadHub()
    q = hub.register()
    assert hub.client_count == 1
    hub.unregister(q)
    assert hub.client_count == 0


def test_hub_broadcast() -> None:
    async def run() -> str:
        hub = ReloadHub()
        q = hub.register()
        hub.broadcast("reload")
        return await asyncio.wait_for(q.get(), timeout=1)

    assert asyncio.run(run()) == "reload"


def test_livereload_websocket_endpoint(tmp_path) -> None:
    from starlette.testclient import TestClient

    from webdev.config import Settings
    from webdev.server import create_app

    (tmp_path / "f.txt").write_text("x")
    settings = Settings(path=str(tmp_path), reload=True, qr=False).normalized()
    app = create_app(settings)
    with TestClient(app) as c, c.websocket_connect(LIVERELOAD_PATH) as ws:
        app.state.hub.broadcast("reload")
        assert ws.receive_text() == "reload"
