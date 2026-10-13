"""End-to-end-ish tests against the Starlette app via TestClient."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from starlette.testclient import TestClient

from webdev.config import Settings
from webdev.server import create_app


def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


def test_serves_file(settings: Settings) -> None:
    with client(settings) as c:
        resp = c.get("/hello.txt")
    assert resp.status_code == 200
    assert resp.text == "hello world"


def test_directory_index_rendered(settings: Settings) -> None:
    with client(settings) as c:
        resp = c.get("/")
    assert resp.status_code == 200
    assert "Index of" in resp.text
    assert "hello.txt" in resp.text
    assert 'data-theme="dark"' in resp.text


def test_directory_redirects_to_trailing_slash(settings: Settings) -> None:
    with client(settings) as c:
        resp = c.get("/sub", follow_redirects=False)
    assert resp.status_code == 308
    assert resp.headers["location"] == "/sub/"


def test_missing_returns_404(settings: Settings) -> None:
    with client(settings) as c:
        resp = c.get("/missing.txt")
    assert resp.status_code == 404


def test_graceful_recovery(settings: Settings, served_dir: Path) -> None:
    import shutil

    with client(settings) as c:
        assert c.get("/hello.txt").status_code == 200
        shutil.rmtree(served_dir)
        assert c.get("/hello.txt").status_code == 404
        served_dir.mkdir()
        (served_dir / "hello.txt").write_text("back")
        resp = c.get("/hello.txt")
    assert resp.status_code == 200
    assert resp.text == "back"


def test_traversal_blocked(settings: Settings) -> None:
    with client(settings) as c:
        resp = c.get("/../../etc/passwd")
    assert resp.status_code == 404


def test_no_cache_headers(settings: Settings) -> None:
    with client(settings) as c:
        resp = c.get("/hello.txt")
    assert "no-store" in resp.headers["cache-control"]


def test_cache_allowed_when_disabled(settings: Settings) -> None:
    s = replace(settings, no_cache=False)
    with client(s) as c:
        resp = c.get("/hello.txt")
    assert "cache-control" not in resp.headers


def test_spa_fallback(settings: Settings, served_dir: Path) -> None:
    (served_dir / "index.html").write_text("<html><body>app</body></html>")
    s = replace(settings, spa=True)
    with client(s) as c:
        resp = c.get("/some/client/route")
    assert resp.status_code == 200
    assert "app" in resp.text


def test_no_spa_fallback_is_404(settings: Settings, served_dir: Path) -> None:
    (served_dir / "index.html").write_text("<html><body>app</body></html>")
    with client(settings) as c:
        resp = c.get("/some/client/route")
    assert resp.status_code == 404


def test_livereload_snippet_injected(settings: Settings) -> None:
    s = replace(settings, reload=True)
    with client(s) as c:
        resp = c.get("/page.html")
    assert "__webdev__/livereload" in resp.text


def test_no_snippet_when_reload_off(settings: Settings) -> None:
    with client(settings) as c:
        resp = c.get("/page.html")
    assert "__webdev__/livereload" not in resp.text


def test_cors_header(settings: Settings) -> None:
    s = replace(settings, cors=True)
    with client(s) as c:
        resp = c.get("/hello.txt", headers={"origin": "http://example.com"})
    assert resp.headers["access-control-allow-origin"] == "*"


def test_toml_served_as_text(settings: Settings, served_dir: Path) -> None:
    (served_dir / "config.toml").write_text("key = 1\n")
    with client(settings) as c:
        resp = c.get("/config.toml")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
