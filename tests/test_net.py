"""Tests for networking helpers."""

from __future__ import annotations

import socket

import pytest

from webdev.net import NoFreePortError, build_urls, find_free_port


def test_find_free_port_returns_base_when_free() -> None:
    # Find an ephemeral free port to use as a base.
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        base = s.getsockname()[1]
    port = find_free_port("127.0.0.1", base, 5)
    assert port == base


def test_find_free_port_increments_when_busy() -> None:
    occupied = socket.socket()
    occupied.bind(("127.0.0.1", 0))
    occupied.listen()
    base = occupied.getsockname()[1]
    try:
        port = find_free_port("127.0.0.1", base, 5)
        assert port != base
        assert base < port <= base + 5
    finally:
        occupied.close()


def test_find_free_port_exhausted() -> None:
    occupied = socket.socket()
    occupied.bind(("127.0.0.1", 0))
    occupied.listen()
    base = occupied.getsockname()[1]
    try:
        with pytest.raises(NoFreePortError):
            find_free_port("127.0.0.1", base, 0)
    finally:
        occupied.close()


def test_build_urls_loopback() -> None:
    urls = build_urls("127.0.0.1", 8080, https=False)
    assert urls == ["http://127.0.0.1:8080"]


def test_build_urls_all_interfaces_includes_loopback() -> None:
    urls = build_urls("0.0.0.0", 9000, https=True)
    assert "https://127.0.0.1:9000" in urls
