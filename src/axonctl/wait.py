"""Event-driven waits.

The heart of the architecture: waits are driven by the ``screenChanged`` event
stream, never by polling. The pattern is — subscribe to the bus, enable the
stream, take a baseline dump and check the predicate, then re-dump and re-check
only when an event signals a *newer* screen, all under a single deadline. While
one device waits on the socket, the event loop serves every other device.

``WaitEngine`` is transport-agnostic: it is handed the event bus, an
``ensure_stream`` coroutine, and a ``dump`` coroutine; :class:`~axonctl.Device`
wires those in and exposes the friendly ``wait_*`` methods.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar

from .events.bus import EventBus, is_closed_event
from .rpc.errors import AccessibilityDisabled, ConnectionLost, WaitTimeout

if TYPE_CHECKING:
    from .tree.tree import UiTree

T = TypeVar("T")

_SCREEN_CHANGED = "screenChanged"
_TOAST = "toast"


class WaitEngine:
    """Runs event-driven waits for one device."""

    def __init__(
        self,
        *,
        events: EventBus,
        ensure_stream: Callable[[], Awaitable[None]],
        dump: Callable[..., Awaitable[UiTree]],
    ) -> None:
        """Initialize the engine.

        Args:
            events: The device's event bus.
            ensure_stream: Coroutine that enables the server-push stream (idempotent).
            dump: Coroutine returning a fresh :class:`UiTree`.
        """
        self._events = events
        self._ensure_stream = ensure_stream
        self._dump = dump

    async def wait_until(
        self,
        predicate: Callable[[UiTree], T | None],
        *,
        timeout: float,
        what: str,
    ) -> T:
        """Wait until ``predicate`` returns a non-``None`` value, then return it.

        Subscribes before dumping so no change is missed, baselines on an initial
        dump, then re-dumps only on a ``screenChanged`` carrying a newer screen.

        Args:
            predicate: Called with each fresh tree; return the result to stop, or
                ``None`` to keep waiting.
            timeout: Deadline in seconds.
            what: Short description used in the timeout message.

        Returns:
            The first non-``None`` value the predicate produced.

        Raises:
            WaitTimeout: If the deadline passes first.
            ConnectionLost: If the connection drops while waiting.
        """
        try:
            async with asyncio.timeout(timeout):
                with self._events.subscribe() as queue:
                    await self._ensure_stream()
                    last_screen = -1
                    tree = await self._safe_dump()
                    if tree is not None:
                        result = predicate(tree)
                        if result is not None:
                            return result
                        last_screen = tree.screen
                    while True:
                        event = await queue.get()
                        if is_closed_event(event):
                            raise ConnectionLost("connection closed during wait")
                        if event.get("event") != _SCREEN_CHANGED:
                            continue
                        if int(event.get("screen", -1)) <= last_screen:
                            continue
                        tree = await self._safe_dump()
                        if tree is None:
                            continue
                        last_screen = tree.screen
                        result = predicate(tree)
                        if result is not None:
                            return result
        except TimeoutError as exc:
            raise WaitTimeout(f"{what} not satisfied within {timeout}s") from exc

    async def _safe_dump(self) -> UiTree | None:
        """Dump, treating a transient no-active-window state as 'keep waiting'.

        Returns:
            The tree, or ``None`` if the screen had no active-window root (e.g.
            mid-transition during an app launch).
        """
        try:
            return await self._dump()
        except AccessibilityDisabled:
            return None

    async def wait_toast(self, *, timeout: float) -> str:
        """Wait for the next ``toast`` event and return its text.

        Args:
            timeout: Deadline in seconds.

        Returns:
            The toast text.

        Raises:
            WaitTimeout: If no toast arrives within the deadline.
            ConnectionLost: If the connection drops while waiting.
        """
        try:
            async with asyncio.timeout(timeout):
                with self._events.subscribe() as queue:
                    await self._ensure_stream()
                    while True:
                        event = await queue.get()
                        if is_closed_event(event):
                            raise ConnectionLost("connection closed during wait")
                        if event.get("event") == _TOAST:
                            return str(event.get("text", ""))
        except TimeoutError as exc:
            raise WaitTimeout(f"no toast within {timeout}s") from exc
