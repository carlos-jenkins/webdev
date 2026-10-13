"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from webdev.config import Settings


@pytest.fixture
def served_dir(tmp_path: Path) -> Path:
    (tmp_path / "hello.txt").write_text("hello world")
    (tmp_path / "page.html").write_text("<html><body>Hi</body></html>")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.txt").write_text("nested")
    return tmp_path


@pytest.fixture
def settings(served_dir: Path) -> Settings:
    return Settings(
        path=str(served_dir),
        reload=False,
        qr=False,
        gzip=False,
    ).normalized()
