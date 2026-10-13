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
Live reload: watch the served tree and tell connected browsers to refresh.

Pieces:

* :class:`ReloadHub` — an in-process registry of connected WebSocket clients
  with a broadcast method.
* :func:`watch_tree` — a background task (started from the app lifespan) that
  runs :func:`watchfiles.awatch` over the served root and broadcasts a reload
  on every debounced change batch. Handles the ``--future`` case by watching the
  nearest existing ancestor until the root appears.
* :data:`LIVERELOAD_PATH` / :data:`CLIENT_SNIPLET` — the reserved WebSocket
  endpoint path and the auto-reconnecting client snippet injected into HTML.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from watchfiles import awatch

#: Reserved, collision-resistant path for the live-reload WebSocket endpoint.
LIVERELOAD_PATH = "/__webdev__/livereload"


class ReloadHub:
    """Tracks connected live-reload clients and broadcasts reload events."""

    def __init__(self) -> None:
        self._clients: set[asyncio.Queue[str]] = set()

    def register(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._clients.add(queue)
        return queue

    def unregister(self, queue: asyncio.Queue[str]) -> None:
        self._clients.discard(queue)

    def broadcast(self, message: str = "reload") -> None:
        for queue in list(self._clients):
            queue.put_nowait(message)

    @property
    def client_count(self) -> int:
        return len(self._clients)


def _nearest_existing(path: Path) -> Path:
    """Return *path* if it exists, else the closest existing ancestor."""
    current = path
    for candidate in (current, *current.parents):
        if candidate.exists():
            return candidate
    return Path(current.anchor or ".")


async def watch_tree(
    root: Path,
    hub: ReloadHub,
    stop_event: asyncio.Event,
) -> None:
    """
    Watch *root* and broadcast a reload on every change batch.

    If *root* does not exist yet (``--future``), watch the nearest existing
    ancestor so that the directory's eventual creation is observed; the watcher
    is then restarted targeting *root* once it appears.
    """
    while not stop_event.is_set():
        target = root if root.exists() else _nearest_existing(root)
        try:
            async for _changes in awatch(
                target,
                stop_event=stop_event,
            ):
                hub.broadcast()
                # If we were watching an ancestor and the root now exists,
                # break to restart the watcher on the real root.
                if target != root and root.exists():
                    break
        except FileNotFoundError:
            # The watched path vanished; wait briefly and re-resolve.
            await asyncio.sleep(0.5)
        if stop_event.is_set():
            break
        # Small debounce before (potentially) re-targeting the watcher.
        await asyncio.sleep(0.1)


#: Auto-reconnecting client snippet injected before </body> of HTML responses.
CLIENT_SNIPLET = """
<script>
(function () {
  var path = "__LIVERELOAD_PATH__";
  var proto = location.protocol === "https:" ? "wss" : "ws";
  var wasConnected = false;
  function connect() {
    var ws = new WebSocket(proto + "://" + location.host + path);
    ws.onopen = function () {
      if (wasConnected) { location.reload(); return; }
      wasConnected = true;
    };
    ws.onmessage = function (event) {
      if (event.data === "reload") { location.reload(); }
    };
    ws.onclose = function () { setTimeout(connect, 1000); };
    ws.onerror = function () { try { ws.close(); } catch (e) {} };
  }
  connect();
})();
</script>
""".replace("__LIVERELOAD_PATH__", LIVERELOAD_PATH)
