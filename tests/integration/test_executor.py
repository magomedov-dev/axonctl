"""Integration tests for the fleet executor (run / targets / concurrency)."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

from fake_agent import FakeAdb, FakeWatcher, fake_agent

from axonctl import Device, FleetConfig, FleetController
from axonctl.conn.ws import WsClient


@contextlib.asynccontextmanager
async def fleet_of(
    uri: str, serials: list[str], **cfg: object
) -> AsyncIterator[tuple[FleetController, FakeWatcher]]:
    """Start a controller with ``serials`` attached against the fake agent."""
    adb, watcher = FakeAdb(), FakeWatcher()
    fleet = FleetController(
        FleetConfig(**cfg),  # type: ignore[arg-type]
        adb=adb,
        watcher=watcher,
        transport_factory=lambda _s, _p: WsClient(uri),
    )
    attached: asyncio.Queue[str] = asyncio.Queue()
    fleet.on_attached(lambda d: attached.put_nowait(d.serial))
    async with fleet:
        for serial in serials:
            watcher.attach(serial)
        for _ in serials:
            await asyncio.wait_for(attached.get(), 2.0)
        yield fleet, watcher


async def test_run_collects_per_device_results() -> None:
    async with fake_agent() as uri, fleet_of(uri, ["d1", "d2", "d3"]) as (fleet, _w):

        async def scenario(device: Device) -> str:
            await device.ping()
            return f"hi-{device.serial}"

        results = await fleet.run(scenario)
        assert results.all_ok
        assert results.succeeded() == {"d1": "hi-d1", "d2": "hi-d2", "d3": "hi-d3"}
        assert set(results) == {"d1", "d2", "d3"}


async def test_failure_is_isolated() -> None:
    async with fake_agent() as uri, fleet_of(uri, ["d1", "d2"]) as (fleet, _w):

        async def scenario(device: Device) -> str:
            if device.serial == "d2":
                raise ValueError("boom")
            return device.serial

        results = await fleet.run(scenario)
        assert results["d1"].ok
        assert results["d1"].value == "d1"
        assert not results["d2"].ok
        assert isinstance(results["d2"].error, ValueError)
        assert set(results.failed()) == {"d2"}


async def test_targets_select_a_group() -> None:
    devices = {
        "d1": frozenset({"us"}),
        "d2": frozenset({"eu"}),
        "d3": frozenset({"us"}),
    }
    async with (
        fake_agent() as uri,
        fleet_of(uri, ["d1", "d2", "d3"], devices=devices) as (fleet, _w),
    ):

        async def scenario(device: Device) -> str:
            return device.serial

        results = await fleet.run(scenario, targets="us")
        assert set(results) == {"d1", "d3"}


async def test_per_run_concurrency_is_capped() -> None:
    active = 0
    peak = 0

    async def scenario(device: Device) -> None:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.03)
        active -= 1

    serials = [f"d{i}" for i in range(5)]
    # Global cap high so the per-run cap is what binds.
    async with (
        fake_agent() as uri,
        fleet_of(uri, serials, concurrency=10) as (fleet, _w),
    ):
        await fleet.run(scenario, concurrency=2)
    assert peak <= 2


async def test_global_semaphore_shared_across_runs() -> None:
    active = 0
    peak = 0

    async def scenario(device: Device) -> None:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.03)
        active -= 1

    devices = {
        "a1": frozenset({"a"}),
        "a2": frozenset({"a"}),
        "b1": frozenset({"b"}),
        "b2": frozenset({"b"}),
    }
    # Global cap of 2 must bound the sum of two concurrent runs of 10 each.
    async with (
        fake_agent() as uri,
        fleet_of(uri, list(devices), devices=devices, concurrency=2) as (fleet, _w),
    ):
        await asyncio.gather(
            fleet.run(scenario, targets="a", concurrency=10),
            fleet.run(scenario, targets="b", concurrency=10),
        )
    assert peak <= 2


async def test_detached_device_becomes_failed_outcome() -> None:
    gate = asyncio.Event()
    detached: asyncio.Queue[str] = asyncio.Queue()

    async with fake_agent() as uri, fleet_of(uri, ["d1", "d2"]) as (fleet, watcher):
        fleet.on_detached(lambda s: detached.put_nowait(s))

        async def scenario(device: Device) -> str:
            if device.serial == "d2":
                await gate.wait()  # hold until d2 is detached
            return (await device.ping()) and device.serial

        run_task = asyncio.create_task(fleet.run(scenario))
        watcher.detach("d2")
        assert await asyncio.wait_for(detached.get(), 2.0) == "d2"
        gate.set()
        results = await run_task

    assert results["d1"].ok
    assert not results["d2"].ok  # its ping failed on the closed connection
