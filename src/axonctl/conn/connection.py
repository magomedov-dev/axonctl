"""Per-device connection.

Owns one device's transport and the machinery above it: the shared pending
registry, the id generator, the frame router, the event bus, the screen-state
tracker, and an :class:`RpcClient`.

A single supervisor task drives the connection lifecycle: run the read and ping
loops, and on a socket drop (e.g. the agent service restarted) reconnect with
backoff while the connection is *not* closed. The supervisor only reopens the
socket to the same URI — it never touches adb (the fleet controller owns forwards
and decides, via device presence, when to stop reconnecting by calling
:meth:`close`). A transient drop fails in-flight calls and waiters but keeps the
event bus usable; an explicit close tears everything down for good.
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
from ..rpc.errors import ConnectionLost, RpcError, RpcTimeout
from ..rpc.ids import IdGenerator
from ..rpc.pending import PendingRegistry
from .reconnect import ReconnectPolicy
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
        reconnect: bool = True,
    ) -> None:
        """Initialize the connection (does not open the socket).

        Args:
            transport: The WebSocket transport (or a fake) to drive.
            serial: Device serial, used for logging and identity.
            config: Fleet config; defaults are used when omitted.
            reconnect: Whether to auto-reconnect on a dropped socket.
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
        self._policy = ReconnectPolicy(self._config.backoff)
        self._reconnect_enabled = reconnect
        self._state = ConnectionState.CONNECTING
        self._supervisor: asyncio.Task[None] | None = None
        self._read_task: asyncio.Task[None] | None = None
        self._ping_task: asyncio.Task[None] | None = None
        self._closing = False
        self._stream_enabled = False
        self._attempt = 0
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
        """Open the socket and start the supervisor (read + ping + reconnect).

        The initial open is awaited so a failure surfaces to the caller; later
        drops are handled by the supervisor.

        Raises:
            ConnectionLost: If the initial open fails.
        """
        self._state = ConnectionState.CONNECTING
        self._stream_enabled = False
        await self._transport.open()
        self._supervisor = asyncio.create_task(
            self._supervise(), name=f"axon-supervise-{self._serial}"
        )

    async def ensure_event_stream(self) -> None:
        """Enable the server-push event stream once (idempotent).

        Reset on every (re)connect, so it is re-enabled lazily after a reconnect.

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
        """Stop the supervisor, fail pending calls/waiters, close the socket.

        Idempotent and safe to call from outside the loop tasks. Stops any
        in-progress reconnect.
        """
        self._closing = True
        self._state = ConnectionState.CLOSED
        if self._supervisor is not None:
            self._supervisor.cancel()
            try:
                await self._supervisor
            except asyncio.CancelledError:
                pass
            except Exception:  # noqa: BLE001 - log and continue shutdown
                self._log.exception("[%s] supervisor error on close", self._serial)
        self._supervisor = None
        self._pending.cancel_all(ConnectionLost("connection closed"))
        self._events.close()
        await self._transport.close()

    def _handle_event(self, event: Mapping[str, Any]) -> None:
        if event.get("event") == "screenChanged":
            self._screen.observe(int(event.get("screen", -1)), event.get("package"))
        self._events.emit(event)

    async def _send(self, text: str) -> None:
        await self._transport.send_text(text)

    async def _supervise(self) -> None:
        first = True
        while not self._closing:
            try:
                if not first:
                    self._state = ConnectionState.RECONNECTING
                    delay = self._policy.next_delay(self._attempt)
                    self._attempt += 1
                    await asyncio.sleep(delay)
                    if self._closing:
                        break
                    await self._transport.open()
                first = False
                self._state = ConnectionState.CONNECTED
                self._stream_enabled = False
                self._attempt = 0
                await self._run_io()
            except asyncio.CancelledError:
                raise
            except ConnectionLost as exc:
                self._on_drop(exc)
                if not self._reconnect_enabled:
                    break
            except Exception as exc:  # noqa: BLE001 - unexpected supervisor failure
                self._log.exception("[%s] supervisor iteration failed", self._serial)
                self._on_drop(ConnectionLost(str(exc)))
                if not self._reconnect_enabled:
                    break
        if not self._closing:
            # Reconnect disabled and the link dropped: settle as closed.
            self._state = ConnectionState.CLOSED
            self._pending.cancel_all(ConnectionLost("connection closed"))
            self._events.close()

    def _on_drop(self, exc: BaseException) -> None:
        reason = (
            exc
            if isinstance(exc, (ConnectionLost, RpcError))
            else ConnectionLost(str(exc))
        )
        self._pending.cancel_all(reason)
        self._events.interrupt()
        if self._reconnect_enabled and not self._closing:
            self._log.warning(
                "[%s] connection dropped, reconnecting: %s", self._serial, exc
            )

    async def _run_io(self) -> None:
        """Run the read and ping loops until one ends; raise the cause.

        Raises:
            ConnectionLost: When the socket drops.
        """
        read = asyncio.create_task(self._read_loop(), name=f"axon-read-{self._serial}")
        ping = asyncio.create_task(self._ping_loop(), name=f"axon-ping-{self._serial}")
        self._read_task, self._ping_task = read, ping
        try:
            done, pending = await asyncio.wait(
                {read, ping}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                exc = task.exception()
                if exc is not None:
                    raise exc
            raise ConnectionLost("io loop ended unexpectedly")
        except asyncio.CancelledError:
            for task in (read, ping):
                task.cancel()
            await asyncio.gather(read, ping, return_exceptions=True)
            raise

    async def _read_loop(self) -> None:
        while True:
            message = await self._transport.recv()  # raises ConnectionLost on drop
            try:
                self._router.classify(message)
            except Exception:  # noqa: BLE001 - one bad frame must not kill the loop
                self._log.exception("[%s] error routing inbound frame", self._serial)

    async def _ping_loop(self) -> None:
        interval = self._config.timeouts.ping_interval
        ping_timeout = self._config.timeouts.ping_timeout
        while True:
            await asyncio.sleep(interval)
            try:
                await self.rpc.call("ping", timeout=ping_timeout)
            except (RpcTimeout, ConnectionLost) as exc:
                raise ConnectionLost(f"heartbeat failed: {exc}") from exc
            except RpcError as exc:  # unexpected, but the link is alive
                self._log.warning("[%s] ping returned an error: %s", self._serial, exc)
