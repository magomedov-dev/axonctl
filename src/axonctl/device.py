"""The :class:`Device` facade.

The object user scenarios talk to. Stage 1 exposes the minimal vertical slice —
``ping`` and ``dump`` — over a :class:`~axonctl.conn.connection.DeviceConnection`;
gestures, actions, waits and the rest are layered on in later stages. A scenario
never reaches into the connection or RPC layers directly.

:func:`connect_device` is a provisional convenience constructor for testing and
the first vertical slice; the public entry point becomes
:class:`~axonctl.FleetController` once the fleet layer lands.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from .config import FleetConfig
from .conn.connection import ConnectionState, DeviceConnection
from .conn.ws import WebSocketTransport, WsClient
from .tree.tree import UiTree


class Device:
    """A single Android device under control.

    Attributes are read via properties; everything a scenario needs is a method
    on this object.
    """

    def __init__(
        self,
        *,
        serial: str,
        tags: Iterable[str],
        connection: DeviceConnection,
    ) -> None:
        """Wrap an established connection.

        Args:
            serial: Device serial.
            tags: Static group tags for this device.
            connection: The live device connection.
        """
        self._serial = serial
        self._tags = frozenset(tags)
        self._conn = connection

    @property
    def serial(self) -> str:
        """The device serial."""
        return self._serial

    @property
    def tags(self) -> frozenset[str]:
        """The device's static group tags."""
        return self._tags

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._conn.state

    async def ping(self) -> Mapping[str, Any]:
        """Check application-level liveness.

        Returns:
            The agent's ``{"pong": True, "ts": <epoch millis>}`` result.

        Raises:
            RpcTimeout: If the agent does not reply within the deadline.
            ConnectionLost: If the connection drops during the call.
        """
        return await self._conn.rpc.call("ping")

    async def dump(
        self,
        *,
        compress: bool = True,
        max_depth: int | None = None,
        window_id: int | None = None,
    ) -> UiTree:
        """Dump the UI hierarchy and parse it into a :class:`UiTree`.

        Args:
            compress: Drop recomputable ``center`` and empty ``children`` to save
                bandwidth (recommended on dense screens).
            max_depth: Maximum tree depth (root is 0); ``None`` for unbounded.
            window_id: Dump a specific window (from ``getWindows``); ``None`` uses
                the active window.

        Returns:
            The parsed UI tree.

        Raises:
            AccessibilityDisabled: If there is no active-window root.
            WindowNotFound: If ``window_id`` has no matching window.
            RpcTimeout: If the agent does not reply within the deadline.
            ConnectionLost: If the connection drops during the call.
        """
        params: dict[str, Any] = {"compress": compress}
        if max_depth is not None:
            params["maxDepth"] = max_depth
        if window_id is not None:
            params["windowId"] = window_id
        result = await self._conn.rpc.call("dumpHierarchy", params)
        return UiTree.from_dict(result)

    async def aclose(self) -> None:
        """Close the underlying connection and release its resources."""
        await self._conn.close()

    async def __aenter__(self) -> Device:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()


async def connect_device(
    serial: str,
    *,
    uri: str | None = None,
    transport: WebSocketTransport | None = None,
    tags: Iterable[str] = (),
    config: FleetConfig | None = None,
    event_sink: Callable[[Mapping[str, Any]], None] | None = None,
) -> Device:
    """Open a connection and return a ready :class:`Device`.

    Provisional helper for the first vertical slice and tests. Provide either a
    ``uri`` (a real ``WsClient`` is created) or a ``transport`` (e.g. a fake).

    Args:
        serial: Device serial.
        uri: WebSocket URI to connect to, if no ``transport`` is given.
        transport: A pre-built transport (takes precedence over ``uri``).
        tags: Static group tags for the device.
        config: Fleet config; defaults are used when omitted.
        event_sink: Optional callback for server-push events.

    Returns:
        A connected :class:`Device`.

    Raises:
        ValueError: If neither ``uri`` nor ``transport`` is provided.
        ConnectionLost: If the socket cannot be opened.
    """
    config = config or FleetConfig()
    if transport is None:
        if uri is None:
            raise ValueError("connect_device requires either uri or transport")
        transport = WsClient(uri, open_timeout=config.timeouts.connect)
    connection = DeviceConnection(
        transport,
        serial=serial,
        config=config,
        event_sink=event_sink,
    )
    await connection.connect()
    return Device(serial=serial, tags=tags, connection=connection)
