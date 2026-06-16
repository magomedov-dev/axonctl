"""Unit tests for frame classification."""

from __future__ import annotations

from typing import Any

import orjson

from axonctl.conn.router import FrameRouter


class FakePending:
    """Captures resolve/resolve_binary calls for assertions."""

    def __init__(self) -> None:
        self.resolved: list[tuple[int, dict[str, Any]]] = []
        self.binary: list[tuple[int, bytes]] = []

    def resolve(self, req_id: int, message: dict[str, Any]) -> None:
        self.resolved.append((req_id, message))

    def resolve_binary(self, req_id: int, payload: bytes) -> None:
        self.binary.append((req_id, payload))


def _router() -> tuple[FrameRouter, FakePending, list[dict[str, Any]]]:
    pending = FakePending()
    events: list[dict[str, Any]] = []
    router = FrameRouter(pending, on_event=events.append)  # type: ignore[arg-type]
    return router, pending, events


def test_text_response_goes_to_resolve() -> None:
    router, pending, events = _router()
    msg = {"id": 5, "result": {"ok": 1}}
    router.classify(orjson.dumps(msg).decode())
    assert pending.resolved == [(5, msg)]
    assert not events
    assert not pending.binary


def test_event_goes_to_sink() -> None:
    router, pending, events = _router()
    evt = {"event": "toast", "text": "hi", "package": "com.x"}
    router.classify(orjson.dumps(evt).decode())
    assert events == [evt]
    assert not pending.resolved


def test_binary_frame_goes_to_resolve_binary() -> None:
    router, pending, events = _router()
    frame = (9).to_bytes(4, "big") + b"image-bytes"
    router.classify(frame)
    assert pending.binary == [(9, b"image-bytes")]
    assert not pending.resolved


def test_uncorrelatable_frame_is_dropped() -> None:
    router, pending, events = _router()
    # No id (or id is null) and no event -> nothing happens.
    router.classify(
        orjson.dumps({"error": {"code": "PARSE_ERROR"}, "id": None}).decode()
    )
    assert not pending.resolved
    assert not events


def test_short_binary_frame_is_dropped() -> None:
    router, pending, events = _router()
    router.classify(b"\x00\x01")  # shorter than the 4-byte id header
    assert not pending.binary
