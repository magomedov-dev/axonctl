"""Monotonic request-id generation.

Each device connection owns one :class:`IdGenerator`. Ids cycle through the
protocol's ``[0, 2**32 - 1]`` range (the screenshot binary header encodes the id
as a big-endian ``uint32``) and never collide with an id still awaiting a reply.
"""

from __future__ import annotations

from collections.abc import Callable

#: Largest valid request id — the screenshot binary header is a ``uint32``.
MAX_REQUEST_ID = 2**32 - 1


class IdGenerator:
    """Hands out request ids that are unique among in-flight requests.

    The generator counts upward and wraps at :data:`MAX_REQUEST_ID`, skipping any
    id that is still registered as pending so a wrapped id can never alias a
    request that has not been answered yet.
    """

    def __init__(self, is_pending: Callable[[int], bool], *, start: int = 0) -> None:
        """Initialize the generator.

        Args:
            is_pending: Predicate returning ``True`` while an id is awaiting a
                reply (typically the pending registry's membership test).
            start: First id to consider (mainly for tests).
        """
        self._is_pending = is_pending
        self._counter = start

    def next(self) -> int:
        """Return the next free request id.

        Returns:
            An id in ``[0, MAX_REQUEST_ID]`` not currently pending.

        Raises:
            RuntimeError: If every id in the range is pending (practically
                impossible; guards against an infinite loop).
        """
        for _ in range(MAX_REQUEST_ID + 1):
            current = self._counter
            self._counter = 0 if current >= MAX_REQUEST_ID else current + 1
            if not self._is_pending(current):
                return current
        raise RuntimeError("request id space exhausted")
