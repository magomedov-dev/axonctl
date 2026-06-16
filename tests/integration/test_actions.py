"""Integration tests for gestures, node actions, screenshot, and retry."""

from __future__ import annotations

import pytest
from fake_agent import fake_agent, stale_then_ok_handler

from axonctl import (
    FleetConfig,
    Selector,
    Stale,
    UnsupportedSelector,
    connect_device,
)
from axonctl.config import Retry

_LOGIN = Selector.id("com.app:id/login")


async def test_screenshot_returns_binary_payload() -> None:
    async with fake_agent() as uri, await connect_device("d", uri=uri) as device:
        data = await device.screenshot(format="png")
        # The fake agent's variant-A reply: JSON meta then the binary frame.
        assert data == b"\x89PNG\r\n\x1a\n-fake-image"


async def test_gestures_and_global_action() -> None:
    async with fake_agent() as uri, await connect_device("d", uri=uri) as device:
        await device.tap(100, 200)
        await device.swipe(0, 1000, 0, 200)
        await device.pinch(500, 500, start_radius=300, end_radius=100)
        assert await device.global_action("home") is True


async def test_node_actions_succeed() -> None:
    async with fake_agent() as uri, await connect_device("d", uri=uri) as device:
        await device.click(_LOGIN)
        await device.set_text(Selector.id("com.app:id/user"), "alice")
        await device.scroll(Selector.cls("android.widget.ScrollView"), "forward")


async def test_action_rejects_within_selector() -> None:
    async with fake_agent() as uri, await connect_device("d", uri=uri) as device:
        scoped = Selector.text("OK").within(Selector.id("com.app:id/dialog"))
        with pytest.raises(UnsupportedSelector, match="within"):
            await device.click(scoped)


async def test_stale_is_retried_then_succeeds() -> None:
    cfg = FleetConfig(retry=Retry(attempts=3, delay=0.0))
    async with (
        fake_agent(stale_then_ok_handler(2)) as uri,
        await connect_device("d", uri=uri, config=cfg) as device,
    ):
        # First two nodeActions return STALE, the third succeeds.
        await device.click(_LOGIN)


async def test_stale_raises_when_attempts_exhausted() -> None:
    cfg = FleetConfig(retry=Retry(attempts=2, delay=0.0))
    async with (
        fake_agent(stale_then_ok_handler(5)) as uri,
        await connect_device("d", uri=uri, config=cfg) as device,
    ):
        with pytest.raises(Stale):
            await device.click(_LOGIN)
