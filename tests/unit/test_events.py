"""Unit tests for the event bus and screen-state tracker."""

from __future__ import annotations

from axonctl.events.bus import EventBus, is_closed_event
from axonctl.events.state import ScreenState


async def test_emit_fans_out_to_all_subscribers() -> None:
    bus = EventBus()
    with bus.subscribe() as q1, bus.subscribe() as q2:
        bus.emit({"event": "toast", "text": "hi"})
        assert (await q1.get())["text"] == "hi"
        assert (await q2.get())["text"] == "hi"


async def test_unsubscribe_on_block_exit() -> None:
    bus = EventBus()
    with bus.subscribe():
        pass
    bus.emit({"event": "toast"})  # no live subscribers -> no error


async def test_close_wakes_subscribers() -> None:
    bus = EventBus()
    with bus.subscribe() as queue:
        bus.close()
        assert is_closed_event(await queue.get())


async def test_subscribe_after_close_is_immediately_closed() -> None:
    bus = EventBus()
    bus.close()
    with bus.subscribe() as queue:
        assert is_closed_event(await queue.get())


def test_screen_state_keeps_highest() -> None:
    state = ScreenState()
    state.observe(5, "com.a")
    assert state.screen == 5
    assert state.package == "com.a"
    state.observe(3, "com.b")  # older generation ignored
    assert state.screen == 5
    assert state.package == "com.a"
    state.observe(7, "com.c")
    assert state.screen == 7
    assert state.package == "com.c"
