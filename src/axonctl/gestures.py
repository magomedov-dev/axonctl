"""Gesture assembly.

Pure construction of ``gesture`` params from intent. The agent exposes a single
coordinate primitive — strokes of timed points — and tap, long-press, double-tap,
swipe, drag and pinch are all just variations in point count, duration, and the
number of parallel strokes. No I/O here; :class:`~axonctl.Device` sends the result.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

#: A gesture params object: ``{"strokes": [...]}`` ready for the ``gesture`` RPC.
GestureParams = dict[str, Any]


def _stroke(
    points: Sequence[tuple[int, int]], *, duration: int, start_time: int = 0
) -> dict[str, Any]:
    return {
        "points": [{"x": int(x), "y": int(y)} for x, y in points],
        "duration": int(duration),
        "startTime": int(start_time),
    }


class GestureBuilder:
    """Builds ``gesture`` params for the common gesture shapes.

    Every method returns a :data:`GestureParams` object; durations are in
    milliseconds.
    """

    @staticmethod
    def tap(x: int, y: int, *, duration: int = 50) -> GestureParams:
        """A single tap at ``(x, y)``."""
        return {"strokes": [_stroke([(x, y)], duration=duration)]}

    @staticmethod
    def long_tap(x: int, y: int, *, duration: int = 600) -> GestureParams:
        """A long-press at ``(x, y)``."""
        return {"strokes": [_stroke([(x, y)], duration=duration)]}

    @staticmethod
    def double_tap(
        x: int, y: int, *, duration: int = 50, gap: int = 120
    ) -> GestureParams:
        """Two taps at ``(x, y)`` separated by ``gap`` milliseconds."""
        return {
            "strokes": [
                _stroke([(x, y)], duration=duration, start_time=0),
                _stroke([(x, y)], duration=duration, start_time=duration + gap),
            ]
        }

    @staticmethod
    def swipe(
        x1: int, y1: int, x2: int, y2: int, *, duration: int = 300
    ) -> GestureParams:
        """A swipe (flick) from ``(x1, y1)`` to ``(x2, y2)``."""
        return {"strokes": [_stroke([(x1, y1), (x2, y2)], duration=duration)]}

    @staticmethod
    def drag(
        x1: int, y1: int, x2: int, y2: int, *, duration: int = 800
    ) -> GestureParams:
        """A slow drag from ``(x1, y1)`` to ``(x2, y2)`` (longer than a swipe)."""
        return {"strokes": [_stroke([(x1, y1), (x2, y2)], duration=duration)]}

    @staticmethod
    def pinch(
        cx: int,
        cy: int,
        *,
        start_radius: int,
        end_radius: int,
        duration: int = 300,
    ) -> GestureParams:
        """A two-finger horizontal pinch around ``(cx, cy)``.

        ``start_radius > end_radius`` pinches in (zoom out); the reverse pinches
        out (zoom in).

        Args:
            cx: Center x.
            cy: Center y.
            start_radius: Initial half-distance between the two fingers.
            end_radius: Final half-distance between the two fingers.
            duration: Stroke duration in milliseconds.

        Returns:
            Gesture params with two parallel strokes.
        """
        left = _stroke(
            [(cx - start_radius, cy), (cx - end_radius, cy)], duration=duration
        )
        right = _stroke(
            [(cx + start_radius, cy), (cx + end_radius, cy)], duration=duration
        )
        return {"strokes": [left, right]}
