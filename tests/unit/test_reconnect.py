"""Unit tests for the reconnect backoff policy."""

from __future__ import annotations

from axonctl.config import Backoff
from axonctl.conn.reconnect import ReconnectPolicy


def test_exponential_growth_and_cap() -> None:
    policy = ReconnectPolicy(Backoff(base=1.0, factor=2.0, max=10.0, jitter=0.0))
    assert policy.next_delay(0) == 1.0
    assert policy.next_delay(1) == 2.0
    assert policy.next_delay(2) == 4.0
    assert policy.next_delay(3) == 8.0
    assert policy.next_delay(4) == 10.0  # capped
    assert policy.next_delay(5) == 10.0


def test_jitter_bounds() -> None:
    policy = ReconnectPolicy(Backoff(base=1.0, factor=2.0, max=100.0, jitter=0.5))
    # raw delay for attempt 2 is 4.0; jitter is +/-50%.
    assert policy.next_delay(2, rand=lambda: 1.0) == 6.0  # +50%
    assert policy.next_delay(2, rand=lambda: 0.0) == 2.0  # -50%
    assert policy.next_delay(2, rand=lambda: 0.5) == 4.0  # no change


def test_delay_never_negative() -> None:
    policy = ReconnectPolicy(Backoff(base=1.0, factor=1.0, max=5.0, jitter=1.0))
    assert policy.next_delay(0, rand=lambda: 0.0) >= 0.0
