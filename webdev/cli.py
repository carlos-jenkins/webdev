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
Command-line interface.

Preserves the legacy flags (``-i``, ``-p``, ``-f``, ``-r``, ``-u``, ``-v``,
positional ``path``) and adds a flag for every new feature. Every flag has a
matching config-file key; precedence is CLI > config file > built-in default.
"""

from __future__ import annotations

import logging
from argparse import ArgumentParser, BooleanOptionalAction, Namespace
from os import getcwd
from os.path import isdir

from . import __version__
from .config import Settings, load_config_file
from .index import ThemeNotFoundError, available_themes

log = logging.getLogger("webdev")

_FORMAT = "%(asctime)s:::%(levelname)s:::%(message)s"
_V_LEVELS = {
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
}

#: Sentinel marking "flag not provided on the CLI" so config can win.
_UNSET = object()


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="webdev", description="Small, fast development web server."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=_UNSET,
        help="Increase verbosity level (repeatable).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Development Web Server v{__version__}",
    )

    # Core / back-compatible options.
    parser.add_argument(
        "-i",
        "--ip",
        default=_UNSET,
        help="IP to bind to. Default: 0.0.0.0",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=_UNSET,
        help="Base port to listen on. Default: 8080.",
    )
    parser.add_argument(
        "-f",
        "--force-port",
        action="store_true",
        default=_UNSET,
        help="Force the use of the given port (disables range probing).",
    )
    parser.add_argument(
        "-r",
        "--range",
        type=int,
        default=_UNSET,
        help="Number of ports to try from the base port. Default: 20.",
    )
    parser.add_argument(
        "-u",
        "--future",
        action="store_true",
        default=_UNSET,
        help="Serve a folder that does not exist yet.",
    )

    # New feature toggles (flag + --no- variant).
    parser.add_argument(
        "--reload",
        action=BooleanOptionalAction,
        default=_UNSET,
        help="Live-reload browsers on file changes. Default: enabled.",
    )
    parser.add_argument(
        "--cache",
        dest="no_cache",
        action="store_false",
        default=_UNSET,
        help="Allow caching (disable no-cache headers).",
    )
    parser.add_argument(
        "--no-cache",
        dest="no_cache",
        action="store_true",
        default=_UNSET,
        help="Send no-cache headers so content is always fresh. Default.",
    )
    parser.add_argument(
        "--spa",
        action=BooleanOptionalAction,
        default=_UNSET,
        help="SPA fallback: serve index.html for unknown routes. Default: off.",
    )
    parser.add_argument(
        "--gzip",
        action=BooleanOptionalAction,
        default=_UNSET,
        help="Gzip-compress responses. Default: enabled.",
    )
    parser.add_argument(
        "--cors",
        action=BooleanOptionalAction,
        default=_UNSET,
        help="Send permissive CORS headers. Default: off.",
    )
    parser.add_argument(
        "--qr",
        action=BooleanOptionalAction,
        default=_UNSET,
        help="Print a QR code / LAN URL at startup. Default: enabled.",
    )
    parser.add_argument(
        "--https",
        action=BooleanOptionalAction,
        default=_UNSET,
        help="Serve over HTTPS (self-signed if no cert/key). Default: off.",
    )
    parser.add_argument(
        "--cert",
        default=_UNSET,
        help="TLS certificate file (with --https).",
    )
    parser.add_argument(
        "--key",
        default=_UNSET,
        help="TLS private key file (with --https).",
    )
    parser.add_argument(
        "--theme",
        default=_UNSET,
        help="Directory index theme. Default: dark.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a config file (TOML). Auto-discovered if omitted.",
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=_UNSET,
        help="Path to serve. Default: current directory.",
    )
    return parser


def _provided(args: Namespace) -> dict:
    """Extract only the options explicitly provided on the command line."""
    out = {}
    for key, value in vars(args).items():
        if key in ("config",):
            continue
        if value is not _UNSET:
            out[key] = value
    return out


def resolve_settings(argv: list[str] | None = None) -> Settings:
    """Parse *argv*, merge with config file, and return resolved settings."""
    parser = build_parser()
    args = parser.parse_args(argv)

    cli_values = _provided(args)

    # Where to look for an auto-discovered config file.
    search_from = cli_values.get("path", getcwd())
    config_values = load_config_file(args.config, search_from)

    # Precedence: defaults < config file < CLI.
    merged = {**config_values, **cli_values}
    settings = Settings(**merged).normalized()

    # Configure logging as early as possible.
    level = _V_LEVELS.get(settings.verbose, logging.DEBUG)
    logging.basicConfig(format=_FORMAT, level=level)
    log.debug("Resolved settings: %s", settings)

    return settings


def main(argv: list[str] | None = None) -> int:
    from .run import serve

    settings = resolve_settings(argv)

    if not settings.future and not isdir(settings.path):
        log.error("Not a directory: %s", settings.path)
        return 1

    try:
        from .index import validate_theme

        validate_theme(settings.theme)
    except ThemeNotFoundError as error:
        log.error(str(error))
        log.error("Available themes: %s", ", ".join(available_themes()))
        return 1

    return serve(settings)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
