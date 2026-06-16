"""Regression tests for the feedback fixes: readiness, target semantics, ergonomics."""

from __future__ import annotations

import asyncio

from fake_agent import FakeAdb, FakeWatcher, fake_agent

from axonctl import (
    Device,
    DeviceNotConnected,
    FleetConfig,
    FleetController,
    connect_device,
)
from axonctl.conn.ws import WsClient


def _controller(
    uri: str, adb: FakeAdb, watcher: FakeWatcher, **cfg: object
) -> FleetController:
    return FleetController(
        FleetConfig(**cfg),  # type: ignore[arg-type]
        adb=adb,
        watcher=watcher,
        transport_factory=lambda _s, _p: WsClient(uri),
        ready_timeout=2.0,
    )


async def _serial(device: Device) -> str:
    return device.serial


async def test_start_waits_until_present_device_ready() -> None:
    # adb reports d1 present; the attach is delivered only after a delay.
    adb, watcher = FakeAdb(), FakeWatcher()
    adb.present = ["d1"]
    async with fake_agent() as uri:
        fleet = _controller(uri, adb, watcher, devices={"d1": frozenset({"g"})})

        async def delayed_attach() -> None:
            await asyncio.sleep(0.1)
            watcher.attach("d1")

        asyncio.create_task(delayed_attach())
        async with fleet:
            # start() blocked on readiness, so d1 is connected with no manual wait.
            assert fleet.get("d1") is not None
            results = await fleet.run(_serial)
            assert set(results) == {"d1"}


async def test_configured_but_disconnected_target_is_failed_not_skipped() -> None:
    devices = {"d1": frozenset({"g"}), "d2": frozenset({"g"})}
    adb, watcher = FakeAdb(), FakeWatcher()
    adb.present = ["d1"]  # only d1 is physically present
    async with fake_agent() as uri:
        fleet = _controller(uri, adb, watcher, devices=devices)
        watcher.attach("d1")
        async with fleet:
            results = await fleet.run(_serial, targets="g")
            # both configured members appear; d2 is a failed outcome, not missing.
            assert set(results) == {"d1", "d2"}
            assert results["d1"].ok and results["d1"].value == "d1"
            assert not results["d2"].ok
            assert isinstance(results["d2"].error, DeviceNotConnected)


async def test_run_on_empty_targets_returns_empty_without_raising() -> None:
    adb, watcher = FakeAdb(), FakeWatcher()
    async with fake_agent() as uri:
        fleet = _controller(uri, adb, watcher)
        async with fleet:
            results = await fleet.run(_serial, targets="nobody")
            assert len(results) == 0  # warns in the log, but does not raise


async def test_connect_device_async_with_form() -> None:
    async with (
        fake_agent() as uri,
        connect_device("d", uri=uri) as device,  # no `await` needed
    ):
        assert (await device.ping())["pong"] is True


async def test_connect_device_await_form_still_works() -> None:
    async with fake_agent() as uri:
        device = await connect_device("d", uri=uri)
        try:
            assert (await device.ping())["pong"] is True
        finally:
            await device.aclose()
