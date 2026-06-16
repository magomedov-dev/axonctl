"""Retry handling for stale node actions.

``STALE`` means the agent found a node but it changed before the action landed —
a transient condition. The device never retries; the controller does. Since each
``nodeAction`` re-finds from a fresh root, retrying simply re-issues the call.

:class:`RetryPolicy` is used internally by :class:`~axonctl.Device`'s node
actions; :func:`retry_on_stale` is a decorator scenarios can put on their own
coroutine helpers.
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from .config import Retry
from .rpc.errors import Stale

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class RetryPolicy:
    """Re-runs an action while it raises :class:`~axonctl.Stale`."""

    def __init__(self, retry: Retry | None = None) -> None:
        """Initialize the policy.

        Args:
            retry: Retry parameters; defaults to :class:`~axonctl.config.Retry`.
        """
        self._retry = retry or Retry()

    async def run(self, action: Callable[[], Awaitable[T]]) -> T:
        """Run ``action``, retrying on ``STALE`` up to the configured attempts.

        Args:
            action: A zero-arg coroutine factory (called afresh per attempt).

        Returns:
            The action's result.

        Raises:
            Stale: If every attempt raises ``STALE``.
        """
        last: Stale | None = None
        for attempt in range(self._retry.attempts):
            try:
                return await action()
            except Stale as exc:
                last = exc
                if attempt + 1 < self._retry.attempts:
                    await asyncio.sleep(self._retry.delay)
        assert last is not None  # attempts >= 1, so the loop ran at least once
        raise last


def retry_on_stale(*, attempts: int = 3, delay: float = 0.1) -> Callable[[F], F]:
    """Decorate a coroutine to retry it on :class:`~axonctl.Stale`.

    Args:
        attempts: Total attempts including the first.
        delay: Delay in seconds between attempts.

    Returns:
        A decorator wrapping the coroutine with the retry policy.

    Example:
        ```python
        from axonctl import retry_on_stale

        @retry_on_stale(attempts=5)
        async def tap_continue(device):
            await device.click(Selector.text("Continue"))
        ```
    """
    policy = RetryPolicy(Retry(attempts=attempts, delay=delay))

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await policy.run(lambda: func(*args, **kwargs))

        return cast(F, wrapper)

    return decorator
