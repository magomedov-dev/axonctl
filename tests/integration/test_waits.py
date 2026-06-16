"""Integration tests for event-driven waits against a scripted fake agent."""

from __future__ import annotations

import asyncio

import pytest
from fake_agent import ScriptedAgent, fake_agent

from axonctl import ConnectionLost, Selector, WaitTimeout, connect_device

_TARGET = Selector.id("com.app:id/target")


async def test_wait_for_resolves_on_event() -> None:
    agent = ScriptedAgent()
    async with (
        fake_agent(agent.handler) as uri,
        await connect_device("d", uri=uri) as device,
    ):
        await agent.ready.wait()
        task = asyncio.create_task(device.wait_for(_TARGET, timeout=2.0))
        await asyncio.sleep(0.05)  # let the wait take its baseline dump and block
        agent.set_target(True)
        await agent.emit_screen_changed()
        node = await task
        assert node is not None
        assert node.resource_id == "com.app:id/target"
        # baseline dump + exactly one re-dump triggered by the event.
        assert agent.dump_count == 2


async def test_wait_for_is_event_driven_not_polling() -> None:
    agent = ScriptedAgent()
    async with (
        fake_agent(agent.handler) as uri,
        await connect_device("d", uri=uri) as device,
    ):
        await agent.ready.wait()
        # Target stays absent and no event is emitted: a poller would keep
        # dumping and (if target appeared) succeed; an event-driven wait dumps
        # once, then blocks until it times out.
        with pytest.raises(WaitTimeout):
            await device.wait_for(_TARGET, timeout=0.3)
        assert agent.dump_count == 1


async def test_wait_tolerates_transient_accessibility_disabled() -> None:
    agent = ScriptedAgent()
    agent.set_dump_error("ACCESSIBILITY_DISABLED")  # no active window yet
    async with (
        fake_agent(agent.handler) as uri,
        await connect_device("d", uri=uri) as device,
    ):
        await agent.ready.wait()
        task = asyncio.create_task(device.wait_for(_TARGET, timeout=2.0))
        await asyncio.sleep(0.05)  # baseline dump fails; the wait must keep going
        agent.set_dump_error(None)
        agent.set_target(True)
        await agent.emit_screen_changed()
        node = await task
        assert node is not None


async def test_wait_gone_resolves_on_event() -> None:
    agent = ScriptedAgent()
    agent.set_target(True)
    async with (
        fake_agent(agent.handler) as uri,
        await connect_device("d", uri=uri) as device,
    ):
        await agent.ready.wait()
        task = asyncio.create_task(device.wait_gone(_TARGET, timeout=2.0))
        await asyncio.sleep(0.05)
        agent.set_target(False)
        await agent.emit_screen_changed()
        await task  # returns None on success


async def test_wait_activity_resolves_on_event() -> None:
    agent = ScriptedAgent()
    agent.set_package("com.other")
    async with (
        fake_agent(agent.handler) as uri,
        await connect_device("d", uri=uri) as device,
    ):
        await agent.ready.wait()
        task = asyncio.create_task(device.wait_activity("com.app", timeout=2.0))
        await asyncio.sleep(0.05)
        agent.set_package("com.app")
        await agent.emit_screen_changed()
        await task


async def test_wait_toast_returns_text() -> None:
    agent = ScriptedAgent()
    async with (
        fake_agent(agent.handler) as uri,
        await connect_device("d", uri=uri) as device,
    ):
        await agent.ready.wait()
        task = asyncio.create_task(device.wait_toast(timeout=2.0))
        await asyncio.sleep(0.05)
        await agent.emit_toast("Wrong password")
        assert await task == "Wrong password"


async def test_wait_toast_catches_toast_fired_before_the_call() -> None:
    agent = ScriptedAgent()
    async with (
        fake_agent(agent.handler) as uri,
        await connect_device("d", uri=uri) as device,
    ):
        await agent.ready.wait()
        await asyncio.sleep(0.05)  # let the stream enable on connect
        # Toast fires BEFORE wait_toast subscribes — the buffer must still catch it.
        await agent.emit_toast("Saved")
        await asyncio.sleep(0.02)
        assert await device.wait_toast(timeout=0.5) == "Saved"


async def test_wait_toast_times_out() -> None:
    agent = ScriptedAgent()
    async with (
        fake_agent(agent.handler) as uri,
        await connect_device("d", uri=uri) as device,
    ):
        await agent.ready.wait()
        with pytest.raises(WaitTimeout):
            await device.wait_toast(timeout=0.2)


async def test_disconnect_wakes_waiter() -> None:
    agent = ScriptedAgent()
    async with (
        fake_agent(agent.handler) as uri,
        await connect_device("d", uri=uri) as device,
    ):
        await agent.ready.wait()
        task = asyncio.create_task(device.wait_for(_TARGET, timeout=5.0))
        await asyncio.sleep(0.05)
        await agent.close_connection()
        with pytest.raises(ConnectionLost):
            await task
