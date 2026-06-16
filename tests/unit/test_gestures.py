"""Unit tests for gesture-params assembly."""

from __future__ import annotations

from axonctl.gestures import GestureBuilder


def test_tap_single_point() -> None:
    params = GestureBuilder.tap(540, 1860, duration=50)
    assert params == {
        "strokes": [{"points": [{"x": 540, "y": 1860}], "duration": 50, "startTime": 0}]
    }


def test_long_tap_uses_longer_duration() -> None:
    params = GestureBuilder.long_tap(10, 20)
    (stroke,) = params["strokes"]
    assert stroke["points"] == [{"x": 10, "y": 20}]
    assert stroke["duration"] == 600


def test_double_tap_has_two_offset_strokes() -> None:
    params = GestureBuilder.double_tap(5, 5, duration=40, gap=100)
    s1, s2 = params["strokes"]
    assert s1["startTime"] == 0
    assert s2["startTime"] == 140  # duration + gap
    assert s1["points"] == s2["points"] == [{"x": 5, "y": 5}]


def test_swipe_two_points() -> None:
    params = GestureBuilder.swipe(0, 100, 0, 900, duration=250)
    (stroke,) = params["strokes"]
    assert stroke["points"] == [{"x": 0, "y": 100}, {"x": 0, "y": 900}]
    assert stroke["duration"] == 250


def test_drag_is_a_single_slow_stroke() -> None:
    params = GestureBuilder.drag(1, 2, 3, 4)
    (stroke,) = params["strokes"]
    assert stroke["points"] == [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
    assert stroke["duration"] == 800


def test_pinch_two_parallel_strokes() -> None:
    params = GestureBuilder.pinch(500, 500, start_radius=300, end_radius=100)
    left, right = params["strokes"]
    assert left["points"] == [{"x": 200, "y": 500}, {"x": 400, "y": 500}]
    assert right["points"] == [{"x": 800, "y": 500}, {"x": 600, "y": 500}]
    assert left["startTime"] == right["startTime"] == 0
