"""Unit tests for the request-id generator."""

from __future__ import annotations

from axonctl.rpc.ids import MAX_REQUEST_ID, IdGenerator


def test_sequential_ids() -> None:
    gen = IdGenerator(lambda _i: False)
    assert [gen.next() for _ in range(4)] == [0, 1, 2, 3]


def test_wraps_at_max() -> None:
    gen = IdGenerator(lambda _i: False, start=MAX_REQUEST_ID)
    assert gen.next() == MAX_REQUEST_ID
    assert gen.next() == 0
    assert gen.next() == 1


def test_skips_pending_ids() -> None:
    pending = {1, 2}
    gen = IdGenerator(lambda i: i in pending)
    assert gen.next() == 0
    # 1 and 2 are pending, so the next free id is 3.
    assert gen.next() == 3
