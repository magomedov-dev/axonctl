"""Device attach/detach watcher.

Wraps ``adbutils.track_devices()`` — a blocking generator — and turns it into an
async stream of :class:`DeviceEvent`, without polling. The blocking iterator runs
in a daemon thread that feeds an asyncio queue.

:class:`Watcher` is the seam the controller depends on, so tests can supply a
scripted fake.
"""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

import adbutils

from .adb import resolve_adb_path


@dataclass(frozen=True, slots=True)
class DeviceEvent:
    """A device presence change.

    Attributes:
        serial: The device serial.
        present: ``True`` on attach, ``False`` on detach.
    """

    serial: str
    present: bool


class Watcher(Protocol):
    """Source of device attach/detach events."""

    def events(self) -> AsyncIterator[DeviceEvent]:
        """Yield device presence changes until the stream ends."""
        ...


class AdbWatcher:
    """A :class:`Watcher` backed by ``adbutils.track_devices()``."""

    def __init__(self, adb_path: str | None = None) -> None:
        """Initialize the watcher.

        Args:
            adb_path: Explicit adb binary path; resolved if omitted.
        """
        resolved = resolve_adb_path(adb_path)
        if resolved:
            os.environ.setdefault("ADBUTILS_ADB_PATH", resolved)
        self._client = adbutils.AdbClient()

    async def events(self) -> AsyncIterator[DeviceEvent]:
        """Yield attach/detach events from the adb server.

        Runs the blocking ``track_devices`` iterator in a daemon thread and
        bridges it to the event loop. The stream ends if the adb server
        connection drops.

        Yields:
            :class:`DeviceEvent` for each presence change.
        """
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[DeviceEvent | None] = asyncio.Queue()

        def worker() -> None:
            try:
                for event in self._client.track_devices():
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        DeviceEvent(serial=event.serial, present=event.present),
                    )
            except Exception:  # noqa: BLE001 - surface end-of-stream to the consumer
                pass
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        thread = threading.Thread(target=worker, name="axon-adb-track", daemon=True)
        thread.start()
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event
