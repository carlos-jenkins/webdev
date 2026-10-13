# Copyright (C) 2026 KuraLabs S.R.L <info@kuralabs.io>
# Copyright (C) 2015-2016 Carlos Jenkins <carlos@jenkins.co.cr>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
Starlette application factory and Uvicorn runner.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    Response,
)
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from .config import Settings
from .index import render_index, validate_theme
from .livereload import (
    CLIENT_SNIPLET,
    LIVERELOAD_PATH,
    ReloadHub,
    watch_tree,
)
from .static import (
    NO_CACHE_HEADERS,
    find_index_file,
    guess_media_type,
    resolve_fs_path,
)

log = logging.getLogger("webdev")

_HTML_SUFFIXES = (".html", ".htm")


def _inject_livereload(html: bytes, enabled: bool) -> bytes:
    """Inject the reload snippet before ``</body>`` (or append) when enabled."""
    if not enabled:
        return html
    snippet = CLIENT_SNIPLET.encode("utf-8")
    lowered = html.lower()
    idx = lowered.rfind(b"</body>")
    if idx != -1:
        return html[:idx] + snippet + html[idx:]
    return html + snippet


def _cache_headers(settings: Settings) -> dict[str, str]:
    return dict(NO_CACHE_HEADERS) if settings.no_cache else {}


def _not_found(settings: Settings) -> Response:
    return Response("404 Not Found", status_code=404, media_type="text/plain")


def _html_response(
    body: bytes, settings: Settings, status_code: int = 200
) -> HTMLResponse:
    body = _inject_livereload(body, settings.reload)
    return HTMLResponse(body, status_code=status_code, headers=_cache_headers(settings))


async def _serve_file(path: Path, settings: Settings) -> Response:
    """Serve a regular file, injecting live-reload JS into HTML documents."""
    if path.suffix.lower() in _HTML_SUFFIXES:
        try:
            body = path.read_bytes()
        except OSError:
            return _not_found(settings)
        return _html_response(body, settings)
    return FileResponse(
        path,
        media_type=guess_media_type(path),
        headers=_cache_headers(settings),
    )


async def _serve_directory(
    request: Request, fs_dir: Path, settings: Settings
) -> Response:
    url_path = request.url.path
    # Ensure a trailing slash so relative links resolve correctly.
    if not url_path.endswith("/"):
        return RedirectResponse(url_path + "/", status_code=308)

    index_file = find_index_file(fs_dir)
    if index_file is not None:
        return await _serve_file(index_file, settings)

    html = render_index(
        fs_dir=fs_dir,
        url_path=url_path,
        served_root=Path(settings.path),
        theme=settings.theme,
        live_reload=settings.reload,
    )
    return _html_response(html.encode("utf-8"), settings)


async def _handle(request: Request) -> Response:
    settings: Settings = request.app.state.settings
    root = Path(settings.path)
    resolved = resolve_fs_path(root, request.url.path)

    if resolved.escapes:
        return _not_found(settings)

    if resolved.fs_path is None:
        # SPA fallback: serve the root index.html for unknown routes.
        if settings.spa:
            index_file = find_index_file(root)
            if index_file is not None:
                return await _serve_file(index_file, settings)
        return _not_found(settings)

    if resolved.is_dir:
        return await _serve_directory(request, resolved.fs_path, settings)

    return await _serve_file(resolved.fs_path, settings)


async def _drain(websocket: WebSocket) -> None:
    """Consume inbound frames so client disconnects are detected."""
    with contextlib.suppress(WebSocketDisconnect):
        while True:
            await websocket.receive_text()


async def _livereload_endpoint(websocket: WebSocket) -> None:
    hub: ReloadHub = websocket.app.state.hub
    await websocket.accept()
    queue = hub.register()
    receiver = asyncio.create_task(_drain(websocket))
    try:
        while True:
            getter = asyncio.create_task(queue.get())
            done, _pending = await asyncio.wait(
                {getter, receiver}, return_when=asyncio.FIRST_COMPLETED
            )
            if receiver in done:
                getter.cancel()
                break
            message = getter.result()
            await websocket.send_text(message)
    except WebSocketDisconnect:
        pass
    finally:
        receiver.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await receiver
        hub.unregister(queue)


def _build_lifespan(settings: Settings):
    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        app.state.settings = settings
        app.state.hub = ReloadHub()
        stop_event = asyncio.Event()
        watcher: asyncio.Task | None = None
        if settings.reload:
            watcher = asyncio.create_task(
                watch_tree(Path(settings.path), app.state.hub, stop_event)
            )
        try:
            yield
        finally:
            stop_event.set()
            if watcher is not None:
                watcher.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await watcher

    return lifespan


def create_app(settings: Settings) -> Starlette:
    """Build the Starlette application for the given *settings*."""
    validate_theme(settings.theme)

    routes: list = []
    if settings.reload:
        routes.append(WebSocketRoute(LIVERELOAD_PATH, _livereload_endpoint))
    routes.append(Route("/{path:path}", _handle, methods=["GET", "HEAD"]))

    middleware: list[Middleware] = []
    if settings.cors:
        middleware.append(
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
            )
        )
    if settings.gzip:
        middleware.append(Middleware(GZipMiddleware, minimum_size=500))

    app = Starlette(
        routes=routes,
        middleware=middleware,
        lifespan=_build_lifespan(settings),
    )
    app.state.settings = settings
    return app
