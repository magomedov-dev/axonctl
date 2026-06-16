"""Frame classification.

Splits the single inbound message stream into its three kinds and dispatches
each to the right place — nothing more:

- **binary frame** -> first 4 bytes (big-endian) are the request id; the rest is
  the payload -> :meth:`PendingRegistry.resolve_binary`.
- **text + ``id``** -> a response -> :meth:`PendingRegistry.resolve`.
- **text + ``event``** -> a server-push event -> the event sink.

Malformed or uncorrelatable frames (e.g. an error response with ``id: null``)
are dropped with a log line.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

import orjson

from ..rpc.pending import PendingRegistry

_log = logging.getLogger("axonctl.router")

#: Width of the binary-frame id header, in bytes (big-endian uint32).
_BINARY_ID_HEADER = 4


class FrameRouter:
    """Routes inbound frames to the pending registry or the event sink."""

    def __init__(
        self,
        pending: PendingRegistry,
        on_event: Callable[[Mapping[str, Any]], None],
    ) -> None:
        """Initialize the router.

        Args:
            pending: Registry resolving correlated responses.
            on_event: Sink invoked for each server-push event.
        """
        self._pending = pending
        self._on_event = on_event

    def classify(self, message: str | bytes) -> None:
        """Classify and dispatch a single inbound frame.

        Args:
            message: A text frame (``str``) or binary frame (``bytes``) as
                returned by the transport's ``recv``.
        """
        if isinstance(message, (bytes, bytearray)):
            self._dispatch_binary(bytes(message))
            return
        self._dispatch_text(message)

    def _dispatch_binary(self, frame: bytes) -> None:
        if len(frame) < _BINARY_ID_HEADER:
            _log.warning(
                "dropping binary frame shorter than id header (%d bytes)", len(frame)
            )
            return
        req_id = int.from_bytes(frame[:_BINARY_ID_HEADER], "big")
        self._pending.resolve_binary(req_id, frame[_BINARY_ID_HEADER:])

    def _dispatch_text(self, text: str) -> None:
        try:
            data: Any = orjson.loads(text)
        except orjson.JSONDecodeError:
            _log.warning("dropping non-JSON text frame")
            return
        if not isinstance(data, dict):
            _log.warning("dropping text frame that is not a JSON object")
            return
        req_id = data.get("id")
        if req_id is not None:
            self._pending.resolve(req_id, data)
        elif "event" in data:
            self._on_event(data)
        else:
            _log.warning("dropping frame with neither correlatable id nor event")
