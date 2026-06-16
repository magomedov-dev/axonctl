"""WebSocket transport.

A thin wrapper over the ``websockets`` asyncio client that knows nothing about
RPC or events — it just opens a socket, sends text, receives text-or-binary
frames, and closes. :class:`WebSocketTransport` is the seam the connection layer
depends on, so tests can substitute an in-process fake.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..rpc.errors import ConnectionLost


@runtime_checkable
class WebSocketTransport(Protocol):
    """Minimal transport contract the connection layer depends on.

    Implemented by :class:`WsClient` in production and by fakes in tests. ``open``
    may be called again after ``close`` to support reconnect.
    """

    async def open(self) -> None:
        """Open (or reopen) the underlying connection."""
        ...

    async def send_text(self, data: str) -> None:
        """Send a text frame."""
        ...

    async def recv(self) -> str | bytes:
        """Receive the next frame: ``str`` for text, ``bytes`` for binary."""
        ...

    async def close(self) -> None:
        """Close the underlying connection."""
        ...


class WsClient:
    """A :class:`WebSocketTransport` backed by the ``websockets`` library."""

    def __init__(self, uri: str, *, open_timeout: float = 10.0) -> None:
        """Initialize the client (does not connect yet).

        Args:
            uri: WebSocket URI, e.g. ``ws://127.0.0.1:10001``.
            open_timeout: Seconds to wait for the connection to open.
        """
        self._uri = uri
        self._open_timeout = open_timeout
        self._conn: ClientConnection | None = None

    async def open(self) -> None:
        """Open a fresh connection to the configured URI.

        ``max_size`` is disabled because UI dumps can be large.

        Raises:
            ConnectionLost: If the connection cannot be established.
        """
        try:
            self._conn = await connect(
                self._uri,
                open_timeout=self._open_timeout,
                max_size=None,
            )
        except (WebSocketException, OSError) as exc:
            raise ConnectionLost(f"failed to open {self._uri}: {exc}") from exc

    async def send_text(self, data: str) -> None:
        """Send a text frame.

        Args:
            data: The text payload.

        Raises:
            ConnectionLost: If the socket is not open or has closed.
        """
        conn = self._require_conn()
        try:
            await conn.send(data)
        except (ConnectionClosed, OSError) as exc:
            raise ConnectionLost(f"send failed: {exc}") from exc

    async def recv(self) -> str | bytes:
        """Receive the next frame.

        Returns:
            ``str`` for a text frame, ``bytes`` for a binary frame.

        Raises:
            ConnectionLost: If the socket is not open or has closed.
        """
        conn = self._require_conn()
        try:
            return await conn.recv()
        except (ConnectionClosed, OSError) as exc:
            raise ConnectionLost(f"recv failed: {exc}") from exc

    async def close(self) -> None:
        """Close the connection if open (idempotent)."""
        conn, self._conn = self._conn, None
        if conn is not None:
            await conn.close()

    def _require_conn(self) -> ClientConnection:
        if self._conn is None:
            raise ConnectionLost("transport is not open")
        return self._conn
