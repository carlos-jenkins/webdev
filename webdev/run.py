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
High-level runner: select a port, build the app, print the banner and start
Uvicorn (optionally over HTTPS).
"""

from __future__ import annotations

import logging

import uvicorn

from .config import Settings
from .net import NoFreePortError, build_urls, find_free_port, render_qr
from .server import create_app
from .tls import ensure_tls_files

log = logging.getLogger("webdev")


def _print_banner(settings: Settings, port: int) -> None:
    urls = build_urls(settings.ip, port, settings.https)
    print(f"WebDev {_version()} serving {settings.path}")
    print(f"Bound to {settings.ip}:{port}")
    for url in urls:
        print(f"  -> {url}")
    if settings.qr and urls:
        qr = render_qr(urls[-1])
        if qr:
            print(qr)
    print("Press Ctrl+C to stop.")


def _version() -> str:
    from . import __version__

    return __version__


def serve(settings: Settings) -> int:
    """Resolve a port, build the app and run the server. Returns an exit code."""
    settings = settings.normalized()

    try:
        port = find_free_port(settings.ip, settings.port, settings.range)
    except NoFreePortError as error:
        log.error(str(error))
        return 1

    cert_file: str | None = None
    key_file: str | None = None
    if settings.https:
        from .tls import TLSUnavailableError

        try:
            cert_file, key_file = ensure_tls_files(settings.cert, settings.key)
        except TLSUnavailableError as error:
            log.error(str(error))
            return 1

    app = create_app(settings)

    _print_banner(settings, port)

    log_level = (
        "debug"
        if settings.verbose >= 3
        else ("info" if settings.verbose >= 2 else "warning")
    )

    config = uvicorn.Config(
        app,
        host=settings.ip,
        port=port,
        log_level=log_level,
        access_log=settings.verbose >= 2,
        ssl_certfile=cert_file,
        ssl_keyfile=key_file,
    )
    server = uvicorn.Server(config)
    try:
        server.run()
    except KeyboardInterrupt:  # pragma: no cover - handled by uvicorn too
        print("Good bye!")
    return 0
