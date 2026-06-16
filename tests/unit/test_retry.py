"""Unit tests for the STALE retry policy and decorator."""

from __future__ import annotations

import pytest

from axonctl import RetryPolicy, retry_on_stale
from axonctl.config import Retry
from axonctl.rpc.errors import NodeNotFound, Stale


async def test_succeeds_after_stale_retries() -> None:
    calls = {"n": 0}

    async def action() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise Stale("stale")
        return "ok"

    policy = RetryPolicy(Retry(attempts=3, delay=0.0))
    assert await policy.run(action) == "ok"
    assert calls["n"] == 3


async def test_raises_after_exhausting_attempts() -> None:
    calls = {"n": 0}

    async def action() -> str:
        calls["n"] += 1
        raise Stale("always")

    policy = RetryPolicy(Retry(attempts=2, delay=0.0))
    with pytest.raises(Stale):
        await policy.run(action)
    assert calls["n"] == 2


async def test_non_stale_errors_are_not_retried() -> None:
    calls = {"n": 0}

    async def action() -> str:
        calls["n"] += 1
        raise NodeNotFound("missing")

    policy = RetryPolicy(Retry(attempts=3, delay=0.0))
    with pytest.raises(NodeNotFound):
        await policy.run(action)
    assert calls["n"] == 1


async def test_decorator_retries_on_stale() -> None:
    calls = {"n": 0}

    @retry_on_stale(attempts=3, delay=0.0)
    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            raise Stale("once")
        return "done"

    assert await flaky() == "done"
    assert calls["n"] == 2
