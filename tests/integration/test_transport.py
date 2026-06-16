"""Integration tests: the full path against an in-process fake agent.

Exercises transport -> router -> pending -> RpcClient -> Device end to end,
including the happy path, protocol errors, per-call timeouts, and a dropped
connection.
"""

from __future__ import annotations

import pytest
from fake_agent import (
    FAKE_PACKAGE,
    accessibility_disabled_handler,
    closing_handler,
    fake_agent,
    silent_handler,
)

from axonctl import (
    AccessibilityDisabled,
    ConnectionLost,
    FleetConfig,
    RpcTimeout,
    Timeouts,
    connect_device,
)


async def test_ping_round_trip() -> None:
    async with fake_agent() as uri, await connect_device("fake", uri=uri) as device:
        result = await device.ping()
        assert result["pong"] is True
        assert "ts" in result


async def test_dump_parses_into_tree() -> None:
    async with fake_agent() as uri, await connect_device("fake", uri=uri) as device:
        tree = await device.dump()
        assert tree.package == FAKE_PACKAGE
        assert tree.screen == 1
        assert tree.root.node_id == 0
        assert len(tree.root.children) == 1
        assert tree.root.children[0].resource_id == "com.app:id/login"


async def test_dump_protocol_error_is_typed() -> None:
    handler = accessibility_disabled_handler()
    async with (
        fake_agent(handler) as uri,
        await connect_device("fake", uri=uri) as device,
    ):
        with pytest.raises(AccessibilityDisabled):
            await device.dump()


async def test_call_times_out() -> None:
    cfg = FleetConfig(timeouts=Timeouts(rpc=0.2, ping_interval=999, ping_timeout=0.2))
    async with (
        fake_agent(silent_handler) as uri,
        await connect_device("fake", uri=uri, config=cfg) as device,
    ):
        with pytest.raises(RpcTimeout):
            await device.ping()


async def test_dropped_connection_wakes_caller() -> None:
    async with (
        fake_agent(closing_handler) as uri,
        await connect_device("fake", uri=uri) as device,
    ):
        with pytest.raises(ConnectionLost):
            await device.ping()
