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
Configuration model and config-file loading for WebDev.

A single :class:`Settings` dataclass holds every runtime option. Each option is
exposed both as a CLI flag (see :mod:`webdev.cli`) and as a config-file key.

Resolution precedence (highest wins):

    CLI flag  >  config file  >  built-in default
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, fields
from os import getcwd
from os.path import abspath
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on Python 3.10
    import tomli as tomllib


#: Candidate config file names auto-discovered when ``--config`` is not given.
CONFIG_FILENAMES = ("webdev.toml", ".webdev.toml")

#: Default directory index theme (and currently the only one shipped).
DEFAULT_THEME = "dark"


@dataclass
class Settings:
    """Fully resolved runtime settings."""

    # Core / back-compatible options.
    path: str = field(default_factory=getcwd)
    ip: str = "0.0.0.0"
    port: int = 8080
    force_port: bool = False
    range: int = 20
    future: bool = False
    verbose: int = 0

    # New feature toggles (defaults per the plan).
    no_cache: bool = True
    reload: bool = True
    spa: bool = False
    gzip: bool = True
    cors: bool = False
    qr: bool = True
    https: bool = False
    cert: str | None = None
    key: str | None = None
    theme: str = DEFAULT_THEME

    def normalized(self) -> Settings:
        """Return a copy with derived/validated invariants applied."""
        self.path = abspath(self.path)
        # Preserve the historical quirk: forcing a port disables range probing.
        if self.force_port:
            self.range = 0
        return self


#: Config keys that are not part of :class:`Settings` construction directly.
_BOOL_KEYS = {
    "force_port",
    "future",
    "no_cache",
    "reload",
    "spa",
    "gzip",
    "cors",
    "qr",
    "https",
}
_INT_KEYS = {"port", "range", "verbose"}
_STR_KEYS = {"path", "ip", "cert", "key", "theme"}


def _settings_field_names() -> set[str]:
    return {f.name for f in fields(Settings)}


def discover_config_file(start: str | Path) -> Path | None:
    """Find a config file by walking up from *start* to the filesystem root."""
    current = Path(start).resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        for name in CONFIG_FILENAMES:
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None


def load_config_file(
    config_path: str | Path | None, search_from: str | Path
) -> dict[str, Any]:
    """
    Load config values from a TOML file.

    If *config_path* is given it is used directly; otherwise a file is
    auto-discovered starting at *search_from*. Returns an empty mapping when no
    config is found. Supports both a top-level table and a ``[tool.webdev]``
    table (e.g. inside ``pyproject.toml``).
    """
    path: Path | None
    if config_path is not None:
        path = Path(config_path)
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {path}")
    else:
        path = discover_config_file(search_from)

    if path is None:
        return {}

    with path.open("rb") as fd:
        data = tomllib.load(fd)

    # Allow [tool.webdev] (pyproject-style) or a flat table.
    if "tool" in data and isinstance(data["tool"], dict):
        data = data["tool"].get("webdev", {}) or {}
    elif "webdev" in data and isinstance(data["webdev"], dict):
        data = data["webdev"]

    return _coerce_config(data)


def _coerce_config(data: dict[str, Any]) -> dict[str, Any]:
    """Keep only known keys and coerce them to their expected types."""
    valid = _settings_field_names()
    result: dict[str, Any] = {}
    for key, value in data.items():
        norm = key.replace("-", "_")
        if norm not in valid:
            continue
        if norm in _BOOL_KEYS:
            result[norm] = bool(value)
        elif norm in _INT_KEYS:
            result[norm] = int(value)
        elif norm in _STR_KEYS:
            result[norm] = str(value)
        else:
            result[norm] = value
    return result
