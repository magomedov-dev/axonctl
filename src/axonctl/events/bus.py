"""Per-device event bus.

Fans server-push events (``screenChanged``, ``toast``) out to any number of
short-lived subscribers, each backed by its own queue. Waits subscribe for the
duration of a single wait and unsubscribe when done. When the connection drops,
:meth:`close` injects a sentinel so blocked subscribers wake instead of hanging
until their timeout.

Nothing here is shared across devices.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Iterator, Mapping
from typing import Any

#: ``event`` value of the sentinel emitted when the connection closes.
CLOSED_EVENT = "__closed__"
_CLOSED: Mapping[str, Any] = {"event": CLOSED_EVENT}

#: A delivered item: a server-push event or the close sentinel.
Event = Mapping[str, Any]


class EventBus:
    """Distributes events to active subscribers (one queue each)."""

    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[Event]] = set()
        self._closed = False

    def emit(self, event: Event) -> None:
        """Deliver ``event`` to every current subscriber.

        Args:
            event: The parsed event object.
        """
        for queue in self._queues:
            queue.put_nowait(event)

    def close(self) -> None:
        """Wake all subscribers with the close sentinel (idempotent)."""
        if self._closed:
            return
        self._closed = True
        self.emit(_CLOSED)

    @contextlib.contextmanager
    def subscribe(self) -> Iterator[asyncio.Queue[Event]]:
        """Subscribe for the duration of the ``with`` block.

        Yields:
            A queue receiving every event emitted while subscribed (plus the
            close sentinel if the bus is already closed).
        """
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._queues.add(queue)
        if self._closed:
            queue.put_nowait(_CLOSED)
        try:
            yield queue
        finally:
            self._queues.discard(queue)


def is_closed_event(event: Event) -> bool:
    """Return whether ``event`` is the close sentinel."""
    return event.get("event") == CLOSED_EVENT
