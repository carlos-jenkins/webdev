"""Tests for config-file loading and CLI/config precedence."""

from __future__ import annotations

from pathlib import Path

import pytest

from webdev.cli import resolve_settings
from webdev.config import Settings, load_config_file


def test_defaults() -> None:
    s = Settings()
    assert s.port == 8080
    assert s.no_cache is True
    assert s.reload is True
    assert s.spa is False
    assert s.theme == "dark"


def test_force_port_zeroes_range() -> None:
    s = Settings(force_port=True, range=20).normalized()
    assert s.range == 0


def test_load_flat_config(tmp_path: Path) -> None:
    cfg = tmp_path / "webdev.toml"
    cfg.write_text('port = 9999\nspa = true\ntheme = "dark"\n')
    values = load_config_file(cfg, tmp_path)
    assert values == {"port": 9999, "spa": True, "theme": "dark"}


def test_load_tool_table(tmp_path: Path) -> None:
    cfg = tmp_path / "pyproject.toml"
    cfg.write_text("[tool.webdev]\nport = 7000\ncors = true\n")
    values = load_config_file(cfg, tmp_path)
    assert values == {"port": 7000, "cors": True}


def test_unknown_keys_ignored(tmp_path: Path) -> None:
    cfg = tmp_path / "webdev.toml"
    cfg.write_text('port = 1234\nbogus = "x"\n')
    values = load_config_file(cfg, tmp_path)
    assert values == {"port": 1234}


def test_missing_config_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config_file(tmp_path / "nope.toml", tmp_path)


def test_cli_overrides_config(tmp_path: Path) -> None:
    (tmp_path / "webdev.toml").write_text("port = 9999\n")
    s = resolve_settings(["-p", "8081", str(tmp_path)])
    assert s.port == 8081  # CLI wins over config


def test_config_used_when_no_cli(tmp_path: Path) -> None:
    (tmp_path / "webdev.toml").write_text("port = 9999\n")
    s = resolve_settings([str(tmp_path)])
    assert s.port == 9999  # config wins over default


def test_boolean_optional_flags() -> None:
    s = resolve_settings(["--no-reload", "--spa", "--no-gzip", "/tmp"])
    assert s.reload is False
    assert s.spa is True
    assert s.gzip is False
