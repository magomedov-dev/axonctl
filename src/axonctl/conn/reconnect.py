"""Reconnect backoff policy.

Pure computation of the delay before the next reconnect attempt: exponential
growth, capped, with bounded jitter to avoid a thundering herd when many devices
drop at once. The actual reconnect loop lives in the connection (wired up in a
later stage); this module just answers "how long to wait".
"""

from __future__ import annotations

import random
from collections.abc import Callable

from ..config import Backoff


class ReconnectPolicy:
    """Computes backoff delays from a :class:`~axonctl.config.Backoff`."""

    def __init__(self, backoff: Backoff) -> None:
        """Initialize the policy.

        Args:
            backoff: The backoff parameters (base, factor, max, jitter).
        """
        self._backoff = backoff

    def next_delay(
        self, attempt: int, *, rand: Callable[[], float] = random.random
    ) -> float:
        """Return the delay in seconds before reconnect ``attempt``.

        Args:
            attempt: Zero-based attempt counter (0 = first retry).
            rand: Source of randomness returning ``[0, 1)``; injectable for tests.

        Returns:
            ``min(base * factor**attempt, max)`` perturbed by ``±jitter`` and
            clamped to be non-negative.
        """
        raw = self._backoff.base * (self._backoff.factor**attempt)
        capped = min(raw, self._backoff.max)
        # Map rand() in [0, 1) to a factor in [1 - jitter, 1 + jitter).
        spread = self._backoff.jitter * (2.0 * rand() - 1.0)
        return max(0.0, capped * (1.0 + spread))
