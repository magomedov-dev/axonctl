"""Unit tests for the port allocator."""

from __future__ import annotations

import pytest

from axonctl.fleet.ports import PortAllocator


def test_acquire_is_stable_per_serial() -> None:
    alloc = PortAllocator((10000, 10010))
    p1 = alloc.acquire("a")
    assert alloc.acquire("a") == p1  # same serial -> same port
    p2 = alloc.acquire("b")
    assert p2 != p1
    assert alloc.port_for("b") == p2


def test_release_frees_the_port() -> None:
    alloc = PortAllocator((10000, 10000))  # single port
    p = alloc.acquire("a")
    assert alloc.release("a") == p
    assert alloc.port_for("a") is None
    # freed, so "b" can take it now
    assert alloc.acquire("b") == p


def test_exhaustion_raises() -> None:
    alloc = PortAllocator((10000, 10000))
    alloc.acquire("a")
    with pytest.raises(RuntimeError, match="no free port"):
        alloc.acquire("b")
