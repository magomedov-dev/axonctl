"""Per-device connection.

Owns one device's transport and the machinery above it: the shared pending
registry, the id generator, the frame router, the event bus, the screen-state
tracker, and an :class:`RpcClient`. Runs two background tasks for the connection's
lifetime — a read loop (feeds inbound frames to the router) and a ping loop
(application-level heartbeat) — and cancels them cleanly on :meth:`close`.

Reconnect handling is scaffolded here but only activated in a later stage; for
now a dropped link transitions to ``CLOSED`` and wakes any in-flight callers and
waiters.
"""

from __future__ import annotations

import asyncio
import enum
import logging
from collections.abc import Mapping
from typing import Any

from ..config import FleetConfig
from ..events.bus import EventBus
from ..events.state import ScreenState
from ..rpc.client import RpcClient
from ..rpc.errors import AxonError, ConnectionLost, RpcError
from ..rpc.ids import IdGenerator
from ..rpc.pending import PendingRegistry
from .router import FrameRouter
from .ws import WebSocketTransport


class ConnectionState(enum.Enum):
    """Lifecycle state of a :class:`DeviceConnection`."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSED = "closed"


class DeviceConnection:
    """Manages the socket and RPC plumbing for a single device."""

    def __init__(
        self,
        transport: WebSocketTransport,
        *,
        serial: str,
        config: FleetConfig | None = None,
    ) -> None:
        """Initialize the connection (does not open the socket).

        Args:
            transport: The WebSocket transport (or a fake) to drive.
            serial: Device serial, used for logging and identity.
            config: Fleet config; defaults are used when omitted.
        """
        self._transport = transport
        self._serial = serial
        self._config = config or FleetConfig()
        self._pending = PendingRegistry()
        self._ids = IdGenerator(self._pending.__contains__)
        self._events = EventBus()
        self._screen = ScreenState()
        self._router = FrameRouter(self._pending, on_event=self._handle_event)
        self.rpc = RpcClient(
            send=self._send,
            pending=self._pending,
            ids=self._ids,
            timeout=self._config.timeouts.rpc,
        )
        self._state = ConnectionState.CONNECTING
        self._read_task: asyncio.Task[None] | None = None
        self._ping_task: asyncio.Task[None] | None = None
        self._closing = False
        self._stream_enabled = False
        self._log = logging.getLogger("axonctl.conn")

    @property
    def serial(self) -> str:
        """The device serial."""
        return self._serial

    @property
    def config(self) -> FleetConfig:
        """The fleet configuration in effect for this connection."""
        return self._config

    @property
    def state(self) -> ConnectionState:
        """Current lifecycle state."""
        return self._state

    @property
    def events(self) -> EventBus:
        """The per-device event bus."""
        return self._events

    @property
    def screen(self) -> ScreenState:
        """The latest observed screen state."""
        return self._screen

    async def connect(self) -> None:
        """Open the socket and start the read and ping loops.

        Raises:
            ConnectionLost: If the socket cannot be opened.
        """
        self._state = ConnectionState.CONNECTING
        self._stream_enabled = False
        await self._transport.open()
        self._state = ConnectionState.CONNECTED
        self._read_task = asyncio.create_task(
            self._read_loop(), name=f"axon-read-{self._serial}"
        )
        self._ping_task = asyncio.create_task(
            self._ping_loop(), name=f"axon-ping-{self._serial}"
        )

    async def ensure_event_stream(self) -> None:
        """Enable the server-push event stream once (idempotent).

        Raises:
            RpcError: If the agent rejects the request.
            RpcTimeout: If the agent does not reply within the deadline.
            ConnectionLost: If the connection drops during the call.
        """
        if self._stream_enabled:
            return
        await self.rpc.call("setEventStream", {"enabled": True})
        self._stream_enabled = True

    async def close(self) -> None:
        """Cancel background tasks, fail pending calls/waiters, close the socket.

        Idempotent and safe to call from outside the loop tasks.
        """
        self._closing = True
        self._state = ConnectionState.CLOSED
        for task in (self._read_task, self._ping_task):
            if task is not None:
                task.cancel()
        for task in (self._read_task, self._ping_task):
            if task is not None:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception:  # noqa: BLE001 - log and continue shutdown
                    self._log.exception(
                        "[%s] background task error on close", self._serial
                    )
        self._read_task = None
        self._ping_task = None
        self._pending.cancel_all(ConnectionLost("connection closed"))
        self._events.close()
        await self._transport.close()

    def _handle_event(self, event: Mapping[str, Any]) -> None:
        if event.get("event") == "screenChanged":
            self._screen.observe(int(event.get("screen", -1)), event.get("package"))
        self._events.emit(event)

    async def _send(self, text: str) -> None:
        await self._transport.send_text(text)

    async def _read_loop(self) -> None:
        try:
            while True:
                message = await self._transport.recv()
                try:
                    self._router.classify(message)
                except Exception:  # noqa: BLE001 - one bad frame must not kill the loop
                    self._log.exception(
                        "[%s] error routing inbound frame", self._serial
                    )
        except asyncio.CancelledError:
            raise
        except ConnectionLost as exc:
            self._on_disconnect(exc)
        except Exception as exc:  # noqa: BLE001 - unexpected read failure
            self._log.exception("[%s] read loop crashed", self._serial)
            self._on_disconnect(ConnectionLost(str(exc)))

    async def _ping_loop(self) -> None:
        interval = self._config.timeouts.ping_interval
        ping_timeout = self._config.timeouts.ping_timeout
        try:
            while True:
                await asyncio.sleep(interval)
                try:
                    await self.rpc.call("ping", timeout=ping_timeout)
                except asyncio.CancelledError:
                    raise
                except AxonError as exc:
                    self._log.warning("[%s] heartbeat failed: %s", self._serial, exc)
                    self._on_disconnect(exc)
                    return
        except asyncio.CancelledError:
            raise

    def _on_disconnect(self, exc: BaseException) -> None:
        """Mark the link dead and wake any in-flight callers and waiters.

        Idempotent. Reconnect is wired in a later stage; for now we just fail
        fast so callers do not hang until their per-call timeout.
        """
        if self._closing or self._state is ConnectionState.CLOSED:
            return
        self._state = ConnectionState.CLOSED
        reason = (
            exc
            if isinstance(exc, (ConnectionLost, RpcError))
            else ConnectionLost(str(exc))
        )
        self._pending.cancel_all(reason)
        self._events.close()
