"""Unit tests for the pending-request registry."""

from __future__ import annotations

import asyncio

import pytest

from axonctl.rpc.errors import ConnectionLost
from axonctl.rpc.pending import PendingRegistry


async def test_resolve_success() -> None:
    reg = PendingRegistry()
    fut = reg.register(1)
    reg.resolve(1, {"id": 1, "result": {"pong": True}})
    response = await fut
    assert response.result == {"pong": True}
    assert response.error is None
    assert 1 not in reg


async def test_resolve_error() -> None:
    reg = PendingRegistry()
    fut = reg.register(2)
    reg.resolve(2, {"id": 2, "error": {"code": "STALE", "message": "x"}})
    response = await fut
    assert response.error == {"code": "STALE", "message": "x"}
    assert response.result is None


async def test_two_part_binary_resolves_only_after_payload() -> None:
    reg = PendingRegistry()
    fut = reg.register(7, expects_binary=True)
    reg.resolve(7, {"id": 7, "result": {"width": 2, "height": 2}})
    assert not fut.done()  # metadata alone must not resolve it
    reg.resolve_binary(7, b"PNG")
    response = await fut
    assert response.result == {"width": 2, "height": 2}
    assert response.binary == b"PNG"


async def test_two_part_error_resolves_without_binary() -> None:
    reg = PendingRegistry()
    fut = reg.register(8, expects_binary=True)
    reg.resolve(8, {"id": 8, "error": {"code": "INTERNAL", "message": "rate"}})
    response = await fut
    assert response.error == {"code": "INTERNAL", "message": "rate"}


async def test_unknown_id_is_ignored() -> None:
    reg = PendingRegistry()
    reg.resolve(999, {"id": 999, "result": {}})  # must not raise
    reg.resolve_binary(999, b"x")


async def test_duplicate_register_raises() -> None:
    reg = PendingRegistry()
    reg.register(1)
    with pytest.raises(ValueError, match="already pending"):
        reg.register(1)


async def test_cancel_all_fails_pending_futures() -> None:
    reg = PendingRegistry()
    fut = reg.register(1)
    reg.cancel_all(ConnectionLost("bye"))
    with pytest.raises(ConnectionLost):
        await fut
    assert 1 not in reg


async def test_pop_removes_without_resolving() -> None:
    reg = PendingRegistry()
    fut = reg.register(1)
    reg.pop(1)
    assert 1 not in reg
    assert not fut.done()
    fut.cancel()
    with pytest.raises(asyncio.CancelledError):
        await fut
