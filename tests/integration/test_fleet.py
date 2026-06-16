"""Integration tests for the fleet controller and reconnect."""

from __future__ import annotations

import asyncio

from fake_agent import FakeAdb, FakeWatcher, ScriptedAgent, fake_agent

from axonctl import (
    Backoff,
    ConnectionLost,
    FleetConfig,
    FleetController,
    connect_device,
)
from axonctl.conn.ws import WsClient


def _controller(
    uri: str, adb: FakeAdb, watcher: FakeWatcher, **cfg: object
) -> FleetController:
    config = FleetConfig(**cfg)  # type: ignore[arg-type]
    return FleetController(
        config,
        adb=adb,
        watcher=watcher,
        transport_factory=lambda _serial, _port: WsClient(uri),
    )


async def test_attach_registers_and_connects() -> None:
    adb, watcher = FakeAdb(), FakeWatcher()
    attached: asyncio.Queue[str] = asyncio.Queue()
    async with fake_agent() as uri:
        fleet = _controller(uri, adb, watcher, devices={"d1": frozenset({"us"})})
        fleet.on_attached(lambda d: attached.put_nowait(d.serial))
        async with fleet:
            watcher.attach("d1")
            assert await asyncio.wait_for(attached.get(), 2.0) == "d1"
            device = fleet.get("d1")
            assert device is not None
            assert device.tags == frozenset({"us"})
            assert (await device.ping())["pong"] is True
            # forward was set up to the agent port.
            assert adb.forwards[0][0] == "d1"
            assert adb.forwards[0][2] == 9008


async def test_detach_cleans_up() -> None:
    adb, watcher = FakeAdb(), FakeWatcher()
    attached: asyncio.Queue[str] = asyncio.Queue()
    detached: asyncio.Queue[str] = asyncio.Queue()
    async with fake_agent() as uri:
        fleet = _controller(uri, adb, watcher)
        fleet.on_attached(lambda d: attached.put_nowait(d.serial))
        fleet.on_detached(lambda s: detached.put_nowait(s))
        async with fleet:
            watcher.attach("d1")
            await asyncio.wait_for(attached.get(), 2.0)
            port = adb.forwards[0][1]
            watcher.detach("d1")
            assert await asyncio.wait_for(detached.get(), 2.0) == "d1"
            assert fleet.get("d1") is None
            assert adb.removed == [("d1", port)]


async def test_group_membership() -> None:
    adb, watcher = FakeAdb(), FakeWatcher()
    attached: asyncio.Queue[str] = asyncio.Queue()
    async with fake_agent() as uri:
        fleet = _controller(
            uri,
            adb,
            watcher,
            devices={"d1": frozenset({"us"}), "d2": frozenset({"eu"})},
        )
        fleet.on_attached(lambda d: attached.put_nowait(d.serial))
        async with fleet:
            watcher.attach("d1")
            watcher.attach("d2")
            await asyncio.wait_for(attached.get(), 2.0)
            await asyncio.wait_for(attached.get(), 2.0)
            assert [d.serial for d in fleet.group("us").devices()] == ["d1"]
            assert {d.serial for d in fleet.devices()} == {"d1", "d2"}


async def test_reconnect_after_drop() -> None:
    agent = ScriptedAgent()
    cfg = FleetConfig(backoff=Backoff(base=0.05, factor=1.5, max=0.2, jitter=0.0))
    async with (
        fake_agent(agent.handler) as uri,
        await connect_device("d", uri=uri, config=cfg) as device,
    ):
        await agent.ready.wait()
        assert (await device.ping())["pong"] is True

        await agent.close_connection()  # server drops the socket

        # The supervisor reconnects with backoff; ping works again once it does.
        reconnected = False
        for _ in range(60):
            await asyncio.sleep(0.05)
            try:
                await device.ping()
                reconnected = True
                break
            except ConnectionLost:
                continue
        assert reconnected, "device did not reconnect after the drop"
