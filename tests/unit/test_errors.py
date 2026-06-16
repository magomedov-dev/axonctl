"""Unit tests for the error-code mapping."""

from __future__ import annotations

import pytest

from axonctl.rpc.errors import (
    AccessibilityDisabled,
    AmbiguousMatch,
    GestureFailed,
    NodeNotFound,
    NotEditable,
    RpcError,
    Stale,
    error_from_code,
)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("NODE_NOT_FOUND", NodeNotFound),
        ("AMBIGUOUS_MATCH", AmbiguousMatch),
        ("STALE", Stale),
        ("NOT_EDITABLE", NotEditable),
        ("ACCESSIBILITY_DISABLED", AccessibilityDisabled),
        ("GESTURE_FAILED", GestureFailed),
    ],
)
def test_known_codes_map_to_subclass(code: str, expected: type[RpcError]) -> None:
    err = error_from_code(code, "boom")
    assert isinstance(err, expected)
    assert err.code == code
    assert "boom" in str(err)


def test_unknown_code_falls_back_to_rpcerror() -> None:
    err = error_from_code("WAT", "huh")
    assert type(err) is RpcError
    assert err.code == "WAT"
    assert err.message == "huh"


def test_subclasses_are_rpcerror_and_axonerror() -> None:
    err = error_from_code("STALE", "x")
    assert isinstance(err, RpcError)
