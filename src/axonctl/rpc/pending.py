"""Pending-request registry.

Correlates outgoing requests with their replies. A normal call resolves on a
single text response. A screenshot call (variant A) resolves only once **both**
the JSON metadata *and* the following binary frame have arrived — the protocol
guarantees they are emitted back-to-back, so the registry simply holds the
metadata until the binary lands.

One registry per device connection; nothing here is shared across devices.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Response:
    """A correlated reply to one request.

    Attributes:
        id: The request id this reply corresponds to.
        result: The ``result`` object on success (``None`` on error).
        error: The ``error`` object on failure (``None`` on success).
        binary: The trailing binary payload for two-part replies, else ``None``.
    """

    id: int
    result: Mapping[str, Any] | None = None
    error: Mapping[str, Any] | None = None
    binary: bytes | None = None


@dataclass(slots=True)
class _Pending:
    future: asyncio.Future[Response]
    expects_binary: bool
    meta: Mapping[str, Any] | None = field(default=None)


class PendingRegistry:
    """Maps in-flight request ids to the future awaiting their reply."""

    def __init__(self) -> None:
        self._entries: dict[int, _Pending] = {}

    def __contains__(self, req_id: int) -> bool:
        """Return ``True`` while ``req_id`` is awaiting a reply."""
        return req_id in self._entries

    def register(
        self, req_id: int, *, expects_binary: bool = False
    ) -> asyncio.Future[Response]:
        """Register ``req_id`` and return the future that will hold its reply.

        Args:
            req_id: The request id being sent.
            expects_binary: ``True`` for two-part (screenshot) replies, which
                resolve only after the trailing binary frame.

        Returns:
            A future resolving to the :class:`Response`.

        Raises:
            ValueError: If ``req_id`` is already registered.
        """
        if req_id in self._entries:
            raise ValueError(f"request id {req_id} already pending")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Response] = loop.create_future()
        self._entries[req_id] = _Pending(future=future, expects_binary=expects_binary)
        return future

    def resolve(self, req_id: int, message: Mapping[str, Any]) -> None:
        """Deliver a text response for ``req_id``.

        An error response resolves immediately. For a two-part call, a success
        response only stashes the metadata; the future resolves on the binary
        frame. Unknown/late ids are ignored.

        Args:
            req_id: The id echoed in the response.
            message: The parsed response object (with ``result`` or ``error``).
        """
        entry = self._entries.get(req_id)
        if entry is None:
            return
        error = message.get("error")
        if error is not None:
            self._finish(req_id, Response(id=req_id, error=error))
            return
        result = message.get("result")
        if entry.expects_binary:
            entry.meta = result
            return
        self._finish(req_id, Response(id=req_id, result=result))

    def resolve_binary(self, req_id: int, payload: bytes) -> None:
        """Deliver the trailing binary frame for a two-part reply.

        Resolves the future by pairing ``payload`` with the metadata stashed by
        the preceding :meth:`resolve`. Unknown ids are ignored.

        Args:
            req_id: The id encoded in the binary frame header.
            payload: The binary payload (header already stripped).
        """
        entry = self._entries.get(req_id)
        if entry is None:
            return
        self._finish(req_id, Response(id=req_id, result=entry.meta, binary=payload))

    def pop(self, req_id: int) -> None:
        """Drop ``req_id`` without resolving (used by callers on timeout/cleanup).

        Args:
            req_id: The id to forget.
        """
        self._entries.pop(req_id, None)

    def cancel_all(self, exc: BaseException) -> None:
        """Fail every pending future with ``exc`` and clear the registry.

        Called when the connection drops so awaiting callers wake immediately
        instead of blocking until their per-call timeout.

        Args:
            exc: The exception to raise in each awaiting caller.
        """
        for entry in list(self._entries.values()):
            if not entry.future.done():
                entry.future.set_exception(exc)
        self._entries.clear()

    def _finish(self, req_id: int, response: Response) -> None:
        entry = self._entries.pop(req_id, None)
        if entry is not None and not entry.future.done():
            entry.future.set_result(response)
