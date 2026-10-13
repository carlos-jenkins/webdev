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
Networking helpers: incremental port selection, LAN address detection and QR.
"""

from __future__ import annotations

import socket
from errno import EADDRINUSE


class NoFreePortError(Exception):
    """Raised when no free port is found in the requested range."""

    def __init__(self, start: int, end: int) -> None:
        self.start = start
        self.end = end
        super().__init__(f"Port(s) {start} - {end} already in use.")


def find_free_port(ip: str, base_port: int, port_range: int) -> int:
    """
    Return the first bindable port in ``[base_port, base_port + port_range]``.

    A port is considered free if we can bind a TCP socket to it on *ip*. The
    probe socket is closed immediately; the caller binds the real server right
    after. ``SO_REUSEADDR`` is set to match Uvicorn's own bind behaviour: on
    Linux it lets us reclaim a port still lingering in ``TIME_WAIT`` from a
    previous run (common right after Ctrl+C with keep-alive clients) while still
    reporting a port actively held by another ``LISTEN``ing process as busy.

    Raises :class:`NoFreePortError` if the whole range is occupied.
    """
    last = base_port + port_range
    for port in range(base_port, last + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((ip, port))
            except OSError as error:
                if error.errno != EADDRINUSE:
                    raise
                continue
            return port
    raise NoFreePortError(base_port, last)


def detect_lan_ip() -> str | None:
    """
    Best-effort detection of the primary LAN IPv4 address.

    Uses a connected UDP socket to a public address to learn which local
    interface the OS would route through. No packets are actually sent. Returns
    ``None`` if detection fails or only loopback is available.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
    except OSError:
        return None
    if not ip or ip.startswith("127."):
        return None
    return ip


def build_urls(bind_ip: str, port: int, https: bool) -> list[str]:
    """Return human-friendly URLs to reach the server."""
    scheme = "https" if https else "http"
    urls: list[str] = []
    if bind_ip in ("0.0.0.0", "::"):
        urls.append(f"{scheme}://127.0.0.1:{port}")
        lan = detect_lan_ip()
        if lan:
            urls.append(f"{scheme}://{lan}:{port}")
    else:
        urls.append(f"{scheme}://{bind_ip}:{port}")
    return urls


def render_qr(url: str) -> str | None:
    """
    Render *url* as an ASCII QR code suitable for a terminal.

    Returns ``None`` if the optional ``qrcode`` dependency is unavailable.
    """
    try:
        import io

        import qrcode
    except ModuleNotFoundError:  # pragma: no cover
        return None

    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    buffer = io.StringIO()
    qr.print_ascii(out=buffer, invert=True)
    return buffer.getvalue()
