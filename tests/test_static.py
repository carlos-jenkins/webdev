"""Tests for per-request path resolution and index helpers."""

from __future__ import annotations

from pathlib import Path

from webdev.static import find_index_file, guess_media_type, resolve_fs_path


def test_resolve_existing_file(served_dir: Path) -> None:
    resolved = resolve_fs_path(served_dir, "/hello.txt")
    assert resolved.escapes is False
    assert resolved.is_dir is False
    assert resolved.fs_path == (served_dir / "hello.txt").resolve()


def test_resolve_directory(served_dir: Path) -> None:
    resolved = resolve_fs_path(served_dir, "/sub")
    assert resolved.is_dir is True
    assert resolved.escapes is False


def test_resolve_missing(served_dir: Path) -> None:
    resolved = resolve_fs_path(served_dir, "/nope.txt")
    assert resolved.fs_path is None
    assert resolved.escapes is False


def test_resolve_traversal_blocked(served_dir: Path) -> None:
    resolved = resolve_fs_path(served_dir, "/../../etc/passwd")
    assert resolved.escapes is True
    assert resolved.fs_path is None


def test_resolve_missing_root(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    resolved = resolve_fs_path(missing, "/anything")
    assert resolved.fs_path is None
    assert resolved.escapes is False


def test_find_index_file(served_dir: Path) -> None:
    (served_dir / "index.html").write_text("<h1>index</h1>")
    assert find_index_file(served_dir) == served_dir / "index.html"
    assert find_index_file(served_dir / "sub") is None


def test_guess_media_type_registered_extensions(tmp_path: Path) -> None:
    for name in ("conf.toml", "setup.ini", "app.cfg", "notes.log"):
        f = tmp_path / name
        f.write_text("key = 1")
        assert guess_media_type(f) == "text/plain"


def test_guess_media_type_known_binary(tmp_path: Path) -> None:
    png = tmp_path / "pic.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert guess_media_type(png) == "image/png"


def test_guess_media_type_unknown_text_falls_back_to_plain(tmp_path: Path) -> None:
    f = tmp_path / "weird.xyz123"
    f.write_text("just some text content")
    assert guess_media_type(f) == "text/plain"


def test_guess_media_type_unknown_binary_is_octet_stream(tmp_path: Path) -> None:
    f = tmp_path / "blob.xyz123"
    f.write_bytes(b"\x00\x01\x02\x03binary\x00data")
    assert guess_media_type(f) == "application/octet-stream"
