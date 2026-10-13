"""Tests for the index renderer and theming."""

from __future__ import annotations

from pathlib import Path

import pytest

from webdev.index import (
    ThemeNotFoundError,
    available_themes,
    human_size,
    render_index,
    validate_theme,
)


def test_available_themes_includes_dark() -> None:
    assert "dark" in available_themes()


def test_validate_theme_ok() -> None:
    validate_theme("dark")  # does not raise


def test_validate_theme_unknown() -> None:
    with pytest.raises(ThemeNotFoundError):
        validate_theme("neon-unicorn")


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "0 B"),
        (512, "512 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1048576, "1.0 MB"),
    ],
)
def test_human_size(value: int, expected: str) -> None:
    assert human_size(value) == expected


def test_render_index_contains_entries(served_dir: Path) -> None:
    html = render_index(
        fs_dir=served_dir,
        url_path="/",
        served_root=served_dir,
        theme="dark",
        live_reload=False,
    )
    assert "hello.txt" in html
    assert "sub/" in html
    assert "Index of" in html


def test_render_index_escapes_names(tmp_path: Path) -> None:
    (tmp_path / "<script>.txt").write_text("x")
    html = render_index(
        fs_dir=tmp_path,
        url_path="/",
        served_root=tmp_path,
        theme="dark",
        live_reload=False,
    )
    assert "<script>.txt" not in html
    assert "&lt;script&gt;" in html
