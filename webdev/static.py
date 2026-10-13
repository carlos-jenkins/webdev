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
Per-request static file resolution.

The core fix over the legacy server: paths are resolved against the **live
filesystem on every request** instead of relying on the process working
directory. A missing served directory therefore yields a real ``404`` and
recovers automatically the instant the directory reappears.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

#: Candidate index file names auto-served for a directory.
INDEX_FILENAMES = ("index.html", "index.htm")

#: Extra extension -> MIME mappings the stdlib ``mimetypes`` module omits.
#: Registered so common dev/config/source files render inline instead of being
#: downloaded as ``application/octet-stream``.
EXTRA_MIME_TYPES = {
    ".toml": "text/plain",
    ".ini": "text/plain",
    ".cfg": "text/plain",
    ".conf": "text/plain",
    ".lock": "text/plain",
    ".log": "text/plain",
    ".env": "text/plain",
    ".properties": "text/plain",
    ".rst": "text/plain",
    ".tsx": "text/plain",
    ".jsx": "text/plain",
    ".vue": "text/plain",
    ".svelte": "text/plain",
    ".yml": "text/plain",
    ".yaml": "text/plain",
}

#: Number of bytes inspected when sniffing whether an unknown file is text.
_SNIFF_BYTES = 8192


def register_mime_types() -> None:
    """Register :data:`EXTRA_MIME_TYPES` with the stdlib ``mimetypes`` module."""
    for ext, media_type in EXTRA_MIME_TYPES.items():
        mimetypes.add_type(media_type, ext)


register_mime_types()


def _looks_like_text(path: Path) -> bool:
    """Heuristically decide whether *path* holds UTF-8 text (no NUL bytes)."""
    try:
        with path.open("rb") as fd:
            chunk = fd.read(_SNIFF_BYTES)
    except OSError:
        return False
    if b"\x00" in chunk:
        return False
    try:
        chunk.decode("utf-8")
    except UnicodeDecodeError:
        # A truncated multi-byte sequence at the boundary is still fine.
        try:
            chunk[: chunk.rfind(b" ") + 1 or len(chunk)].decode("utf-8")
        except UnicodeDecodeError:
            return False
    return True


def guess_media_type(path: Path) -> str:
    """
    Resolve a response ``Content-Type`` for *path*.

    Uses the stdlib ``mimetypes`` registry (augmented by
    :func:`register_mime_types`). For still-unknown extensions, sniffs the file
    and falls back to ``text/plain`` when it looks like text, otherwise
    ``application/octet-stream`` — so arbitrary text files preview inline while
    binaries still download.
    """
    media_type, _encoding = mimetypes.guess_type(path.name)
    if media_type:
        return media_type
    if _looks_like_text(path):
        return "text/plain"
    return "application/octet-stream"


#: Headers that disable caching for fresh dev content.
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


class ResolvedPath:
    """Result of resolving a URL path against the served root."""

    __slots__ = ("fs_path", "is_dir", "escapes")

    def __init__(self, fs_path: Path | None, is_dir: bool, escapes: bool) -> None:
        self.fs_path = fs_path
        self.is_dir = is_dir
        self.escapes = escapes


def resolve_fs_path(root: Path, url_path: str) -> ResolvedPath:
    """
    Resolve *url_path* (the request path) to a filesystem path under *root*.

    Returns a :class:`ResolvedPath`. ``escapes`` is ``True`` when the request
    attempted to traverse outside *root* (the caller should reject with 404).
    ``fs_path`` is ``None`` when the target does not exist.
    """
    # Normalise: strip leading slash, decode nothing here (Starlette already
    # provides a decoded path), collapse via Path semantics.
    relative = url_path.lstrip("/")
    root_resolved = root.resolve(strict=False)
    candidate = (root_resolved / relative).resolve(strict=False)

    # Traversal safety: the resolved candidate must live under the root.
    if candidate != root_resolved and root_resolved not in candidate.parents:
        return ResolvedPath(None, False, escapes=True)

    if not candidate.exists():
        return ResolvedPath(None, False, escapes=False)

    return ResolvedPath(candidate, candidate.is_dir(), escapes=False)


def find_index_file(directory: Path) -> Path | None:
    """Return the first existing index file inside *directory*, if any."""
    for name in INDEX_FILENAMES:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None
