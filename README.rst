======================
Development Web Server
======================

About
=====

``webdev`` is a small, fast development web server. It serves any local
directory over HTTP (or HTTPS) with developer-friendly conveniences, and ships
a modern, dark-themed directory index.

It is built on `Starlette <https://www.starlette.io/>`_ and
`Uvicorn <https://www.uvicorn.org/>`_ (an ASGI stack), and requires Python 3.10+.

Features
========

- **Serve any directory** — passed as the first positional argument; defaults to
  the current directory.
- **Graceful when the folder disappears** — responds with ``404`` instead of
  crashing if the served directory is removed, and **recovers automatically**
  the moment it is recreated. Paths are resolved against the live filesystem on
  every request, which is great with build systems that perform clean/rebuild
  actions.
- **Automatic port selection** — if the base port is busy, the next free port in
  a range is used. Can be forced to a single port.
- **Serve a not-yet-existing folder** — ``--future`` assumes the folder will be
  created later.
- **Modern dark directory index** — breadcrumbs, file-type icons, human-readable
  sizes, modified dates and client-side sortable columns. Themable: drop a new
  directory under ``webdev/templates/<theme>/``.
- **Live reload** — connected browsers refresh automatically on file changes
  (via a WebSocket; a tiny auto-reconnecting snippet is injected into HTML).
- **No-cache headers** for always-fresh development content.
- **SPA fallback** — optionally serve ``index.html`` for unknown routes.
- **Gzip**, **CORS**, optional **HTTPS** (self-signed if no cert/key is given),
  and a startup **QR code / LAN URL** for quick mobile testing.
- **Config file** — every option can be set via ``webdev.toml`` (or a
  ``[tool.webdev]`` table). Precedence: CLI flag > config file > default.

Installation
============

::

   pip install webdev

Usage
=====

::

   $ webdev --help
   usage: webdev [-h] [-v] [--version] [-i IP] [-p PORT] [-f] [-r RANGE] [-u]
                 [--reload | --no-reload] [--cache] [--no-cache]
                 [--spa | --no-spa] [--gzip | --no-gzip] [--cors | --no-cors]
                 [--qr | --no-qr] [--https | --no-https] [--cert CERT]
                 [--key KEY] [--theme THEME] [--config CONFIG]
                 [path]

Examples::

   # Serve the current directory on http://localhost:8080
   webdev

   # Serve ./public on a forced port, over HTTPS, without live reload
   webdev -p 3000 -f --https --no-reload ./public

   # Single-page app: fall back to index.html for client-side routes
   webdev --spa ./dist

Options and config keys
-----------------------

Every option has both a CLI flag and a config-file key. Booleans accept
``--x`` / ``--no-x``.

=====================  ========================  ==================  ==========
Feature                CLI flag                  Config key          Default
=====================  ========================  ==================  ==========
Serve path             positional ``path``       ``path``            CWD
Bind IP                ``-i/--ip``               ``ip``              0.0.0.0
Base port              ``-p/--port``             ``port``            8080
Force exact port       ``-f/--force-port``       ``force_port``      false
Port range             ``-r/--range``            ``range``           20
Serve missing folder   ``-u/--future``           ``future``          false
No-cache headers       ``--no-cache/--cache``    ``no_cache``        enabled
Live reload            ``--reload/--no-reload``  ``reload``          enabled
SPA fallback           ``--spa/--no-spa``        ``spa``             disabled
Gzip                   ``--gzip/--no-gzip``      ``gzip``            enabled
CORS                   ``--cors/--no-cors``      ``cors``            disabled
QR / LAN URL           ``--qr/--no-qr``          ``qr``              enabled
HTTPS/TLS              ``--https/--no-https``    ``https``           disabled
TLS cert / key         ``--cert`` / ``--key``    ``cert`` / ``key``  self-signed
Index theme            ``--theme``               ``theme``           dark
=====================  ========================  ==================  ==========

Example ``webdev.toml``::

   port = 3000
   force_port = true
   spa = true
   cors = true

Design notes
============

- **Framework:** Starlette + Uvicorn was chosen over a full framework such as
  Sanic because this is a static file server: Starlette provides exactly the
  primitives needed (routing, static serving, WebSockets, middleware) with a
  small surface, and Uvicorn handles fast binding, HTTP keep-alive, HTTPS and
  graceful shutdown.
- **The legacy reload hack is gone.** The old server patched ``send_head`` to
  ``chdir`` back into the served folder; modern ``http.server`` captures the
  working directory in the handler constructor, so that hook stopped running and
  a removed folder crashed the request. ``webdev`` now resolves every request
  against the live filesystem, so missing folders yield a real ``404`` and
  recover automatically.

Development
===========

The development workflow is driven by `tox <https://tox.wiki/>`_ using
`uv <https://docs.astral.sh/uv/>`_ as the backend (via ``tox-uv``). ``uv`` is the
only tool you need preinstalled::

   # Lint, format-check and type-check
   tox -e style

   # Run the test suite
   tox -e test

   # Build and verify the distribution
   tox -e build

Each environment declares its own tooling dependencies in ``tox.ini`` so it
installs only what it needs.

Changelog
=========

2.0.0
-----

**Reimplemented** on a modern async stack (Starlette + Uvicorn), Python 3.10+.

**New**

- Modern dark, themable directory index (breadcrumbs, icons, sizes, dates,
  sortable columns), rendered with Jinja2.
- Live reload over WebSocket.
- No-cache headers, SPA fallback, gzip, CORS, optional HTTPS (self-signed),
  startup QR code / LAN URL.
- Config-file support (``webdev.toml`` / ``[tool.webdev]``); every option has a
  CLI flag and a config key (precedence CLI > config > default).
- ``pyproject.toml`` packaging; tox + uv development workflow; Ruff, mypy and a
  pytest suite.

**Fixed**

- The directory auto-recovery feature, which silently broke on modern Python
  when ``http.server`` began capturing the working directory in the request
  handler constructor. Path resolution is now per-request against the live
  filesystem.

**Changed**

- Dropped Python 2 support.

1.1.0
-----

**New**

- Added support for Python 3 (issue #5).
- Added support for incremental automatic port selection (issue #2).
- Added the ``--future`` flag that allows the webserver to serve a non-existent
  folder, assuming it will be created in the future (issue #3).

**Changed**

- Ctrl+C is now handled (issue #4).

1.0.0
-----

- Initial release.

License
=======

::

   Copyright (C) 2015-2026 Carlos Jenkins <carlos@jenkins.co.cr>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing,
   software distributed under the License is distributed on an
   "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
   KIND, either express or implied.  See the License for the
   specific language governing permissions and limitations
   under the License.
