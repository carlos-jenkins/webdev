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
Directory index rendering.

Builds the template context from a filesystem directory and renders it with a
themed Jinja2 template. Templates live under ``webdev/templates/<theme>/`` and
are shipped as package data, so new themes are added by dropping in a new
sibling directory — no code changes required.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from importlib import resources
from pathlib import Path, PurePosixPath

from jinja2 import Environment, PackageLoader, select_autoescape

#: Template package and root directory inside this package.
_TEMPLATE_PACKAGE = "webdev"
_TEMPLATE_DIR = "templates"

_INDEX_TEMPLATE = "index.html.jinja2"


class ThemeNotFoundError(Exception):
    """Raised when a requested theme directory does not exist."""

    def __init__(self, theme: str, available: list[str]) -> None:
        self.theme = theme
        self.available = available
        choices = ", ".join(available) if available else "(none found)"
        super().__init__(f"Unknown theme {theme!r}. Available themes: {choices}.")


@dataclass(frozen=True)
class Entry:
    """A single directory entry for the index listing."""

    name: str
    href: str
    is_dir: bool
    size: int | None
    size_human: str
    mtime: float
    mtime_human: str
    icon: str


@lru_cache(maxsize=1)
def _environment() -> Environment:
    return Environment(
        loader=PackageLoader(_TEMPLATE_PACKAGE, _TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml", "jinja2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def available_themes() -> list[str]:
    """Return the sorted list of bundled theme names."""
    root = resources.files(_TEMPLATE_PACKAGE).joinpath(_TEMPLATE_DIR)
    themes = []
    for item in root.iterdir():
        name = item.name
        if item.is_dir() and not name.startswith("_"):
            themes.append(name)
    return sorted(themes)


def validate_theme(theme: str) -> None:
    """Raise :class:`ThemeNotFoundError` if *theme* is not available."""
    themes = available_themes()
    if theme not in themes:
        raise ThemeNotFoundError(theme, themes)


def human_size(num_bytes: int) -> str:
    """Format a byte count as a short human-readable string."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024.0 or unit == "PB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"  # pragma: no cover


def _icon_for(name: str, is_dir: bool) -> str:
    """Return a coarse icon class/name based on the entry type/extension."""
    if is_dir:
        return "dir"
    ext = Path(name).suffix.lower().lstrip(".")
    mapping = {
        "image": {"png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "bmp"},
        "video": {"mp4", "webm", "mov", "avi", "mkv"},
        "audio": {"mp3", "wav", "ogg", "flac", "m4a"},
        "code": {
            "py",
            "js",
            "ts",
            "jsx",
            "tsx",
            "c",
            "h",
            "cpp",
            "go",
            "rs",
            "java",
            "rb",
            "sh",
            "css",
            "html",
            "json",
            "yaml",
            "yml",
            "toml",
            "xml",
        },
        "archive": {"zip", "tar", "gz", "bz2", "xz", "7z", "rar"},
        "doc": {"pdf", "md", "rst", "txt", "doc", "docx", "odt"},
    }
    for icon, extensions in mapping.items():
        if ext in extensions:
            return icon
    return "file"


def _breadcrumbs(rel_path: str) -> list[dict[str, str]]:
    """Build breadcrumb segments (name + href) for *rel_path*."""
    crumbs: list[dict[str, str]] = [{"name": "/", "href": "/"}]
    accumulated = PurePosixPath("/")
    for part in PurePosixPath(rel_path).parts:
        if part in ("", "/"):
            continue
        accumulated = accumulated / part
        href = str(accumulated)
        if not href.endswith("/"):
            href += "/"
        crumbs.append({"name": part, "href": href})
    return crumbs


def list_directory(fs_dir: Path, url_path: str) -> list[Entry]:
    """Build the sorted list of :class:`Entry` for *fs_dir*."""
    base = url_path if url_path.endswith("/") else url_path + "/"
    entries: list[Entry] = []
    with os.scandir(fs_dir) as iterator:
        for item in iterator:
            try:
                is_dir = item.is_dir()
                stat = item.stat()
            except OSError:
                continue
            size = None if is_dir else stat.st_size
            name = item.name
            href = base + name + ("/" if is_dir else "")
            entries.append(
                Entry(
                    name=name,
                    href=href,
                    is_dir=is_dir,
                    size=size,
                    size_human="" if size is None else human_size(size),
                    mtime=stat.st_mtime,
                    mtime_human=datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    icon=_icon_for(name, is_dir),
                )
            )
    entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
    return entries


def render_index(
    *,
    fs_dir: Path,
    url_path: str,
    served_root: Path,
    theme: str,
    live_reload: bool,
) -> str:
    """Render the directory index HTML for *fs_dir*."""
    from . import __version__

    rel = url_path.strip("/")
    entries = list_directory(fs_dir, url_path)
    template = _environment().get_template(f"{theme}/{_INDEX_TEMPLATE}")
    return template.render(
        entries=entries,
        version=__version__,
        breadcrumbs=_breadcrumbs(rel),
        url_path=url_path,
        rel_path=rel,
        served_root=str(served_root),
        is_root=url_path in ("", "/"),
        theme=theme,
        live_reload=live_reload,
        n_dirs=sum(1 for e in entries if e.is_dir),
        n_files=sum(1 for e in entries if not e.is_dir),
    )
